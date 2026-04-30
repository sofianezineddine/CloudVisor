from .auth import router as auth_router
from .internal import router as internal_router
from .mfa import router as mfa_router
from .sessions import router as sessions_router
from .admin_auth import router as admin_router

__all__ = ["auth_router", "mfa_router", "sessions_router", "internal_router", "admin_router"]
