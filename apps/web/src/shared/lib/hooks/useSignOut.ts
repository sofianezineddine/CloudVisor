"use client";

import { useCallback } from "react";

/**
 * CloudVisor shim — replaces Keep's signOut with CloudVisor's logout flow.
 */
export function useSignOut() {
  return useCallback(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('cloudvisor-user');
    window.location.href = '/login';
  }, []);
}
