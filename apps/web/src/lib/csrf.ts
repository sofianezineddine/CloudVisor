/**
 * CSRF Token Utility
 *
 * Reads the cv_csrf cookie (non-HttpOnly, set by auth service)
 * and provides it for the double-submit cookie pattern.
 */

/**
 * Get a cookie value by name from document.cookie
 */
export function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * Get the CSRF token from the cv_csrf cookie.
 * This must be sent as X-CSRF-Token header on state-changing requests.
 */
export function getCsrfToken(): string | null {
  return getCookie('cv_csrf');
}

/**
 * Check if the user has an active session (cv_session cookie exists).
 * This is the ONLY way to check auth status without accessing HttpOnly tokens.
 */
export function hasSessionCookie(): boolean {
  if (typeof document === 'undefined') return false;
  return document.cookie.includes('cv_session=1');
}
