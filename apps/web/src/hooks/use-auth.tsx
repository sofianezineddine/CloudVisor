'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authAPI } from '@/lib/api/auth';

interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  organization_id: string;
  organization_name?: string;
  role?: string;
  mfa_enabled: boolean;
  provider: 'local' | 'google' | 'github' | 'saml' | 'oidc';
  created_at?: string;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string, mfaCode?: string) => Promise<void>;
  register: (data: {
    email: string;
    password: string;
    organization_name: string;
    first_name: string;
    last_name: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

// ─── Cookie-based auth ───────────────────────────────────────────────────────
// Tokens are stored in HttpOnly cookies (set by auth service).
// JavaScript cannot read them — we use the cv_session cookie to check auth status.
// localStorage is only used for non-sensitive display data (user name, org).

function hasSession(): boolean {
  if (typeof document === 'undefined') return false;
  return document.cookie.includes('cv_session=1');
}

function clearLocalUserData() {
  localStorage.removeItem('cloudvisor-user');
  // Legacy cleanup — remove any old localStorage tokens
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    if (!hasSession()) {
      setUser(null);
      return;
    }

    try {
      // getCurrentUser uses credentials: 'include' — cookie sent automatically
      const userData = await authAPI.getCurrentUser();
      setUser(userData);
      // Store only non-sensitive display data
      if (typeof window !== 'undefined') {
        localStorage.setItem('cloudvisor-user', JSON.stringify({
          id: userData.id,
          organization_id: userData.organization_id,
          organization_name: userData.organization_name,
          role: userData.role,
        }));
      }
    } catch {
      // Token might be expired — try refresh (server reads cv_refresh cookie)
      try {
        await authAPI.refreshToken();
        // Refresh succeeded — server set new cookies, retry getCurrentUser
        const newUserData = await authAPI.getCurrentUser();
        setUser(newUserData);
        if (typeof window !== 'undefined') {
          localStorage.setItem('cloudvisor-user', JSON.stringify({
            id: newUserData.id,
            organization_id: newUserData.organization_id,
            organization_name: newUserData.organization_name,
            role: newUserData.role,
          }));
        }
      } catch {
        clearLocalUserData();
        setUser(null);
      }
    }
  }, []);

  useEffect(() => {
    refreshUser().finally(() => setIsLoading(false));
  }, [refreshUser]);

  const login = async (email: string, password: string, mfaCode?: string) => {
    // Server sets HttpOnly cookies on successful login
    await authAPI.login({ email, password, mfa_code: mfaCode });
    await refreshUser();
  };

  const register = async (data: {
    email: string;
    password: string;
    organization_name: string;
    first_name: string;
    last_name: string;
  }) => {
    // Server sets HttpOnly cookies on successful registration
    await authAPI.register(data);
    await refreshUser();
  };

  const logout = async () => {
    try {
      // Server clears HttpOnly cookies
      await authAPI.logout();
    } catch {
    } finally {
      clearLocalUserData();
      // Reset account loader so next login fetches fresh accounts
      try {
        const { resetAccountLoader } = await import('@/components/layout/header');
        resetAccountLoader();
      } catch {
        // Non-fatal if import fails
      }
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}