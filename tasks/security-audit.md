# CloudVisor Security Audit Report

**Date:** May 21, 2026
**Scope:** All services except `keep/` and `n8n/`
**Auditor:** Codebuff AI

---

## 🔴 CRITICAL FINDINGS

### C-01: JWT Tokens Stored in localStorage (XSS-Vulnerable)
**Severity:** CRITICAL  
**Files:** `apps/web/src/hooks/use-auth.tsx`, `apps/web/src/lib/api/auth.ts`, `apps/web/src/shared/api/ApiClient.ts`, `apps/web/src/lib/api/keep.ts`

**Issue:** Access and refresh tokens are stored in `localStorage` under keys `access_token` and `refresh_token`. localStorage is accessible to ANY JavaScript executing on the same origin. A single XSS vulnerability anywhere in the frontend would allow an attacker to exfiltrate all tokens, gaining persistent access to the victim's account.

The code has a dual auth approach — HttpOnly cookies AND localStorage tokens — which undermines the security of HttpOnly cookies. The localStorage fallback was added to handle cross-origin cookie issues (auth service on port 8002, frontend on port 3000).

**Evidence:**
```typescript
// use-auth.tsx
function hasSession(): boolean {
  return document.cookie.includes('cv_session=1') || 
    !!localStorage.getItem('access_token');  // ← CRITICAL
}

// login:
localStorage.setItem('access_token', response.access_token);
localStorage.setItem('refresh_token', response.refresh_token);

// auth.ts - every API call sends token from localStorage:
Authorization: Bearer ${localStorage.getItem('access_token')}
```

**Recommendation:**
- Use a reverse proxy (nginx/Caddy) so the auth service and frontend share the same origin (e.g., `/api/auth` proxied to auth service on port 8002)
- Eliminate all localStorage token storage — rely solely on HttpOnly cookies
- The `cv_session` cookie (non-HttpOnly indicator) is acceptable but must not carry secrets

---

### C-02: PostgreSQL and Neo4j Credentials in Plaintext in docker-compose.yml
**Severity:** CRITICAL  
**File:** `docker-compose.yml`

**Issue:** Database credentials are hardcoded in docker-compose.yml:
- `POSTGRES_PASSWORD: cvpassword`
- `NEO4J_AUTH: "neo4j/password"`
- All service connection strings embed these credentials

This file is committed to git history. Anyone with access to the repository has production database credentials.

**Recommendation:**
- Use Docker secrets or environment variable substitution with `.env` files
- Never hardcode credentials in compose files
- Rotate all credentials if this has been in a public repository

---

### C-03: Elasticsearch Runs Without Authentication
**Severity:** CRITICAL  
**File:** `docker-compose.yml`

**Issue:** `xpack.security.enabled=false` — Elasticsearch is completely open with no authentication. Anyone who can reach port 9200 can read/write all indices, including potentially sensitive scan data.

**Recommendation:**
- Enable Elasticsearch security features
- Set up built-in user authentication
- Use TLS for transport encryption

---

### C-04: Kafka Uses PLAINTEXT (No Encryption or Authentication)
**Severity:** CRITICAL  
**File:** `docker-compose.yml`

**Issue:** Kafka is configured with `PLAINTEXT` listener — no TLS encryption, no SASL authentication. All inter-service messages (including audit events, findings, alerts) travel unencrypted over the Docker network. Anyone with container access can eavesdrop on or inject messages.

**Recommendation:**
- Configure Kafka with SSL/TLS encryption
- Enable SASL/SCRAM authentication
- Use ACLs for topic-level authorization

---

## 🔴 HIGH SEVERITY FINDINGS

### H-01: Rate Limiter Fails Open When Redis Is Down
**Severity:** HIGH  
**File:** `services/auth/app/services/rate_limiter.py`

**Issue:** When Redis is unavailable, `_check()` catches the exception and returns `True` (allow):
```python
except Exception as e:
    logger.warning(f"Rate limiter Redis error (fail open): {e}")
    return True  # ← FAILS OPEN
```

This means any Redis outage completely disables rate limiting — attackers can brute-force credentials, spam registrations, and trigger password reset emails without restriction.

**Recommendation:** Fail closed (deny) when Redis is unavailable, especially for login and password reset rate limits.

---

