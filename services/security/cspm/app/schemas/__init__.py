"""Pydantic schemas for all CSPM modules."""

from .iam_schemas import (
    CrossAccountTrustOut,
    DormantIdentityOut,
    EscalationPathOut,
    IAMAnalyzeRequest,
    IAMIdentityListOut,
    IAMIdentityOut,
    ServiceAccountOut,
)
from .attack_path_schemas import (
    AttackPathAnalyzeRequest,
    AttackPathListOut,
    AttackPathOut,
    BlastRadiusOut,
    ToxicCombinationOut,
)
from .iac_schemas import (
    IaCFindingOut,
    IaCScanOut,
    IaCScanRequest,
    IaCWebhookConfigOut,
    IaCWebhookConfigRequest,
)
from .drift_schemas import (
    AnomalyOut,
    ConfigChangeHistoryOut,
    CorrelatedAlertOut,
    CorrelationRuleOut,
    CorrelationRuleRequest,
    DriftBaselineOut,
    DriftBaselineRequest,
    DriftEventOut,
)
from .policy_schemas import (
    CustomRuleOut,
    CustomRuleRequest,
    PolicyAuditLogOut,
    PolicyExceptionOut,
    PolicyExceptionRequest,
    PolicyHierarchyOut,
    PolicyHierarchyRequest,
    RuleTestOut,
    RuleTestRequest,
    RuleVersionOut,
)

__all__ = [
    # IAM
    "IAMAnalyzeRequest",
    "IAMIdentityOut",
    "IAMIdentityListOut",
    "EscalationPathOut",
    "CrossAccountTrustOut",
    "ServiceAccountOut",
    "DormantIdentityOut",
    # Attack Path
    "AttackPathAnalyzeRequest",
    "AttackPathOut",
    "AttackPathListOut",
    "BlastRadiusOut",
    "ToxicCombinationOut",
    # IaC
    "IaCScanRequest",
    "IaCScanOut",
    "IaCFindingOut",
    "IaCWebhookConfigRequest",
    "IaCWebhookConfigOut",
    # Drift
    "DriftEventOut",
    "DriftBaselineRequest",
    "DriftBaselineOut",
    "AnomalyOut",
    "CorrelationRuleRequest",
    "CorrelationRuleOut",
    "CorrelatedAlertOut",
    "ConfigChangeHistoryOut",
    # Policy
    "CustomRuleRequest",
    "CustomRuleOut",
    "RuleVersionOut",
    "PolicyHierarchyRequest",
    "PolicyHierarchyOut",
    "PolicyExceptionRequest",
    "PolicyExceptionOut",
    "PolicyAuditLogOut",
    "RuleTestRequest",
    "RuleTestOut",
]
