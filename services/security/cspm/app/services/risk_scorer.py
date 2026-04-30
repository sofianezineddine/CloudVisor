"""Risk scoring engine for CSPM resources."""
import logging
from typing import Any

logger = logging.getLogger(__name__)

SEVERITY_WEIGHTS = {
    "CRITICAL": 40,
    "HIGH": 15,
    "MEDIUM": 4,
    "LOW": 1,
    "INFO": 0,
}


def compute_risk_score(
    findings: list[dict[str, Any]],
    is_internet_exposed: bool = False,
    contains_sensitive_data: bool = False,
    environment: str = "unknown",
) -> int:
    """
    Compute risk score 0-100 per CSPM spec:
    - Finding severity contribution (max 60 pts)
    - Context multipliers: internet_exposed(1.3x), sensitive_data(1.2x), prod(1.5x)
    """
    counts: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for f in findings:
        sev = f.get("severity", "MEDIUM").upper()
        counts[sev] = counts.get(sev, 0) + 1

    # Severity contribution capped at 60 pts
    raw = (
        counts["CRITICAL"] * SEVERITY_WEIGHTS["CRITICAL"]
        + counts["HIGH"] * SEVERITY_WEIGHTS["HIGH"]
        + counts["MEDIUM"] * SEVERITY_WEIGHTS["MEDIUM"]
        + counts["LOW"] * SEVERITY_WEIGHTS["LOW"]
    )
    score = min(float(raw), 60.0)

    # Context multipliers
    if is_internet_exposed:
        score *= 1.3
    if contains_sensitive_data:
        score *= 1.2
    if environment.lower() in ("prod", "production"):
        score *= 1.5

    return min(int(score), 100)


def get_score_color(score: int) -> str:
    """Return color class for risk score display."""
    if score >= 80:
        return "red"
    elif score >= 60:
        return "orange-red"
    elif score >= 40:
        return "amber"
    elif score >= 20:
        return "blue"
    return "green"