### H-02: No Session Cleanup / Stale Session Accumulation
**Severity:** HIGH  
**Files:** `services/auth/app/services/auth_service.py`, `services/auth/app/models/auth.py`

**Issue:** Sessions are never purged from the database. Expired/inactive sessions remain forever, causing unbounded table growth. There is no background job to clean up expired sessions.

Session tokens are also not explicitly blacklisted or checked for expiry in a centralized way — they rely on the `is_active` flag being set to `False`.

**Recommendation:**
- Add a scheduled cleanup job (e.g., `DELETE FROM sessions WHERE expires_at < NOW() - INTERVAL '30 days'`)
- Consider a session revocation bloom filter for O(1) checks

---

### H-03: No Email Verification on Registration
**Severity:** HIGH  
**Files:** `services/auth/app/services/auth_service.py`, `services/auth/app/api/routes/auth.py`

**Issue:** Users can register and immediately receive tokens without verifying their email address. This enables:
- Signup with arbitrary email addresses (e.g., `victim@company.com`)
- Resource exhaustion by creating unlimited disposable accounts
- Potential abuse of free-tier resources

**Recommendation:**
- Implement email verification flow (send verification link on registration)
- Mark users as `email_verified=false` until they confirm
- Allow limited functionality (e.g., read-only) until email is verified

---

### H-04: No Input Sanitization on User Profile Fields
**Severity:** HIGH  
**File:** `services/auth/app/api/routes/auth.py` (`PATCH /auth/me`)

**Issue:** `first_name` and `last_name` fields are stored and returned without any sanitization or encoding. If these values are rendered anywhere in the UI without proper escaping, this creates a stored XSS vector.

**Recommendation:**
- Strip HTML tags from name fields on input
- Validate length (currently no max-length enforcement beyond DB column)
- Apply output encoding when rendering in UI

---

### H-05: Internal Service Auth Uses Shared Secret, Not mTLS
**Severity:** HIGH  
**File:** `services/auth/app/api/routes/internal.py`

**Issue:** The spec requires "zero-trust (mTLS)" but implementation uses a shared secret (`AUTH_INTERNAL_SERVICE_TOKEN`) passed as an HTTP header. Additionally, when the env var is not set, the code logs a warning but ALLOWS all requests:

```python
if not _INTERNAL_SERVICE_TOKEN:
    logging.getLogger("auth.internal").warning(
        "AUTH_INTERNAL_SERVICE_TOKEN not set — internal endpoints are unprotected."
    )
    return  # ← ALLOWS ALL
```

**Recommendation:**
- Implement mTLS with per-service certificates
- Fail closed when `AUTH_INTERNAL_SERVICE_TOKEN` is not configured
- Never default to "allow all" when security config is missing

---

### H-06: Vault Without TLS and Static Token on Shared Volume
**Severity:** HIGH  
**Files:** `docker-compose.yml`, `services/connector/app/services/vault_client.py`

**Issue:**
1. Vault is accessed via HTTP (no TLS) — anyone on the Docker network can intercept secrets
2. Vault token is stored in a shared volume (`/vault/data/vault_token`) readable by the connector container
3. Vault root token is used for all operations instead of wrapped tokens or AppRole

**Recommendation:**
- Enable TLS on Vault
- Use Vault AppRole or Kubernetes auth method instead of shared token files
- Apply Vault policies with least privilege per service

---

## 🟡 MEDIUM SEVERITY FINDINGS

### M-01: CSRF Cookie Is Not HttpOnly (Double-Submit Pattern)
**Severity:** MEDIUM  
**File:** `apps/web/src/lib/csrf.ts`

**Issue:** The `cv_csrf` cookie is not HttpOnly, so JavaScript can read it. This is by design (double-submit cookie pattern), but if an XSS vulnerability exists, the attacker can read the CSRF token. Combined with localStorage token exposure (C-01), this provides no additional protection.

**Recommendation:**
- This is acceptable only if C-01 is fixed (remove localStorage tokens)
- Consider SameSite=Strict on the CSRF cookie when not needed for cross-origin
- Alternatively, use a CSRF token embedded in the HTML/API response rather than a readable cookie

---

### M-02: Password Reset Token Not Rate-Limited Per IP
**Severity:** MEDIUM  
**File:** `services/auth/app/api/routes/auth.py` (`POST /auth/forgot-password`)

