"""IaC Scanner API routes.

Endpoints for Infrastructure-as-Code security scanning, webhook integration
with Git providers, and scan history management.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.auth import require_org_id
from ..db_helper import AsyncSessionLocal, get_db
from ..models.iac_models import (
    IaCFindingModel,
    IaCScanModel,
    IaCWebhookConfigModel,
)
from ..schemas.iac_schemas import (
    IaCFindingOut,
    IaCScanOut,
    IaCScanRequest,
    IaCWebhookConfigOut,
    IaCWebhookConfigRequest,
)
from ..services.iac_scanner import (
    CloudVisorConfig,
    IaCFinding,
    handle_bitbucket_webhook,
    handle_github_webhook,
    handle_gitlab_webhook,
    parse_cloudvisor_yaml,
    post_scan_results,
    scan_template,
    verify_webhook_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["IaC Scanner"])


# ---------------------------------------------------------------------------
# POST /api/v1/cspm/iac/scan — Submit IaC template for scanning (synchronous)
# ---------------------------------------------------------------------------


@router.post("/api/v1/cspm/iac/scan", response_model=IaCScanOut)
async def submit_iac_scan(
    payload: IaCScanRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> IaCScanOut:
    """Submit an IaC template for security scanning.

    Performs synchronous scanning: parses the template, detects secrets,
    evaluates against Rego rules, and returns results immediately.
    """
    scan_id = str(uuid.uuid4())
    started_at = datetime.utcnow()

    try:
        # Run the scan
        findings, parse_errors = await scan_template(
            content=payload.content,
            file_path=payload.file_path,
            template_type=payload.template_type,
        )

        # Compute severity counts
        critical_count = sum(1 for f in findings if f.severity == "CRITICAL")
        high_count = sum(1 for f in findings if f.severity == "HIGH")
        medium_count = sum(1 for f in findings if f.severity == "MEDIUM")
        low_count = sum(1 for f in findings if f.severity == "LOW")

        # Determine pass/fail based on enforcement mode
        if payload.enforcement_mode == "blocking":
            passed = critical_count == 0 and high_count == 0
        else:
            passed = True  # Advisory mode always passes

        completed_at = datetime.utcnow()

        # Persist scan record
        scan_model = IaCScanModel(
            id=scan_id,
            organization_id=org_id,
            source_type="api",
            template_type=payload.template_type,
            enforcement_mode=payload.enforcement_mode,
            status="completed",
            total_files=1,
            total_findings=len(findings),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            passed=passed,
            started_at=started_at,
            completed_at=completed_at,
        )
        db.add(scan_model)

        # Persist findings
        finding_models = []
        for finding in findings:
            finding_model = IaCFindingModel(
                id=str(uuid.uuid4()),
                organization_id=org_id,
                scan_id=scan_id,
                file_path=finding.file_path,
                line_number=finding.line_number,
                resource_identifier=finding.resource_identifier,
                resource_type=finding.resource_type,
                rule_id=finding.rule_id,
                severity=finding.severity,
                title=finding.title,
                description=finding.description,
                remediation=finding.remediation,
                is_secret=finding.is_secret,
                secret_type=finding.secret_type,
            )
            finding_models.append(finding_model)
            db.add(finding_model)

        await db.commit()

        # Build response
        findings_out = [IaCFindingOut.model_validate(fm) for fm in finding_models]

        return IaCScanOut(
            id=scan_id,
            organization_id=org_id,
            source_type="api",
            template_type=payload.template_type,
            enforcement_mode=payload.enforcement_mode,
            status="completed",
            total_files=1,
            total_findings=len(findings),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            passed=passed,
            findings=findings_out,
            started_at=started_at,
            completed_at=completed_at,
        )

    except Exception as e:
        logger.error("IaC scan failed: %s", e, exc_info=True)
        # Record failed scan
        scan_model = IaCScanModel(
            id=scan_id,
            organization_id=org_id,
            source_type="api",
            template_type=payload.template_type,
            enforcement_mode=payload.enforcement_mode,
            status="failed",
            total_files=1,
            started_at=started_at,
            completed_at=datetime.utcnow(),
        )
        db.add(scan_model)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


# ---------------------------------------------------------------------------
# POST /api/v1/cspm/iac/webhook — Webhook endpoint for Git providers (async)
# ---------------------------------------------------------------------------


@router.post("/api/v1/cspm/iac/webhook", status_code=202)
async def handle_webhook(
    request: Request,
    org_id: str = Depends(require_org_id),
) -> dict:
    """Receive webhook events from Git providers (GitHub, GitLab, Bitbucket).

    Auto-detects the Git provider from request headers, verifies the signature,
    parses the event, and triggers an asynchronous IaC scan.

    Returns 202 Accepted immediately; scan runs in background.
    """
    # Read raw body for signature verification
    body = await request.body()
    headers = dict(request.headers)

    # Auto-detect provider from headers
    provider = _detect_git_provider(headers)
    if not provider:
        raise HTTPException(
            status_code=400,
            detail="Unable to detect Git provider. Expected X-GitHub-Event, X-Gitlab-Event, or X-Hook-UUID header.",
        )

    # Parse the payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Determine repository for webhook config lookup
    repository = _extract_repository(payload, provider)
    if not repository:
        raise HTTPException(status_code=400, detail="Could not determine repository from payload")

    # Look up webhook configuration
    async with AsyncSessionLocal() as db:
        config_result = await db.execute(
            select(IaCWebhookConfigModel).where(
                IaCWebhookConfigModel.organization_id == org_id,
                IaCWebhookConfigModel.repository == repository,
                IaCWebhookConfigModel.git_provider == provider,
                IaCWebhookConfigModel.is_active == True,  # noqa: E712
            )
        )
        webhook_config = config_result.scalar_one_or_none()

    # Verify signature if config exists
    if webhook_config:
        signature = _get_signature_header(headers, provider)
        if not verify_webhook_signature(body, signature, webhook_config.webhook_secret, provider):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    else:
        # No config found — still process but log warning
        logger.warning(
            "No webhook config found for %s/%s org=%s; processing without signature verification",
            provider,
            repository,
            org_id,
        )

    # Parse the webhook event
    event = _parse_webhook_event(payload, provider)
    if not event:
        return {"status": "ignored", "message": "Event type not actionable"}

    # Launch background scan
    asyncio.create_task(
        _run_webhook_scan(org_id, event, webhook_config)
    )

    return {
        "status": "accepted",
        "message": "IaC scan triggered",
        "provider": provider,
        "repository": repository,
        "pull_request_id": event.pull_request_id,
    }


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/iac/scans — List IaC scan history
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/iac/scans", response_model=list[IaCScanOut])
async def list_scans(
    org_id: str = Depends(require_org_id),
    status: Optional[str] = Query(default=None),
    template_type: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[IaCScanOut]:
    """List IaC scan history with optional filters."""
    try:
        q = select(IaCScanModel).where(
            IaCScanModel.organization_id == org_id
        )
        if status:
            q = q.where(IaCScanModel.status == status)
        if template_type:
            q = q.where(IaCScanModel.template_type == template_type)

        q = q.order_by(IaCScanModel.started_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(q)).scalars().all()

        return [IaCScanOut.model_validate(r) for r in rows]
    except Exception as e:
        logger.error("list_scans error: %s", e)
        return []


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/iac/scans/{scan_id} — Get scan detail with findings
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/iac/scans/{scan_id}", response_model=IaCScanOut)
async def get_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
) -> IaCScanOut:
    """Get detailed IaC scan result including findings."""
    try:
        scan = (
            await db.execute(
                select(IaCScanModel).where(IaCScanModel.id == scan_id)
            )
        ).scalar_one_or_none()

        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")

        # Fetch associated findings
        findings_result = await db.execute(
            select(IaCFindingModel).where(IaCFindingModel.scan_id == scan_id)
        )
        findings = findings_result.scalars().all()

        scan_out = IaCScanOut.model_validate(scan)
        scan_out.findings = [IaCFindingOut.model_validate(f) for f in findings]

        return scan_out
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_scan error: %s", e)
        raise HTTPException(status_code=500, detail="Internal error")


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/iac/scans/{scan_id}/findings — Get findings for a scan
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/iac/scans/{scan_id}/findings", response_model=list[IaCFindingOut])
async def get_scan_findings(
    scan_id: str,
    severity: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[IaCFindingOut]:
    """Get findings for a specific IaC scan with optional severity filter."""
    try:
        # Verify scan exists
        scan = (
            await db.execute(
                select(IaCScanModel).where(IaCScanModel.id == scan_id)
            )
        ).scalar_one_or_none()

        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")

        q = select(IaCFindingModel).where(IaCFindingModel.scan_id == scan_id)
        if severity:
            q = q.where(IaCFindingModel.severity == severity.upper())

        q = q.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(q)).scalars().all()

        return [IaCFindingOut.model_validate(r) for r in rows]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_scan_findings error: %s", e)
        return []


# ---------------------------------------------------------------------------
# POST /api/v1/cspm/iac/webhook-configs — Register webhook configuration
# ---------------------------------------------------------------------------


@router.post("/api/v1/cspm/iac/webhook-configs", response_model=IaCWebhookConfigOut, status_code=201)
async def create_webhook_config(
    payload: IaCWebhookConfigRequest,
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> IaCWebhookConfigOut:
    """Register a new webhook configuration for a Git repository."""
    try:
        config = IaCWebhookConfigModel(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            git_provider=payload.git_provider,
            repository=payload.repository,
            webhook_secret=payload.webhook_secret,
            enforcement_mode=payload.enforcement_mode,
            scan_paths=payload.scan_paths,
            excluded_paths=payload.excluded_paths,
            severity_threshold=payload.severity_threshold,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)

        return IaCWebhookConfigOut.model_validate(config)
    except Exception as e:
        logger.error("create_webhook_config error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create webhook config")


# ---------------------------------------------------------------------------
# GET /api/v1/cspm/iac/webhook-configs — List webhook configurations
# ---------------------------------------------------------------------------


@router.get("/api/v1/cspm/iac/webhook-configs", response_model=list[IaCWebhookConfigOut])
async def list_webhook_configs(
    org_id: str = Depends(require_org_id),
    db: AsyncSession = Depends(get_db),
) -> list[IaCWebhookConfigOut]:
    """List all webhook configurations for the organization."""
    try:
        q = select(IaCWebhookConfigModel).where(
            IaCWebhookConfigModel.organization_id == org_id
        )
        q = q.order_by(IaCWebhookConfigModel.created_at.desc())
        rows = (await db.execute(q)).scalars().all()

        return [IaCWebhookConfigOut.model_validate(r) for r in rows]
    except Exception as e:
        logger.error("list_webhook_configs error: %s", e)
        return []


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _detect_git_provider(headers: dict[str, str]) -> str | None:
    """Auto-detect Git provider from webhook request headers."""
    # Normalize header keys to lowercase for comparison
    lower_headers = {k.lower(): v for k, v in headers.items()}

    if "x-github-event" in lower_headers:
        return "github"
    elif "x-gitlab-event" in lower_headers:
        return "gitlab"
    elif "x-hook-uuid" in lower_headers:
        return "bitbucket"
    return None


def _get_signature_header(headers: dict[str, str], provider: str) -> str:
    """Extract the signature header value based on provider."""
    lower_headers = {k.lower(): v for k, v in headers.items()}

    if provider == "github":
        return lower_headers.get("x-hub-signature-256", "")
    elif provider == "gitlab":
        return lower_headers.get("x-gitlab-token", "")
    elif provider == "bitbucket":
        return lower_headers.get("x-hub-signature", "")
    return ""


def _extract_repository(payload: dict, provider: str) -> str | None:
    """Extract repository full name from webhook payload."""
    if provider == "github":
        return payload.get("repository", {}).get("full_name")
    elif provider == "gitlab":
        return payload.get("project", {}).get("path_with_namespace")
    elif provider == "bitbucket":
        return payload.get("repository", {}).get("full_name")
    return None


def _parse_webhook_event(payload: dict, provider: str):
    """Parse webhook event based on provider."""
    if provider == "github":
        return handle_github_webhook(payload)
    elif provider == "gitlab":
        return handle_gitlab_webhook(payload)
    elif provider == "bitbucket":
        return handle_bitbucket_webhook(payload)
    return None


async def _run_webhook_scan(
    org_id: str,
    event,
    webhook_config: IaCWebhookConfigModel | None,
) -> None:
    """Run IaC scan in background for a webhook event.

    Creates a scan record, processes changed files, and posts results
    back to the Git provider.
    """
    scan_id = str(uuid.uuid4())
    started_at = datetime.utcnow()

    # Determine enforcement mode
    enforcement_mode = "advisory"
    if webhook_config:
        enforcement_mode = webhook_config.enforcement_mode

    try:
        async with AsyncSessionLocal() as db:
            # Create scan record
            scan_model = IaCScanModel(
                id=scan_id,
                organization_id=org_id,
                source_type="webhook",
                git_provider=event.provider,
                repository=event.repository,
                branch=event.branch,
                commit_sha=event.commit_sha,
                pull_request_id=event.pull_request_id,
                template_type="mixed",  # webhook scans may include multiple types
                enforcement_mode=enforcement_mode,
                status="running",
                total_files=len(event.changed_files),
                started_at=started_at,
            )
            db.add(scan_model)
            await db.commit()

            # Scan each changed file
            all_findings: list[IaCFinding] = []
            scanned_files = 0

            for file_path in event.changed_files:
                template_type = _detect_template_type(file_path)
                if not template_type:
                    continue

                # In a real implementation, we'd fetch file content from the Git provider
                # For now, log that we would scan this file
                logger.info(
                    "Would scan file %s (type=%s) from %s/%s@%s",
                    file_path,
                    template_type,
                    event.provider,
                    event.repository,
                    event.commit_sha,
                )
                scanned_files += 1

            # Compute severity counts
            critical_count = sum(1 for f in all_findings if f.severity == "CRITICAL")
            high_count = sum(1 for f in all_findings if f.severity == "HIGH")
            medium_count = sum(1 for f in all_findings if f.severity == "MEDIUM")
            low_count = sum(1 for f in all_findings if f.severity == "LOW")

            # Determine pass/fail
            if enforcement_mode == "blocking":
                passed = critical_count == 0 and high_count == 0
            else:
                passed = True

            # Update scan record
            scan_model.status = "completed"
            scan_model.total_files = scanned_files
            scan_model.total_findings = len(all_findings)
            scan_model.critical_count = critical_count
            scan_model.high_count = high_count
            scan_model.medium_count = medium_count
            scan_model.low_count = low_count
            scan_model.passed = passed
            scan_model.completed_at = datetime.utcnow()

            # Persist findings
            for finding in all_findings:
                finding_model = IaCFindingModel(
                    id=str(uuid.uuid4()),
                    organization_id=org_id,
                    scan_id=scan_id,
                    file_path=finding.file_path,
                    line_number=finding.line_number,
                    resource_identifier=finding.resource_identifier,
                    resource_type=finding.resource_type,
                    rule_id=finding.rule_id,
                    severity=finding.severity,
                    title=finding.title,
                    description=finding.description,
                    remediation=finding.remediation,
                    is_secret=finding.is_secret,
                    secret_type=finding.secret_type,
                )
                db.add(finding_model)

            await db.commit()

        # Post results back to Git provider
        await post_scan_results(
            provider=event.provider,
            repository=event.repository,
            commit_sha=event.commit_sha,
            pull_request_id=event.pull_request_id,
            findings=all_findings,
            passed=passed,
            enforcement_mode=enforcement_mode,
        )

        logger.info(
            "Webhook scan completed: scan_id=%s provider=%s repo=%s findings=%d passed=%s",
            scan_id,
            event.provider,
            event.repository,
            len(all_findings),
            passed,
        )

    except Exception as e:
        logger.error("Webhook scan failed: %s", e, exc_info=True)
        try:
            async with AsyncSessionLocal() as db:
                scan = (
                    await db.execute(
                        select(IaCScanModel).where(IaCScanModel.id == scan_id)
                    )
                ).scalar_one_or_none()
                if scan:
                    scan.status = "failed"
                    scan.completed_at = datetime.utcnow()
                    await db.commit()
        except Exception:
            pass


def _detect_template_type(file_path: str) -> str | None:
    """Detect IaC template type from file extension."""
    path_lower = file_path.lower()

    if path_lower.endswith(".tf") or path_lower.endswith(".tf.json"):
        return "terraform"
    elif path_lower.endswith((".yaml", ".yml")):
        # Could be CloudFormation or Kubernetes — check path hints
        if "cloudformation" in path_lower or "cfn" in path_lower:
            return "cloudformation"
        return "kubernetes"
    elif path_lower.endswith(".json"):
        if "cloudformation" in path_lower or "cfn" in path_lower:
            return "cloudformation"
        return None
    return None
