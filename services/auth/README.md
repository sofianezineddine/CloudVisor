# CloudVisor Auth Service

Multi-Tenant Authentication & RBAC Service for the CloudVisor CNAPP Platform.

## Quick Start

### Run with Docker Compose (Recommended)

```bash
# Build and start all services including auth
docker-compose up -d --build auth-service

# View logs
docker-compose logs -f auth-service

# Check health
curl http://localhost:8002/health
```

### Run Locally (Development)

```bash
# Install dependencies
cd services/auth
pip install -r requirements.txt

# Install shared utils package
pip install -e ../../packages/utils

# Start the service
python -m uvicorn main:app --reload --port 8002
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/register` | POST | Register new user + organization |
| `/auth/login` | POST | Login with email/password |
| `/auth/refresh` | POST | Refresh access token |
| `/auth/logout` | POST | Logout and invalidate session |
| `/auth/me` | GET | Get current user profile |
| `/auth/mfa/enroll` | POST | Enroll in MFA |
| `/auth/mfa/verify` | POST | Verify MFA code |
| `/auth/sessions` | GET | List active sessions |
| `/auth/api-keys` | GET/POST | Manage API keys |
| `/admin/auth/login` | POST | Admin login |
| `/admin/auth/me` | GET | Get admin profile |
| `/health` | GET | Health check |
| `/ready` | GET | Readiness check |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_URL` | PostgreSQL connection string | `postgresql+asyncpg://cvadmin:cvpassword@localhost:5432/cloudvisor` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `AUTH_SECRET_KEY` | JWT signing secret | `change-me-in-production-min-32-chars!` |
| `AUTH_ALGORITHM` | JWT algorithm | `HS256` |
| `AUTH_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token expiry | `15` |
| `AUTH_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token expiry | `30` |
| `AUTH_CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000,http://localhost:3001` |
| `AUTH_OAUTH_GOOGLE_ENABLED` | Enable Google OAuth | `false` |
| `AUTH_OAUTH_GOOGLE_CLIENT_ID` | Google OAuth client ID | |
| `AUTH_OAUTH_GOOGLE_CLIENT_SECRET` | Google OAuth client secret | |
| `AUTH_OAUTH_GITHUB_ENABLED` | Enable GitHub OAuth | `false` |
| `AUTH_OAUTH_GITHUB_CLIENT_ID` | GitHub OAuth client ID | |
| `AUTH_OAUTH_GITHUB_CLIENT_SECRET` | GitHub OAuth client secret | |

## Default Admin User

When the service starts, a default admin user is created:

- **Email:** `admin@cloudvisor.io`
- **Password:** `AdminPass123!`
- **Role:** `super_admin`

## Database Tables

| Table | Purpose |
|-------|---------|
| `admins` | Platform admin users |
| `admin_sessions` | Admin sessions |
| `organizations` | Tenant organizations |
| `users` | Tenant users |
| `cv_clients` | Client registry |
| `roles` | RBAC roles |
| `sessions` | User sessions |
| `api_keys` | API keys |
| `audit_log` | Auth event audit trail |
