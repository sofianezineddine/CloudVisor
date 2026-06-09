"""Pydantic schemas for Auth service."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, EmailStr


class RegisterRequest(BaseModel):
    """Registration request."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    organization_name: str = Field(..., min_length=1, max_length=255)
    first_name: str | None = None
    last_name: str | None = None


class LoginRequest(BaseModel):
    """Login request."""

    email: EmailStr
    password: str
    mfa_code: str | None = None


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str | None = None


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class UserResponse(BaseModel):
    """User response."""

    id: str
    email: str
    first_name: str | None
    last_name: str | None
    organization_id: str
    role: str = "viewer"  # B-05 fix: populated from user_roles table, not hardcoded
    mfa_enabled: bool
    provider: str  # local, google, github, saml, oidc
    created_at: datetime


class UserProfileResponse(BaseModel):
    """User profile response."""

    id: str
    email: str
    first_name: str | None
    last_name: str | None
    organization: dict[str, Any]
    role: dict[str, Any] | None
    mfa_enabled: bool
    last_login_at: datetime | None


class MfaEnrollResponse(BaseModel):
    """MFA enrollment response."""

    secret: str
    qr_code: str


class MfaVerifyRequest(BaseModel):
    """MFA verification request."""

    code: str


class MfaBackupCodesResponse(BaseModel):
    """MFA backup codes response."""

    backup_codes: list[str]


class ApiKeyCreateRequest(BaseModel):
    """API key creation request."""

    name: str = Field(..., min_length=1, max_length=255)
    scopes: list[str] = Field(default_factory=lambda: ["read"])
    expires_at: datetime | None = None


class ApiKeyResponse(BaseModel):
    """API key response — used for list and detail views (key value is never included)."""

    id: str
    name: str
    scopes: list[str]
    expires_at: datetime | None
    created_at: datetime
    last_used_at: datetime | None = None
    is_active: bool = True


class ApiKeyCreatedResponse(BaseModel):
    """API key creation response — includes the key value (shown only once)."""

    id: str
    name: str
    key: str  # Only returned on creation/rotation — never again
    scopes: list[str]
    expires_at: datetime | None
    created_at: datetime


class ApiKeyListResponse(BaseModel):
    """API key list response."""

    keys: list[dict[str, Any]]


class RoleResponse(BaseModel):
    """Role response."""

    id: str
    name: str
    description: str | None
    permissions: list[str]
    is_builtin: bool
    is_default: bool


class RoleListResponse(BaseModel):
    """Role list response."""

    roles: list[RoleResponse]


class SessionResponse(BaseModel):
    """Session response."""

    id: str
    device_info: str | None
    ip_address: str | None
    last_active_at: datetime
    created_at: datetime


class SessionListResponse(BaseModel):
    """Session list response."""

    sessions: list[SessionResponse]


class AssignRoleRequest(BaseModel):
    """Assign role request."""

    role_id: str


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: str | None = None