**Issue:** Password reset requests are rate-limited per email (3/hr) but not per IP. This means an attacker can:
- Spam password reset emails to many different addresses from a single IP
- Use this for email bombing attacks

**Recommendation:**
- Add IP-based rate limiting to forgot-password endpoint (e.g., 10/hr/IP)
- Consider CAPTCHA for password reset requests

---

### M-03: OAuth Redirect URI Not Whitelist-Validated
**Severity:** MEDIUM  
**File:** `services/auth/app/api/routes/auth.py`

**Issue:** The OAuth redirect_uri is constructed server-side from `FRONTEND_URL` env var, which is better than accepting it from the client. However, there's no validation against a whitelist of allowed redirect URIs. If `FRONTEND_URL` is misconfigured or compromised, OAuth tokens could be redirected.

**Recommendation:**
- Maintain a whitelist of allowed redirect URIs
- Validate redirect_uri against the whitelist on every OAuth flow

---

### M-04: CORS Configuration Exposes Multiple Localhost Origins in Production
**Severity:** MEDIUM  
**File:** `services/auth/main.py`

**Issue:** The CORS middleware allows `["*"]` for methods and headers, plus exposes all headers. The origins list includes 6 localhost variants beyond the configured origin. While this is typical for development, it increases attack surface.

**Recommendation:**
- Tighten CORS origins to only the configured value in production
- Remove `expose_headers=["*"]` — expose only needed headers
- Only allow specific methods, not `["*"]`

---

### M-05: No Certificate Validation in HTTPX Calls (OAuth Token Exchange)
**Severity:** MEDIUM  
**File:** `services/auth/app/api/routes/auth.py` (OAuth callback)

**Issue:** HTTPX async client calls to OAuth providers and userinfo endpoints don't explicitly verify certificates. While Python's default SSL context does verify by default, the code doesn't pin certificates or verify against known fingerprints.

**Recommendation:**
- Add explicit SSL verification with certificate pinning
- Set a timeout on all HTTPX calls (currently not set, could hang indefinitely)

---

### M-06: Kafka Topics Auto-Create Enabled in Production
**Severity:** MEDIUM  
**File:** `docker-compose.yml`

**Issue:** `KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"` allows any topic to be created automatically by any producer. A compromised service could create unexpected topics or produce to misspelled topic names.

**Recommendation:**
- Set `KAFKA_AUTO_CREATE_TOPICS_ENABLE: "false"` in production
- Pre-create all required topics via init container or scripts

---

### M-07: Missing SQL Injection Protections in User Repository
**Severity:** MEDIUM  
**File:** `services/auth/app/repositories/user_repository.py`

**Issue:** While SQLAlchemy provides parameterized queries by default, there are a few areas where dynamic inputs are passed without explicit validation. The `create(**kwargs)` pattern could allow unexpected column injection.

**Recommendation:**
- Use Pydantic models to validate all inputs before passing to ORM
- Avoid `**kwargs` patterns in repository methods

---

### M-08: MFA Backup Code Column Type Mismatch
**Severity:** MEDIUM  
**File:** `services/auth/app/models/auth.py`

**Issue:** The `mfa_backup_codes` field is typed as `JSON` column in the ORM model, but treated as both `TEXT` (comma-separated string in some code paths) and `JSON` (in others). This inconsistency could cause serialization issues or data corruption.

**Recommendation:**
- Standardize on a single storage format (JSON array of bcrypt hashes)
- Remove the comma-separated fallback code path

---

### M-09: No Global Request Size Limits
**Severity:** MEDIUM  
**Files:** All service `main.py` files

**Issue:** None of the FastAPI applications have request body size limits configured. An attacker could send multi-gigabyte payloads, causing memory exhaustion.

**Recommendation:**
- Add `max_request_size` middleware or FastAPI body limit (e.g., `max_size=10_000_000` for 10MB)
- Set upload limits per endpoint

---

## 🟢 LOW SEVERITY FINDINGS

### L-01: Health Endpoints Return No Useful Diagnostics
**Files:** All service `main.py` files

**Issue:** `/health` and `/ready` endpoints return static responses without verifying actual downstream dependencies (DB, Redis, Kafka). A service could report "healthy" while its database connection pool is exhausted.

**Recommendation:**
- Implement proper health checks that verify DB connectivity, Redis ping, Kafka producer status
- Add `/ready` that checks all dependencies before returning 200

---

