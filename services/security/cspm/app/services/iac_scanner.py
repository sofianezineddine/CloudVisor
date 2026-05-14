"""IaC Security Scanner — template parsing, secret detection, OPA evaluation, and Git webhooks.

Supports Terraform HCL, CloudFormation (JSON/YAML), Kubernetes manifests,
and Helm charts. Evaluates parsed resources against Rego rules via the
Policy Service and detects embedded secrets/credentials.

Also handles webhook events from GitHub, GitLab, and Bitbucket for
CI/CD-integrated IaC scanning.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..core.opa_client import OPAClient, OPAClientError

logger = logging.getLogger(__name__)


# ─── Secret Detection Patterns ─────────────────────────────────────────────────

SECRET_PATTERNS: list[tuple[str, str]] = [
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    (r"-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----", "Private Key"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
    (r"sk-[a-zA-Z0-9]{48}", "OpenAI API Key"),
    (r"(?i)(password|secret|token|api_key)\s*[=:]\s*['\"][^'\"]{8,}", "Hardcoded Secret"),
]

_COMPILED_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(pattern), secret_type) for pattern, secret_type in SECRET_PATTERNS
]


# ─── Data Classes ───────────────────────────────────────────────────────────────


@dataclass
class ParsedResource:
    """A single resource extracted from an IaC template."""

    resource_type: str
    resource_identifier: str
    properties: dict[str, Any]
    file_path: str
    line_number: int | None = None


@dataclass
class IaCFinding:
    """A security finding from IaC scanning."""

    file_path: str
    line_number: int | None
    resource_identifier: str
    resource_type: str | None
    rule_id: str
    severity: str
    title: str
    description: str | None = None
    remediation: str | None = None
    is_secret: bool = False
    secret_type: str | None = None


@dataclass
class IaCParseError:
    """Describes a parse error encountered during template parsing."""

    file_path: str
    line_number: int | None
    error_message: str


@dataclass
class IaCParseResult:
    """Result of parsing an IaC template."""

    resources: list[ParsedResource] = field(default_factory=list)
    errors: list[IaCParseError] = field(default_factory=list)


# ─── Template Parsers ───────────────────────────────────────────────────────────


def parse_terraform(content: str, file_path: str) -> IaCParseResult:
    """Parse a Terraform HCL file and extract resource blocks.

    Uses the python-hcl2 library to parse HCL syntax into a Python dict,
    then extracts all ``resource`` blocks with their type and name.

    Args:
        content: Raw HCL file content.
        file_path: Original file path for error reporting.

    Returns:
        IaCParseResult with extracted resources or parse errors.
    """
    result = IaCParseResult()

    try:
        import hcl2  # type: ignore[import-untyped]
        import io

        parsed = hcl2.load(io.StringIO(content))
    except Exception as exc:
        # Attempt to extract a line number from the error message
        line_number = _extract_line_from_error(str(exc))
        result.errors.append(
            IaCParseError(
                file_path=file_path,
                line_number=line_number,
                error_message=f"Failed to parse Terraform HCL: {exc}",
            )
        )
        logger.warning("Terraform parse error in %s: %s", file_path, exc)
        return result

    # python-hcl2 returns {"resource": [{type: [{name: {config}}]}]}
    resource_blocks = parsed.get("resource", [])
    for block in resource_blocks:
        if not isinstance(block, dict):
            continue
        for resource_type, instances in block.items():
            # python-hcl2 may return keys with surrounding quotes
            resource_type = resource_type.strip('"')
            if not isinstance(instances, list):
                instances = [instances]
            for instance in instances:
                if not isinstance(instance, dict):
                    continue
                for resource_name, config in instance.items():
                    resource_name = resource_name.strip('"')
                    properties = config if isinstance(config, dict) else {}
                    line_number = _estimate_line_number(
                        content, resource_type, resource_name
                    )
                    result.resources.append(
                        ParsedResource(
                            resource_type=resource_type,
                            resource_identifier=f"{resource_type}.{resource_name}",
                            properties=properties,
                            file_path=file_path,
                            line_number=line_number,
                        )
                    )

    logger.info(
        "Parsed %d Terraform resources from %s", len(result.resources), file_path
    )
    return result


def parse_cloudformation(content: str, file_path: str) -> IaCParseResult:
    """Parse a CloudFormation template (JSON or YAML) and extract Resources.

    Args:
        content: Raw CloudFormation template content.
        file_path: Original file path for error reporting.

    Returns:
        IaCParseResult with extracted resources or parse errors.
    """
    result = IaCParseResult()
    parsed: dict[str, Any] | None = None

    # Try JSON first, then YAML
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        try:
            parsed = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            line_number = _extract_yaml_error_line(exc)
            result.errors.append(
                IaCParseError(
                    file_path=file_path,
                    line_number=line_number,
                    error_message=f"Failed to parse CloudFormation template: {exc}",
                )
            )
            logger.warning("CloudFormation parse error in %s: %s", file_path, exc)
            return result

    if parsed is None or not isinstance(parsed, dict):
        result.errors.append(
            IaCParseError(
                file_path=file_path,
                line_number=1,
                error_message="CloudFormation template is empty or not a valid mapping",
            )
        )
        return result

    resources_section = parsed.get("Resources", {})
    if not isinstance(resources_section, dict):
        result.errors.append(
            IaCParseError(
                file_path=file_path,
                line_number=None,
                error_message="CloudFormation 'Resources' section is missing or invalid",
            )
        )
        return result

    for logical_id, resource_def in resources_section.items():
        if not isinstance(resource_def, dict):
            continue
        resource_type = resource_def.get("Type", "Unknown")
        properties = resource_def.get("Properties", {})
        line_number = _estimate_line_number(content, logical_id)

        result.resources.append(
            ParsedResource(
                resource_type=resource_type,
                resource_identifier=logical_id,
                properties=properties if isinstance(properties, dict) else {},
                file_path=file_path,
                line_number=line_number,
            )
        )

    logger.info(
        "Parsed %d CloudFormation resources from %s",
        len(result.resources),
        file_path,
    )
    return result


def parse_kubernetes(content: str, file_path: str) -> IaCParseResult:
    """Parse multi-document Kubernetes YAML and extract resource definitions.

    Args:
        content: Raw YAML content (may contain multiple documents separated by ---).
        file_path: Original file path for error reporting.

    Returns:
        IaCParseResult with extracted resources or parse errors.
    """
    result = IaCParseResult()

    try:
        documents = list(yaml.safe_load_all(content))
    except yaml.YAMLError as exc:
        line_number = _extract_yaml_error_line(exc)
        result.errors.append(
            IaCParseError(
                file_path=file_path,
                line_number=line_number,
                error_message=f"Failed to parse Kubernetes YAML: {exc}",
            )
        )
        logger.warning("Kubernetes YAML parse error in %s: %s", file_path, exc)
        return result

    for doc in documents:
        if doc is None or not isinstance(doc, dict):
            continue

        kind = doc.get("kind", "Unknown")
        api_version = doc.get("apiVersion", "")
        metadata = doc.get("metadata", {})
        name = metadata.get("name", "unnamed") if isinstance(metadata, dict) else "unnamed"
        namespace = metadata.get("namespace", "default") if isinstance(metadata, dict) else "default"

        resource_identifier = f"{namespace}/{kind}/{name}"
        line_number = _estimate_line_number(content, f"name: {name}")

        # Merge spec and metadata as properties for rule evaluation
        properties: dict[str, Any] = {
            "apiVersion": api_version,
            "kind": kind,
            "metadata": metadata if isinstance(metadata, dict) else {},
            "spec": doc.get("spec", {}),
        }

        result.resources.append(
            ParsedResource(
                resource_type=f"{api_version}/{kind}" if api_version else kind,
                resource_identifier=resource_identifier,
                properties=properties,
                file_path=file_path,
                line_number=line_number,
            )
        )

    logger.info(
        "Parsed %d Kubernetes resources from %s", len(result.resources), file_path
    )
    return result


def parse_helm(
    chart_path: str,
    file_path: str,
    values: dict[str, Any] | None = None,
    release_name: str = "release",
) -> IaCParseResult:
    """Render a Helm chart via ``helm template`` and parse as Kubernetes manifests.

    Args:
        chart_path: Path to the Helm chart directory or .tgz archive.
        file_path: Logical file path for reporting.
        values: Optional values to pass to helm template (--set-json).
        release_name: Release name for rendering.

    Returns:
        IaCParseResult with extracted resources or parse errors.
    """
    result = IaCParseResult()

    cmd = ["helm", "template", release_name, chart_path]

    # Write values to a temp file if provided
    values_file = None
    try:
        if values:
            values_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            )
            yaml.safe_dump(values, values_file)
            values_file.close()
            cmd.extend(["--values", values_file.name])

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if proc.returncode != 0:
            error_msg = proc.stderr.strip() or "helm template failed with no output"
            line_number = _extract_line_from_error(error_msg)
            result.errors.append(
                IaCParseError(
                    file_path=file_path,
                    line_number=line_number,
                    error_message=f"Helm template rendering failed: {error_msg}",
                )
            )
            logger.warning("Helm render error for %s: %s", file_path, error_msg)
            return result

        # Parse the rendered output as Kubernetes manifests
        rendered_content = proc.stdout
        if not rendered_content.strip():
            result.errors.append(
                IaCParseError(
                    file_path=file_path,
                    line_number=None,
                    error_message="Helm template produced empty output",
                )
            )
            return result

        k8s_result = parse_kubernetes(rendered_content, file_path)
        result.resources = k8s_result.resources
        result.errors = k8s_result.errors

    except FileNotFoundError:
        result.errors.append(
            IaCParseError(
                file_path=file_path,
                line_number=None,
                error_message="'helm' command not found. Ensure Helm is installed and in PATH.",
            )
        )
        logger.error("Helm binary not found when processing %s", file_path)
    except subprocess.TimeoutExpired:
        result.errors.append(
            IaCParseError(
                file_path=file_path,
                line_number=None,
                error_message="Helm template rendering timed out after 60 seconds",
            )
        )
        logger.error("Helm template timed out for %s", file_path)
    except Exception as exc:
        result.errors.append(
            IaCParseError(
                file_path=file_path,
                line_number=None,
                error_message=f"Unexpected error during Helm rendering: {exc}",
            )
        )
        logger.error("Unexpected Helm error for %s: %s", file_path, exc)
    finally:
        if values_file:
            try:
                Path(values_file.name).unlink(missing_ok=True)
            except OSError:
                pass

    logger.info(
        "Parsed %d resources from Helm chart %s", len(result.resources), file_path
    )
    return result


# ─── Secret Detection ───────────────────────────────────────────────────────────


def detect_secrets(content: str, file_path: str) -> list[IaCFinding]:
    """Scan content for embedded secrets and credentials.

    Matches against known secret patterns and returns findings with the
    actual secret value REDACTED.

    Args:
        content: Raw file content to scan.
        file_path: File path for reporting.

    Returns:
        List of IaCFinding objects for each detected secret.
    """
    findings: list[IaCFinding] = []
    lines = content.splitlines()

    for line_idx, line in enumerate(lines, start=1):
        for pattern, secret_type in _COMPILED_SECRET_PATTERNS:
            match = pattern.search(line)
            if match:
                # Redact the matched secret value
                redacted_value = _redact_value(match.group(0))
                findings.append(
                    IaCFinding(
                        file_path=file_path,
                        line_number=line_idx,
                        resource_identifier=f"secret:{file_path}:{line_idx}",
                        resource_type=None,
                        rule_id="iac.secrets.embedded-credential",
                        severity="CRITICAL",
                        title=f"Embedded {secret_type} detected",
                        description=(
                            f"A {secret_type} was found at line {line_idx}. "
                            f"Value: {redacted_value}"
                        ),
                        remediation=(
                            "Remove the hardcoded secret and use a secrets manager "
                            "(e.g., HashiCorp Vault, AWS Secrets Manager) or "
                            "environment variables instead."
                        ),
                        is_secret=True,
                        secret_type=secret_type,
                    )
                )
                logger.debug(
                    "Secret detected in %s at line %d: %s",
                    file_path,
                    line_idx,
                    secret_type,
                )
                # Only report one secret per line to avoid duplicates
                break

    if findings:
        logger.info(
            "Detected %d secret(s) in %s", len(findings), file_path
        )
    return findings


# ─── OPA Rule Evaluation ────────────────────────────────────────────────────────


async def evaluate_against_rules(
    resources: list[ParsedResource],
    rule_paths: list[str] | None = None,
    opa_client: OPAClient | None = None,
) -> list[IaCFinding]:
    """Evaluate parsed IaC resources against OPA/Rego rules.

    Sends each resource to the Policy Service for evaluation and collects
    any violations as findings.

    Args:
        resources: List of parsed resources to evaluate.
        rule_paths: Optional list of specific rule paths to evaluate.
            If None, evaluates against all applicable rules for the resource type.
        opa_client: Optional OPAClient instance. Creates a new one if not provided.

    Returns:
        List of IaCFinding objects for each rule violation.
    """
    if opa_client is None:
        opa_client = OPAClient()

    findings: list[IaCFinding] = []

    for resource in resources:
        # Determine applicable rule paths based on resource type
        paths_to_evaluate = rule_paths or _get_rule_paths_for_resource(resource)

        for rule_path in paths_to_evaluate:
            try:
                input_data = {
                    "resource": {
                        "type": resource.resource_type,
                        "identifier": resource.resource_identifier,
                        "properties": resource.properties,
                    }
                }

                result = await opa_client.evaluate_rule(rule_path, input_data)

                # Process violations from OPA result
                violations = result.get("result", {}).get("violations", [])
                if not isinstance(violations, list):
                    violations = [violations] if violations else []

                for violation in violations:
                    if not isinstance(violation, dict):
                        continue
                    findings.append(
                        IaCFinding(
                            file_path=resource.file_path,
                            line_number=resource.line_number,
                            resource_identifier=resource.resource_identifier,
                            resource_type=resource.resource_type,
                            rule_id=violation.get("rule_id", rule_path),
                            severity=violation.get("severity", "MEDIUM"),
                            title=violation.get("title", f"Policy violation: {rule_path}"),
                            description=violation.get("description"),
                            remediation=violation.get("remediation"),
                            is_secret=False,
                            secret_type=None,
                        )
                    )

            except OPAClientError as exc:
                logger.warning(
                    "OPA evaluation failed for resource %s with rule %s: %s",
                    resource.resource_identifier,
                    rule_path,
                    exc,
                )
            except Exception as exc:
                logger.error(
                    "Unexpected error evaluating resource %s against %s: %s",
                    resource.resource_identifier,
                    rule_path,
                    exc,
                )

    logger.info(
        "Evaluated %d resources, found %d violations",
        len(resources),
        len(findings),
    )
    return findings


# ─── High-Level Scan Orchestration ──────────────────────────────────────────────


async def scan_template(
    content: str,
    file_path: str,
    template_type: str,
    rule_paths: list[str] | None = None,
    opa_client: OPAClient | None = None,
) -> tuple[list[IaCFinding], list[IaCParseError]]:
    """Scan an IaC template: parse, detect secrets, and evaluate rules.

    This is the main entry point for scanning a single IaC file.

    Args:
        content: Raw template content.
        file_path: Original file path for reporting.
        template_type: One of 'terraform', 'cloudformation', 'kubernetes', 'helm'.
        rule_paths: Optional specific rule paths to evaluate.
        opa_client: Optional OPAClient instance.

    Returns:
        Tuple of (findings, parse_errors).
    """
    all_findings: list[IaCFinding] = []
    parse_errors: list[IaCParseError] = []

    # Step 1: Parse the template
    parse_result = _parse_by_type(content, file_path, template_type)
    parse_errors.extend(parse_result.errors)

    # Step 2: Detect secrets in the raw content
    secret_findings = detect_secrets(content, file_path)
    all_findings.extend(secret_findings)

    # Step 3: Evaluate parsed resources against OPA rules
    if parse_result.resources:
        rule_findings = await evaluate_against_rules(
            parse_result.resources, rule_paths, opa_client
        )
        all_findings.extend(rule_findings)

    logger.info(
        "Scan complete for %s: %d findings, %d parse errors",
        file_path,
        len(all_findings),
        len(parse_errors),
    )
    return all_findings, parse_errors


# ─── Helper Functions ───────────────────────────────────────────────────────────


def _parse_by_type(content: str, file_path: str, template_type: str) -> IaCParseResult:
    """Route to the appropriate parser based on template type."""
    parsers = {
        "terraform": parse_terraform,
        "cloudformation": parse_cloudformation,
        "kubernetes": parse_kubernetes,
    }

    parser = parsers.get(template_type.lower())
    if parser is None:
        if template_type.lower() == "helm":
            # Helm requires a chart path, not raw content — treat as K8s if content provided
            logger.info(
                "Helm content provided directly; parsing as Kubernetes manifests"
            )
            return parse_kubernetes(content, file_path)
        return IaCParseResult(
            errors=[
                IaCParseError(
                    file_path=file_path,
                    line_number=None,
                    error_message=f"Unsupported template type: {template_type}",
                )
            ]
        )

    return parser(content, file_path)


def _get_rule_paths_for_resource(resource: ParsedResource) -> list[str]:
    """Determine OPA rule paths applicable to a resource based on its type."""
    resource_type_lower = resource.resource_type.lower()

    # Terraform resources (e.g., aws_s3_bucket, aws_security_group)
    if resource_type_lower.startswith("aws_"):
        return [f"cspm/iac/terraform/{resource_type_lower}"]

    # CloudFormation resources (e.g., AWS::S3::Bucket)
    if "::" in resource_type_lower:
        # Convert AWS::S3::Bucket -> s3_bucket
        parts = resource_type_lower.split("::")
        if len(parts) >= 3:
            cf_rule_name = f"{parts[1]}_{parts[2]}".lower()
            return [f"cspm/iac/cloudformation/{cf_rule_name}"]

    # Kubernetes resources (e.g., apps/v1/Deployment)
    if "/" in resource_type_lower:
        kind = resource_type_lower.split("/")[-1].lower()
        return [f"cspm/iac/kubernetes/{kind}"]

    # Fallback: use the resource type directly
    return [f"cspm/iac/{resource_type_lower}"]


def _estimate_line_number(content: str, *search_terms: str) -> int | None:
    """Estimate the line number where a resource is defined.

    Searches for the first occurrence of any search term in the content.
    """
    lines = content.splitlines()
    for term in search_terms:
        if not term:
            continue
        for idx, line in enumerate(lines, start=1):
            if term in line:
                return idx
    return None


def _extract_line_from_error(error_msg: str) -> int | None:
    """Try to extract a line number from an error message."""
    # Common patterns: "line 42", "Line 42", ":42:", "at line 42"
    match = re.search(r"(?:line|Line|:)\s*(\d+)", error_msg)
    if match:
        return int(match.group(1))
    return None


def _extract_yaml_error_line(exc: Exception) -> int | None:
    """Extract line number from a YAML parsing exception."""
    if hasattr(exc, "problem_mark") and exc.problem_mark is not None:  # type: ignore[union-attr]
        return exc.problem_mark.line + 1  # type: ignore[union-attr]
    return _extract_line_from_error(str(exc))


def _redact_value(secret_value: str) -> str:
    """Redact a secret value, showing only the first 4 characters.

    Args:
        secret_value: The raw secret string.

    Returns:
        Redacted string like "AKIA****REDACTED****".
    """
    if len(secret_value) <= 4:
        return "****REDACTED****"
    return f"{secret_value[:4]}****REDACTED****"


# ─── Webhook Data Classes ───────────────────────────────────────────────────────


@dataclass
class WebhookEvent:
    """Parsed webhook event from a Git provider."""

    provider: str  # github, gitlab, bitbucket
    repository: str
    branch: str
    commit_sha: str
    pull_request_id: str | None
    changed_files: list[str]
    action: str  # opened, synchronize, updated, etc.
    sender: str | None = None


@dataclass
class CloudVisorConfig:
    """Parsed .cloudvisor.yaml configuration from a repository."""

    scan_paths: list[str] = field(default_factory=lambda: ["**/*.tf", "**/*.yaml", "**/*.yml", "**/*.json"])
    excluded_paths: list[str] = field(default_factory=list)
    enforcement_mode: str = "advisory"
    severity_threshold: str = "HIGH"
    template_types: list[str] = field(default_factory=lambda: ["terraform", "cloudformation", "kubernetes"])
    notifications: dict[str, Any] = field(default_factory=dict)


# ─── Webhook Signature Verification ────────────────────────────────────────────


def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str,
    provider: str,
) -> bool:
    """Verify webhook payload signature from a Git provider.

    Uses HMAC-SHA256 for GitHub, token comparison for GitLab,
    and HMAC-SHA256 for Bitbucket.

    Args:
        payload: Raw request body bytes.
        signature: Signature header value from the request.
        secret: Webhook secret configured for this repository.
        provider: Git provider name (github, gitlab, bitbucket).

    Returns:
        True if signature is valid, False otherwise.
    """
    if not signature or not secret:
        return False

    if provider == "github":
        # GitHub uses HMAC-SHA256: X-Hub-Signature-256 = sha256=<hex>
        expected = "sha256=" + hmac.HMAC(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    elif provider == "gitlab":
        # GitLab sends the secret token in X-Gitlab-Token header
        return hmac.compare_digest(secret, signature)

    elif provider == "bitbucket":
        # Bitbucket Cloud uses HMAC-SHA256
        expected = hmac.HMAC(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    logger.warning("Unknown provider for signature verification: %s", provider)
    return False


# ─── GitHub Webhook Handler ─────────────────────────────────────────────────────


def handle_github_webhook(payload: dict[str, Any]) -> WebhookEvent | None:
    """Parse a GitHub pull_request webhook event and extract changed files info.

    Args:
        payload: Parsed JSON body from GitHub webhook.

    Returns:
        WebhookEvent with PR details, or None if event should be ignored.
    """
    action = payload.get("action", "")

    # Only process opened, synchronize (new push), and reopened events
    if action not in ("opened", "synchronize", "reopened"):
        logger.info("Ignoring GitHub PR action: %s", action)
        return None

    pull_request = payload.get("pull_request", {})
    if not pull_request:
        logger.warning("GitHub webhook missing pull_request field")
        return None

    repository = payload.get("repository", {})
    head = pull_request.get("head", {})

    # Extract changed files from the PR
    # Note: GitHub webhook doesn't include file list directly;
    # the API route will fetch files via GitHub API
    changed_files: list[str] = []

    # If files are included in the payload (some webhook configs include them)
    if "files" in payload:
        changed_files = [f.get("filename", "") for f in payload["files"] if f.get("filename")]

    return WebhookEvent(
        provider="github",
        repository=repository.get("full_name", ""),
        branch=head.get("ref", ""),
        commit_sha=head.get("sha", ""),
        pull_request_id=str(pull_request.get("number", "")),
        changed_files=changed_files,
        action=action,
        sender=payload.get("sender", {}).get("login"),
    )


# ─── GitLab Webhook Handler ─────────────────────────────────────────────────────


def handle_gitlab_webhook(payload: dict[str, Any]) -> WebhookEvent | None:
    """Parse a GitLab merge_request webhook event and extract changed files info.

    Args:
        payload: Parsed JSON body from GitLab webhook.

    Returns:
        WebhookEvent with MR details, or None if event should be ignored.
    """
    object_kind = payload.get("object_kind", "")
    if object_kind != "merge_request":
        logger.info("Ignoring GitLab event kind: %s", object_kind)
        return None

    object_attributes = payload.get("object_attributes", {})
    action = object_attributes.get("action", "")

    # Only process open, update, and reopen actions
    if action not in ("open", "update", "reopen"):
        logger.info("Ignoring GitLab MR action: %s", action)
        return None

    project = payload.get("project", {})
    last_commit = object_attributes.get("last_commit", {})

    # GitLab includes changes in the webhook payload
    changes = payload.get("changes", {})
    changed_files: list[str] = []

    # Extract file paths from commits if available
    commits = payload.get("commits", [])
    for commit in commits:
        changed_files.extend(commit.get("added", []))
        changed_files.extend(commit.get("modified", []))

    # Deduplicate
    changed_files = list(set(changed_files))

    return WebhookEvent(
        provider="gitlab",
        repository=project.get("path_with_namespace", ""),
        branch=object_attributes.get("source_branch", ""),
        commit_sha=last_commit.get("id", ""),
        pull_request_id=str(object_attributes.get("iid", "")),
        changed_files=changed_files,
        action=action,
        sender=payload.get("user", {}).get("username"),
    )


# ─── Bitbucket Webhook Handler ──────────────────────────────────────────────────


def handle_bitbucket_webhook(payload: dict[str, Any]) -> WebhookEvent | None:
    """Parse a Bitbucket pull_request webhook event and extract changed files info.

    Args:
        payload: Parsed JSON body from Bitbucket webhook.

    Returns:
        WebhookEvent with PR details, or None if event should be ignored.
    """
    pullrequest = payload.get("pullrequest", {})
    if not pullrequest:
        logger.warning("Bitbucket webhook missing pullrequest field")
        return None

    # Bitbucket sends state in the pullrequest object
    state = pullrequest.get("state", "")
    if state not in ("OPEN",):
        logger.info("Ignoring Bitbucket PR state: %s", state)
        return None

    repository = payload.get("repository", {})
    source = pullrequest.get("source", {})
    source_branch = source.get("branch", {})
    source_commit = source.get("commit", {})

    # Bitbucket doesn't include file list in webhook; files fetched via API
    changed_files: list[str] = []

    return WebhookEvent(
        provider="bitbucket",
        repository=repository.get("full_name", ""),
        branch=source_branch.get("name", ""),
        commit_sha=source_commit.get("hash", ""),
        pull_request_id=str(pullrequest.get("id", "")),
        changed_files=changed_files,
        action="opened",
        sender=payload.get("actor", {}).get("display_name"),
    )


# ─── Post Scan Results to Git Provider ──────────────────────────────────────────


async def post_scan_results(
    provider: str,
    repository: str,
    commit_sha: str,
    pull_request_id: str | None,
    findings: list[IaCFinding],
    passed: bool,
    enforcement_mode: str = "advisory",
) -> bool:
    """Post scan results back to the Git provider as a status check or comment.

    For blocking mode, posts a commit status (success/failure).
    For advisory mode, posts a PR comment with findings summary.

    Args:
        provider: Git provider name (github, gitlab, bitbucket).
        repository: Full repository name (org/repo).
        commit_sha: Commit SHA to post status on.
        pull_request_id: PR/MR number for comments.
        findings: List of scan findings.
        passed: Whether the scan passed (no blocking findings).
        enforcement_mode: advisory or blocking.

    Returns:
        True if posting succeeded, False otherwise.
    """
    try:
        # Build summary
        critical_count = sum(1 for f in findings if f.severity == "CRITICAL")
        high_count = sum(1 for f in findings if f.severity == "HIGH")
        medium_count = sum(1 for f in findings if f.severity == "MEDIUM")
        low_count = sum(1 for f in findings if f.severity == "LOW")

        summary = (
            f"CloudVisor IaC Scan: {'✅ Passed' if passed else '❌ Failed'}\n"
            f"Findings: {len(findings)} total "
            f"({critical_count} critical, {high_count} high, "
            f"{medium_count} medium, {low_count} low)"
        )

        if provider == "github":
            return await _post_github_status(
                repository, commit_sha, pull_request_id, summary, passed, findings
            )
        elif provider == "gitlab":
            return await _post_gitlab_status(
                repository, commit_sha, pull_request_id, summary, passed, findings
            )
        elif provider == "bitbucket":
            return await _post_bitbucket_status(
                repository, commit_sha, pull_request_id, summary, passed, findings
            )
        else:
            logger.warning("Unknown provider for posting results: %s", provider)
            return False

    except Exception as exc:
        logger.error(
            "Failed to post scan results to %s/%s: %s", provider, repository, exc
        )
        return False


async def _post_github_status(
    repository: str,
    commit_sha: str,
    pull_request_id: str | None,
    summary: str,
    passed: bool,
    findings: list[IaCFinding],
) -> bool:
    """Post commit status and PR comment to GitHub.

    Uses the GitHub API to set a commit status and optionally post a comment.
    Requires GITHUB_TOKEN environment variable.
    """
    import os

    import httpx

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        logger.warning("GITHUB_TOKEN not set; cannot post to GitHub")
        return False

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    async with httpx.AsyncClient() as client:
        # Post commit status
        status_url = f"https://api.github.com/repos/{repository}/statuses/{commit_sha}"
        status_payload = {
            "state": "success" if passed else "failure",
            "description": summary[:140],
            "context": "cloudvisor/iac-scan",
        }
        resp = await client.post(status_url, json=status_payload, headers=headers)
        if resp.status_code not in (200, 201):
            logger.warning("GitHub status post failed: %d %s", resp.status_code, resp.text)

        # Post PR comment with details if there are findings
        if pull_request_id and findings:
            comment_url = (
                f"https://api.github.com/repos/{repository}"
                f"/issues/{pull_request_id}/comments"
            )
            comment_body = _format_findings_comment(summary, findings)
            resp = await client.post(
                comment_url, json={"body": comment_body}, headers=headers
            )
            if resp.status_code not in (200, 201):
                logger.warning("GitHub comment post failed: %d", resp.status_code)

    return True


async def _post_gitlab_status(
    repository: str,
    commit_sha: str,
    pull_request_id: str | None,
    summary: str,
    passed: bool,
    findings: list[IaCFinding],
) -> bool:
    """Post commit status and MR note to GitLab.

    Uses the GitLab API. Requires GITLAB_TOKEN and GITLAB_URL environment variables.
    """
    import os
    import urllib.parse

    import httpx

    token = os.environ.get("GITLAB_TOKEN")
    gitlab_url = os.environ.get("GITLAB_URL", "https://gitlab.com")
    if not token:
        logger.warning("GITLAB_TOKEN not set; cannot post to GitLab")
        return False

    headers = {"PRIVATE-TOKEN": token}
    project_encoded = urllib.parse.quote(repository, safe="")

    async with httpx.AsyncClient() as client:
        # Post commit status
        status_url = (
            f"{gitlab_url}/api/v4/projects/{project_encoded}"
            f"/statuses/{commit_sha}"
        )
        status_payload = {
            "state": "success" if passed else "failed",
            "description": summary[:140],
            "name": "cloudvisor/iac-scan",
        }
        resp = await client.post(status_url, json=status_payload, headers=headers)
        if resp.status_code not in (200, 201):
            logger.warning("GitLab status post failed: %d", resp.status_code)

        # Post MR note
        if pull_request_id and findings:
            note_url = (
                f"{gitlab_url}/api/v4/projects/{project_encoded}"
                f"/merge_requests/{pull_request_id}/notes"
            )
            comment_body = _format_findings_comment(summary, findings)
            resp = await client.post(
                note_url, json={"body": comment_body}, headers=headers
            )
            if resp.status_code not in (200, 201):
                logger.warning("GitLab note post failed: %d", resp.status_code)

    return True


async def _post_bitbucket_status(
    repository: str,
    commit_sha: str,
    pull_request_id: str | None,
    summary: str,
    passed: bool,
    findings: list[IaCFinding],
) -> bool:
    """Post commit status and PR comment to Bitbucket.

    Uses the Bitbucket API. Requires BITBUCKET_TOKEN environment variable.
    """
    import os

    import httpx

    token = os.environ.get("BITBUCKET_TOKEN")
    if not token:
        logger.warning("BITBUCKET_TOKEN not set; cannot post to Bitbucket")
        return False

    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        # Post commit status
        status_url = (
            f"https://api.bitbucket.org/2.0/repositories/{repository}"
            f"/commit/{commit_sha}/statuses/build"
        )
        status_payload = {
            "state": "SUCCESSFUL" if passed else "FAILED",
            "key": "cloudvisor-iac-scan",
            "name": "CloudVisor IaC Scan",
            "description": summary[:140],
        }
        resp = await client.post(status_url, json=status_payload, headers=headers)
        if resp.status_code not in (200, 201):
            logger.warning("Bitbucket status post failed: %d", resp.status_code)

        # Post PR comment
        if pull_request_id and findings:
            comment_url = (
                f"https://api.bitbucket.org/2.0/repositories/{repository}"
                f"/pullrequests/{pull_request_id}/comments"
            )
            comment_body = _format_findings_comment(summary, findings)
            resp = await client.post(
                comment_url,
                json={"content": {"raw": comment_body}},
                headers=headers,
            )
            if resp.status_code not in (200, 201):
                logger.warning("Bitbucket comment post failed: %d", resp.status_code)

    return True


def _format_findings_comment(summary: str, findings: list[IaCFinding]) -> str:
    """Format findings into a markdown comment for Git provider PRs."""
    lines = [f"## 🔒 {summary}", "", "| Severity | File | Rule | Title |", "|----------|------|------|-------|"]

    # Show top 20 findings to avoid overly long comments
    for finding in findings[:20]:
        location = finding.file_path
        if finding.line_number:
            location += f":{finding.line_number}"
        lines.append(
            f"| {finding.severity} | `{location}` | {finding.rule_id} | {finding.title} |"
        )

    if len(findings) > 20:
        lines.append(f"\n_...and {len(findings) - 20} more findings._")

    return "\n".join(lines)


# ─── CloudVisor YAML Config Parser ─────────────────────────────────────────────


def parse_cloudvisor_yaml(content: str) -> CloudVisorConfig:
    """Parse a .cloudvisor.yaml configuration file from a repository.

    This file allows repository owners to customize IaC scanning behavior
    including scan paths, exclusions, enforcement mode, and severity thresholds.

    Args:
        content: Raw YAML content of the .cloudvisor.yaml file.

    Returns:
        CloudVisorConfig with parsed settings, or defaults if parsing fails.
    """
    config = CloudVisorConfig()

    try:
        parsed = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        logger.warning("Failed to parse .cloudvisor.yaml: %s", exc)
        return config

    if not isinstance(parsed, dict):
        return config

    iac_section = parsed.get("iac", parsed)  # Support both top-level and nested

    if isinstance(iac_section.get("scan_paths"), list):
        config.scan_paths = iac_section["scan_paths"]

    if isinstance(iac_section.get("excluded_paths"), list):
        config.excluded_paths = iac_section["excluded_paths"]

    if isinstance(iac_section.get("enforcement_mode"), str):
        mode = iac_section["enforcement_mode"].lower()
        if mode in ("advisory", "blocking"):
            config.enforcement_mode = mode

    if isinstance(iac_section.get("severity_threshold"), str):
        threshold = iac_section["severity_threshold"].upper()
        if threshold in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            config.severity_threshold = threshold

    if isinstance(iac_section.get("template_types"), list):
        config.template_types = iac_section["template_types"]

    if isinstance(iac_section.get("notifications"), dict):
        config.notifications = iac_section["notifications"]

    return config
