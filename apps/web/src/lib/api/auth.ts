/**
 * Auth Service API Client
 *
 * All auth-related operations call the auth service directly at :8002.
 * This is intentional — auth is NOT proxied through the API gateway (:8005)
 * because it handles token issuance and must be called before a valid token exists.
 *
 * Endpoint coverage (50 backend routes):
 *
 * ✅ POST   /auth/register
 * ✅ POST   /auth/login
 * ✅ POST   /auth/refresh
 * ✅ POST   /auth/logout
 * ✅ POST   /auth/forgot-password
 * ✅ POST   /auth/reset-password
 * ✅ GET    /auth/me
 * ✅ PATCH  /auth/me
 * ✅ POST   /auth/password
 * ✅ GET    /auth/oauth/{provider}/authorize  (browser redirect — no fetch needed)
 * ✅ GET    /auth/callback/{provider}          (browser redirect — no fetch needed)
 * ✅ POST   /auth/oauth/exchange
 * ✅ GET    /auth/sessions
 * ✅ DELETE /auth/sessions/{id}
 * ✅ GET    /auth/api-keys
 * ✅ POST   /auth/api-keys
 * ✅ DELETE /auth/api-keys/{id}
 * ✅ POST   /auth/api-keys/{id}/rotate
 * ✅ POST   /auth/mfa/enroll
 * ✅ POST   /auth/mfa/verify
 * ✅ POST   /auth/mfa/validate
 * ✅ GET    /auth/mfa/backup-codes            (returns 410 — intentional)
 * ✅ POST   /auth/mfa/backup-codes/regenerate
 * ✅ DELETE /auth/mfa/disable
 * ✅ GET    /auth/org/me
 * ✅ PATCH  /auth/org/me
 * ✅ POST   /auth/org/me/plan
 * ✅ DELETE /auth/org/me
 * ✅ GET    /auth/org/me/members
 * ✅ POST   /auth/org/me/members/invite
 * ✅ DELETE /auth/org/me/members/{id}
 * ✅ PATCH  /auth/org/me/members/{id}/role
 * ✅ GET    /auth/org/me/audit-log
 * ✅ GET    /auth/sso/saml/login              (browser redirect — no fetch needed)
 * ✅ POST   /auth/sso/saml/acs                (browser redirect — no fetch needed)
 * ✅ GET    /auth/sso/saml/metadata
 * ✅ POST   /auth/sso/saml/configure
 * ✅ GET    /auth/sso/oidc/login              (browser redirect — no fetch needed)
 * ✅ GET    /auth/sso/oidc/callback           (browser redirect — no fetch needed)
 * ✅ POST   /auth/sso/oidc/configure
 * ✅ POST   /admin/auth/login
 * ✅ POST   /admin/auth/refresh
 * ✅ POST   /admin/auth/logout
 * ✅ GET    /admin/auth/me
 * —  POST   /internal/auth/validate           (internal — called by API gateway, not frontend)
 * —  POST   /internal/auth/authorize          (internal — called by API gateway, not frontend)
 * —  GET    /internal/auth/org/{id}           (internal — called by API gateway, not frontend)
 * —  GET    /internal/auth/org/{id}/roles     (internal — called by API gateway, not frontend)
 * —  POST   /internal/auth/org/{id}/roles     (internal — called by API gateway, not frontend)
 * —  POST   /internal/auth/users/{id}/role    (internal — called by API gateway, not frontend)
 */

const API_BASE_URL = ''; // Relative URLs — proxy (nginx/Next.js rewrite) handles routing

function getAdminToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('admin_access_token');
}

/**
 * Shared silent token refresh using HttpOnly cookies.
 * Server reads cv_refresh cookie and sets new cv_access cookie.
 * Uses relative URL (same origin via nginx proxy) — works in dev and production.
 * This is exported for use by all API clients across the codebase.
 */
