"use client";

import { useCallback } from "react";

/**
 * CloudVisor shim — replaces Keep's signOut with CloudVisor's logout flow.
 */
export function useSignOut() {
  return useCallback(() => {
    /* cleared by server via Set-Cookie max-age=0 */;
    /* cleared by server via Set-Cookie max-age=0 */;
    localStorage.removeItem('cloudvisor-user');
    window.location.href = '/login';
  }, []);
}
