"""CloudVisor Auth Service.

Foundation 3 of the CloudVisor CNAPP platform - Multi-tenant authentication
and role-based access control.

## Overview

The Auth service is the identity and access control backbone of CloudVisor.
It handles:
- User authentication (email/password, OAuth, SAML, OIDC)
- Multi-factor authentication (TOTP)
- API key management
- Role-based access control (built-in + custom roles)
- Session management
- Audit logging

## Security Features

- Passwords: bcrypt with cost factor 12
- Tokens: JWT (RS256) with 15-min access, 30-day refresh
- MFA: TOTP with backup codes
- RLS: PostgreSQL Row-Level Security for tenant isolation

## Built-in Roles

| Role | Permissions |
|------|-------------|
| Owner | All (including billing, org deletion) |
| Admin | Security + user management |
| Security Engineer | Findings, policies, suppressions, reports |
| DevOps | CI/CD, IaC, read-only elsewhere |
| Viewer | Read-only across all modules |
| Auditor | Read-only + export compliance |

## API Endpoints

### Public
- POST /auth/register - Create account
- POST /auth/login - Login
- POST /auth/refresh - Refresh token

### Authenticated
- GET /auth/me - Current user
- POST /auth/mfa/enroll - Start MFA
- POST /auth/mfa/verify - Verify MFA
- GET /auth/sessions - List sessions
- DELETE /auth/sessions/{id} - Revoke session
- GET /auth/api-keys - List API keys
- POST /auth/api-keys - Create API key

### Internal (mTLS)
- POST /internal/auth/validate - Validate token
- POST /internal/auth/authorize - Check permission
- GET /internal/auth/org/{id} - Get org details
"""

from .main import app

__version__ = "1.0.0"
__all__ = ["app"]