export async function refreshSession(): Promise<boolean> {
  try {
    const res = await fetch('/auth/refresh', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (res.ok) {
      // Renew the JS-readable session indicator cookie
      document.cookie = 'cv_session=1; path=/; max-age=3600; samesite=lax';
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

/** Authenticated fetch to the auth service.
 *  All services are behind nginx on the same origin — cookies work natively. */
async function authFetch(path: string, options: RequestInit = {}, _retry = true): Promise<any> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include', // Same-origin cookies sent automatically
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  // On 401, try refresh (server reads cv_refresh cookie, sets new cv_access cookie)
  if (res.status === 401 && _retry) {
    const refreshRes = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (refreshRes.ok) {
      return authFetch(path, options, false);
    }
    throw new Error('Session expired. Please sign in again.');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

/** Authenticated fetch using the admin access token. */
async function adminFetch(path: string, options: RequestInit = {}): Promise<any> {
  const token = getAdminToken();
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const authAPI = {
  // ─── Authentication ────────────────────────────────────────────────────────

  /** POST /auth/register — create new user + org */
  register: async (data: {
    email: string;
    password: string;
    organization_name: string;
    first_name: string;
    last_name: string;
  }) => {
    const res = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Registration failed'); }
    return res.json();
  },

  /** POST /auth/login — email + password (+ optional MFA code). Server sets HttpOnly cookies. */
  login: async (data: { email: string; password: string; mfa_code?: string }) => {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      credentials: 'include', // Receive Set-Cookie from server
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Login failed'); }
    return res.json();
  },

  /** POST /auth/refresh — server reads refresh cookie, sets new cookies */
  refreshToken: async (_refreshToken?: string) => {
    const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      credentials: 'include', // Send cv_refresh cookie, receive new cookies
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}), // Body not needed, server reads cookie
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Token refresh failed'); }
    return res.json();
  },

  /** POST /auth/logout — server clears HttpOnly cookies */
  logout: async () => {
    const res = await fetch(`${API_BASE_URL}/auth/logout`, {
      method: 'POST',
      credentials: 'include', // Send cookies so server can identify session
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Logout failed'); }
    return res.json();
  },

  /** GET /auth/me — current user profile (cookie-authenticated) */
  getCurrentUser: async () => {
    const res = await fetch(`${API_BASE_URL}/auth/me`, {
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Failed to fetch user'); }
    return res.json();
  },

  /** PATCH /auth/me — update first_name / last_name */
  updateProfile: async (data: { first_name?: string; last_name?: string }) =>
    authFetch('/auth/me', { method: 'PATCH', body: JSON.stringify(data) }),

  /** POST /auth/password — change password (requires current_password) */
  changePassword: async (data: { current_password: string; new_password: string }) =>
    authFetch('/auth/password', { method: 'POST', body: JSON.stringify(data) }),

  /** POST /auth/forgot-password — send password reset email */
  forgotPassword: async (email: string) => {
    const res = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Failed to send reset email'); }
    return res.json();
  },

  /** POST /auth/reset-password — consume reset token and set new password */
  resetPassword: async (token: string, password: string) => {
    const res = await fetch(`${API_BASE_URL}/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, password }),
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Failed to reset password'); }
    return res.json();
  },

  // ─── OAuth ─────────────────────────────────────────────────────────────────
  // GET /auth/oauth/{provider}/authorize — browser redirect, no fetch needed
  // GET /auth/callback/{provider}         — browser redirect, no fetch needed

  /** POST /auth/oauth/exchange — exchange one-time code, server sets HttpOnly cookies */
  exchangeOAuthCode: async (code: string) => {
    const res = await fetch(`${API_BASE_URL}/auth/oauth/exchange`, {
      method: 'POST',
      credentials: 'include', // Receive Set-Cookie from server
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Token exchange failed'); }
    return res.json();
  },

  // ─── Sessions ──────────────────────────────────────────────────────────────

  /** GET /auth/sessions — list active sessions */
  getSessions: async () => authFetch('/auth/sessions'),

  /** DELETE /auth/sessions/{id} — revoke a specific session */
  revokeSession: async (sessionId: string) =>
    authFetch(`/auth/sessions/${sessionId}`, { method: 'DELETE' }),

  // ─── API Keys ──────────────────────────────────────────────────────────────

  /** GET /auth/api-keys — list all API keys (no key values) */
  getApiKeys: async () => authFetch('/auth/api-keys'),

  /** POST /auth/api-keys — create new API key (returns key value once) */
  createApiKey: async (data: { name: string; scopes?: string[]; expires_at?: string }) =>
    authFetch('/auth/api-keys', { method: 'POST', body: JSON.stringify(data) }),

  /** DELETE /auth/api-keys/{id} — revoke an API key */
  revokeApiKey: async (keyId: string) =>
    authFetch(`/auth/api-keys/${keyId}`, { method: 'DELETE' }),

  /** POST /auth/api-keys/{id}/rotate — rotate an API key (returns new key value once) */
  rotateApiKey: async (keyId: string) =>
    authFetch(`/auth/api-keys/${keyId}/rotate`, { method: 'POST' }),

  // ─── MFA ───────────────────────────────────────────────────────────────────

  /** POST /auth/mfa/enroll — begin MFA enrollment, returns QR code + secret */
  enrollMfa: async () => authFetch('/auth/mfa/enroll', { method: 'POST' }),

  /** POST /auth/mfa/verify — confirm enrollment with TOTP code, returns backup codes */
  verifyMfaEnrollment: async (code: string) =>
    authFetch('/auth/mfa/verify', { method: 'POST', body: JSON.stringify({ code }) }),

  /** POST /auth/mfa/validate — validate TOTP code during login */
  validateMfa: async (code: string) =>
    authFetch('/auth/mfa/validate', { method: 'POST', body: JSON.stringify({ code }) }),

  /** DELETE /auth/mfa/disable — disable MFA (requires current TOTP code) */
  disableMfa: async (code: string) =>
    authFetch('/auth/mfa/disable', { method: 'DELETE', body: JSON.stringify({ code }) }),

  /** POST /auth/mfa/backup-codes/regenerate — regenerate backup codes (requires TOTP) */
  regenerateBackupCodes: async (code: string) =>
    authFetch('/auth/mfa/backup-codes/regenerate', {
      method: 'POST',
      body: JSON.stringify({ code }),
    }),

  // ─── Organization ──────────────────────────────────────────────────────────

  /** GET /auth/org/me — get current org details + plan + feature flags */
  getOrg: async () => authFetch('/auth/org/me'),

  /** PATCH /auth/org/me — update org name or billing email */
  updateOrg: async (data: { name?: string; billing_email?: string }) =>
    authFetch('/auth/org/me', { method: 'PATCH', body: JSON.stringify(data) }),

  /** POST /auth/org/me/plan — change org plan (owner only) */
  changePlan: async (plan: string) =>
    authFetch('/auth/org/me/plan', { method: 'POST', body: JSON.stringify({ plan }) }),

  /** DELETE /auth/org/me — delete org with full cascade (owner only) */
  deleteOrg: async () => authFetch('/auth/org/me', { method: 'DELETE' }),

  // ─── Team / Members ────────────────────────────────────────────────────────

  /** GET /auth/org/me/members — list all org members with roles */
  getMembers: async () => authFetch('/auth/org/me/members'),

  /** POST /auth/org/me/members/invite — invite a new member */
  inviteMember: async (data: {
    email: string;
    role: string;
    first_name?: string;
    last_name?: string;
  }) =>
    authFetch('/auth/org/me/members/invite', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  /** DELETE /auth/org/me/members/{id} — remove a member */
  removeMember: async (memberId: string) =>
    authFetch(`/auth/org/me/members/${memberId}`, { method: 'DELETE' }),

  /** PATCH /auth/org/me/members/{id}/role — change a member's role */
  updateMemberRole: async (memberId: string, role: string) =>
    authFetch(`/auth/org/me/members/${memberId}/role`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    }),

  // ─── Audit Log ─────────────────────────────────────────────────────────────

  /** GET /auth/org/me/audit-log — paginated audit log with filters */
  getAuditLog: async (params?: {
    limit?: number;
    offset?: number;
    event_type?: string;
    user_id?: string;
    since?: string;
    until?: string;
  }) => {
    const q = new URLSearchParams();
    if (params?.limit !== undefined) q.set('limit', String(params.limit));
    if (params?.offset !== undefined) q.set('offset', String(params.offset));
    if (params?.event_type) q.set('event_type', params.event_type);
    if (params?.user_id) q.set('user_id', params.user_id);
    if (params?.since) q.set('since', params.since);
    if (params?.until) q.set('until', params.until);
    const qs = q.toString();
    return authFetch(`/auth/org/me/audit-log${qs ? `?${qs}` : ''}`);
  },

  // ─── SSO ───────────────────────────────────────────────────────────────────
  // GET /auth/sso/saml/login    — browser redirect, no fetch needed
  // POST /auth/sso/saml/acs     — browser redirect, no fetch needed
  // GET /auth/sso/oidc/login    — browser redirect, no fetch needed
  // GET /auth/sso/oidc/callback — browser redirect, no fetch needed

  /** GET /auth/sso/saml/metadata — SAML SP metadata XML for IdP configuration */
  getSamlMetadata: async (orgId: string) => {
    const res = await fetch(`${API_BASE_URL}/auth/sso/saml/metadata?org_id=${encodeURIComponent(orgId)}`);
    if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed to fetch SAML metadata'); }
    return res.text(); // Returns XML
  },

  /** POST /auth/sso/saml/configure — save SAML config for org (admin/owner only) */
  configureSaml: async (orgId: string, config: {
    idp_entity_id: string;
    idp_sso_url: string;
    idp_cert: string;
    sp_entity_id?: string;
    acs_url?: string;
  }) =>
    authFetch(`/auth/sso/saml/configure?org_id=${encodeURIComponent(orgId)}`, {
      method: 'POST',
      body: JSON.stringify(config),
    }),

  /** POST /auth/sso/oidc/configure — save OIDC config for org (admin/owner only) */
  configureOidc: async (orgId: string, config: {
    issuer: string;
    client_id: string;
    client_secret: string;
    scopes?: string;
  }) =>
    authFetch(`/auth/sso/oidc/configure?org_id=${encodeURIComponent(orgId)}`, {
      method: 'POST',
      body: JSON.stringify(config),
    }),

  // ─── Admin Auth ────────────────────────────────────────────────────────────

  /** POST /admin/auth/login — platform admin login */
  adminLogin: async (email: string, password: string) => {
    const res = await fetch(`${API_BASE_URL}/admin/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Admin login failed'); }
    return res.json();
  },

  /** POST /admin/auth/refresh — refresh admin access token */
  adminRefreshToken: async (refreshToken: string) => {
    const res = await fetch(`${API_BASE_URL}/admin/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Admin token refresh failed'); }
    return res.json();
  },

  /** POST /admin/auth/logout — admin logout */
  adminLogout: async () => adminFetch('/admin/auth/logout', { method: 'POST' }),

  /** GET /admin/auth/me — current admin user profile */
  getAdminUser: async () => adminFetch('/admin/auth/me'),
};
