"""Async OPA (Open Policy Agent) evaluation client for CSPM service.

Communicates with the Policy Service (cv-policy) via HTTP to compile,
evaluate, and test Rego rules.
"""

import logging
from typing import Any

import httpx

from .config import get_cspm_settings

logger = logging.getLogger(__name__)


class OPAClientError(Exception):
    """Raised when an OPA operation fails."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class OPAClient:
    """Async HTTP client for the OPA-backed Policy Service."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None) -> None:
        settings = get_cspm_settings()
        self._base_url = (base_url or settings.opa_service_url).rstrip("/")
        self._timeout = timeout or settings.http_timeout

    async def compile_rule(
        self,
        rego_content: str,
        package_name: str | None = None,
    ) -> dict[str, Any]:
        """Compile a Rego rule to validate syntax and check for errors.

        Args:
            rego_content: The Rego source code to compile.
            package_name: Optional package name for the rule.

        Returns:
            Compilation result dict with 'valid' bool and optional 'errors' list.

        Raises:
            OPAClientError: If the request to the policy service fails.
        """
        payload: dict[str, Any] = {"rego_content": rego_content}
        if package_name:
            payload["package_name"] = package_name

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/internal/policy/compile",
                    json=payload,
                )
                if resp.status_code >= 500:
                    detail = resp.text[:500]
                    logger.error(
                        "OPA compile_rule server error [%d]: %s",
                        resp.status_code,
                        detail,
                    )
                    raise OPAClientError(
                        f"OPA compile failed: {detail}",
                        status_code=resp.status_code,
                    )
                # 4xx responses may indicate invalid Rego — return as result
                return resp.json()
        except httpx.HTTPError as exc:
            logger.error("Policy service connection error: %s", exc)
            raise OPAClientError(f"Policy service unavailable: {exc}") from exc

    async def evaluate_rule(
        self,
        rule_path: str,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate a Rego rule against the provided input data.

        Args:
            rule_path: The OPA rule path (e.g. "cspm/iac/terraform/s3_encryption").
            input_data: The input document to evaluate against.

        Returns:
            Evaluation result dict containing the rule's output.

        Raises:
            OPAClientError: If the request fails or returns a server error.
        """
        payload: dict[str, Any] = {
            "rule_path": rule_path,
            "input": input_data,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/internal/policy/evaluate",
                    json=payload,
                )
                if resp.status_code >= 400:
                    detail = resp.text[:500]
                    logger.error(
                        "OPA evaluate_rule failed [%d]: %s",
                        resp.status_code,
                        detail,
                    )
                    raise OPAClientError(
                        f"OPA evaluation failed: {detail}",
                        status_code=resp.status_code,
                    )
                return resp.json()
        except httpx.HTTPError as exc:
            logger.error("Policy service connection error: %s", exc)
            raise OPAClientError(f"Policy service unavailable: {exc}") from exc

    async def test_rule(
        self,
        rego_content: str,
        test_input: dict[str, Any],
        expected_output: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Test a Rego rule against sample input without persisting findings.

        Args:
            rego_content: The Rego source code to test.
            test_input: Sample input document for evaluation.
            expected_output: Optional expected output for assertion.

        Returns:
            Test result dict with 'result', 'passed' bool, and optional 'errors'.

        Raises:
            OPAClientError: If the request to the policy service fails.
        """
        payload: dict[str, Any] = {
            "rego_content": rego_content,
            "input": test_input,
        }
        if expected_output is not None:
            payload["expected_output"] = expected_output

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/internal/policy/test",
                    json=payload,
                )
                if resp.status_code >= 500:
                    detail = resp.text[:500]
                    logger.error(
                        "OPA test_rule server error [%d]: %s",
                        resp.status_code,
                        detail,
                    )
                    raise OPAClientError(
                        f"OPA test failed: {detail}",
                        status_code=resp.status_code,
                    )
                # 4xx may indicate rule errors — return as result
                return resp.json()
        except httpx.HTTPError as exc:
            logger.error("Policy service connection error: %s", exc)
            raise OPAClientError(f"Policy service unavailable: {exc}") from exc
