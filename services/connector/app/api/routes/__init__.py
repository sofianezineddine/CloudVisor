"""API routes for the Connector service."""

from .accounts import router as accounts_router
from .onboarding import router as onboarding_router
from .resources import router as resources_router

__all__ = ["accounts_router", "onboarding_router", "resources_router"]
