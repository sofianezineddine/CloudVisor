"""CSPM extended database models for all five modules."""

from .iam_models import (
    IAMAnalysisResultModel,
    IAMCrossAccountTrustModel,
    IAMEscalationPathModel,
    IAMServiceAccountModel,
)
from .attack_path_models import (
    AttackPathModel,
    ToxicCombinationModel,
)
from .iac_models import (
    IaCScanModel,
    IaCFindingModel,
    IaCWebhookConfigModel,
)
from .drift_models import (
    DriftBaselineModel,
    DriftEventModel,
    ConfigChangeHistoryModel,
    BehavioralBaselineModel,
    AnomalyFindingModel,
    CorrelationRuleModel,
    CorrelatedAlertModel,
)
from .policy_models import (
    CustomRegoRuleModel,
    RegoRuleVersionModel,
    PolicyHierarchyModel,
    PolicyExceptionModel,
    PolicyAuditLogModel,
)

__all__ = [
    # IAM
    "IAMAnalysisResultModel",
    "IAMCrossAccountTrustModel",
    "IAMEscalationPathModel",
    "IAMServiceAccountModel",
    # Attack Path
    "AttackPathModel",
    "ToxicCombinationModel",
    # IaC
    "IaCScanModel",
    "IaCFindingModel",
    "IaCWebhookConfigModel",
    # Drift
    "DriftBaselineModel",
    "DriftEventModel",
    "ConfigChangeHistoryModel",
    "BehavioralBaselineModel",
    "AnomalyFindingModel",
    "CorrelationRuleModel",
    "CorrelatedAlertModel",
    # Policy
    "CustomRegoRuleModel",
    "RegoRuleVersionModel",
    "PolicyHierarchyModel",
    "PolicyExceptionModel",
    "PolicyAuditLogModel",
]
