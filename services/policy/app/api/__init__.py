from .routes.policy import router as policy_router
from .routes.compliance import router as compliance_router
from .routes.internal import router as internal_router

__all__ = ["policy_router", "compliance_router", "internal_router"]