### L-02: No OpenAPI/Swagger Protection in Production
**Files:** All service `main.py` files

**Issue:** FastAPI's `/docs` and `/redoc` endpoints are enabled in all environments. This exposes the full internal API schema, including internal endpoints, in production.

**Recommendation:**
- Disable `/docs` in production or protect with authentication
- Use separate `docs_url=None` in production FastAPI constructor

---

### L-03: Missing Pagination on Audit Log List Endpoint (Frontend)
**File:** `apps/web/src/lib/api/auth.ts`

**Issue:** The audit log endpoint supports pagination parameters, but the frontend does not pass pagination in typical usage. Large orgs with extensive audit logs could experience slow responses or timeouts.

**Recommendation:**
- Default to reasonable page size (e.g., 100)
- Implement cursor-based pagination for audit logs

---

### L-04: No Request Timeout on authFetch
**File:** `apps/web/src/lib/api/auth.ts`

**Issue:** The `authFetch` helper doesn't set a timeout on fetch requests. If the auth service is slow or unresponsive, requests can hang indefinitely in the browser.

**Recommendation:**
- Add `AbortController` with a 30-second timeout to all fetch calls

---

### L-05: console.error Exposes Internal Details
**File:** `apps/web/src/shared/api/ApiClient.ts`

**Issue:** `console.error(error)` logs caught errors to the browser console, potentially exposing internal details to users.

**Recommendation:**
- Remove or sanitize error details before logging to console

---

## ✅ POSITIVE SECURITY CONTROLS (Already Implemented)

The following security best practices are already in place:

| Control | Details |
|---------|---------|
| **Password Hashing** | bcrypt with 12 rounds, executed in thread pool to avoid blocking event loop |
| **Rate Limiting** | Login (10/min/IP), Password Reset (3/hr/email), Registration (5/hr/IP) |
| **Account Lockout** | Escalating: 15min → 1hr → 24hr after 5/10/20 failures |
| **JWT** | Supports RS256 (asymmetric) with HS256 fallback |
| **Refresh Token Rotation** | Old token invalidated on each refresh |
| **Session Invalidation** | All sessions force-expired on password change |
| **OAuth State Nonce** | Cryptographically random, Redis-stored, single-use, 10min TTL |
| **OAuth One-Time Exchange Code** | Tokens never in URL fragments (120s Redis TTL, single-use) |
| **Backup Codes** | Bcrypt-hashed, single-use, consumed immediately |
| **Audit Logging** | Extensive: login, logout, token refresh, API key lifecycle, MFA events |
| **API Key Hashing** | SHA-256 hashed at rest, value returned only on creation/rotation |
| **Per-Key Rate Limiting** | Redis-based, configurable per API key |
| **Security Headers** | X-Content-Type-Options, X-Frame-Options, HSTS (prod), Referrer-Policy, Cache-Control |
| **Docker Non-Root** | All containers use non-root `appuser` |
| **Enterprise MFA Enforcement** | Configurable enforcement for growth/enterprise orgs |
| **Internal Service Token** | X-Service-Token required for inter-service calls |
| **CORS Configuration** | Configured origins with credentials support |
| **CSRF Protection** | Double-submit cookie pattern (X-CSRF-Token + cv_csrf cookie) |
| **Paginated Endpoints** | All list endpoints support limit/offset |
| **Health Checks** | Docker-level health checks on all services |

---

## SUMMARY

| Severity | Count | Key Issues |
|----------|-------|------------|
| 🔴 CRITICAL | 4 | localStorage tokens (XSS), plaintext DB creds in git, Elasticsearch no auth, Kafka no encryption |
| 🔴 HIGH | 6 | Rate limiter fails open, stale sessions, no email verification, no input sanitization, shared-secret internal auth, vault without TLS |
| 🟡 MEDIUM | 9 | CSRF cookie exposure, no IP-based reset limiting, CORS looseness, OAuth redirect whitelist missing, etc. |
| 🟢 LOW | 5 | Health checks, Swagger exposure, missing timeouts, etc. |

**Top 3 priorities for immediate remediation:**
1. **C-01**: Remove localStorage token storage — use a reverse proxy for same-origin cookie auth
2. **C-02**: Move database credentials from docker-compose.yml to `.env` files/Docker secrets
3. **H-01**: Make rate limiter fail closed when Redis is unavailable

---

*Generated by Codebuff Security Audit*
