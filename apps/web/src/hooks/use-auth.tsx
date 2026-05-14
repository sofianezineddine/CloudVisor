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

// SECURITY NOTE: Tokens are stored in localStorage for compatibility with the
// current architecture. This is acceptable for a development/demo environment.
// For production hardening, migrate to httpOnly cookies set by the auth service
// to eliminate XSS token theft risk. The auth service already supports this via
// the Set-Cookie header on /auth/login and /auth/refresh.

function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

function setTokens(accessToken: string, refreshToken: string) {
  // Validate tokens are non-empty strings before storing
  if (!accessToken || !refreshToken) return;
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setUser(null);
      return;
    }

    try {
      const userData = await authAPI.getCurrentUser(token);
      setUser(userData);
      // Persist only non-sensitive user fields needed for org ID resolution.
      // Do NOT store sensitive fields like mfa_secret or full profile in localStorage.
      if (typeof window !== 'undefined') {
        const safeUserData = {
          id: userData.id,
          organization_id: userData.organization_id,
          organization_name: userData.organization_name,
          role: userData.role,
        };
        localStorage.setItem('cloudvisor-user', JSON.stringify(safeUserData));
      }
    } catch {
      const refreshToken = getRefreshToken();
      if (refreshToken) {
        try {
          const tokens = await authAPI.refreshToken(refreshToken);
          setTokens(tokens.access_token, tokens.refresh_token);
          const newUserData = await authAPI.getCurrentUser(tokens.access_token);
          setUser(newUserData);
          if (typeof window !== 'undefined') {
            const safeUserData = {
              id: newUserData.id,
              organization_id: newUserData.organization_id,
              organization_name: newUserData.organization_name,
              role: newUserData.role,
            };
            localStorage.setItem('cloudvisor-user', JSON.stringify(safeUserData));
          }
        } catch {
          clearTokens();
          localStorage.removeItem('cloudvisor-user');
          setUser(null);
        }
      } else {
        clearTokens();
        localStorage.removeItem('cloudvisor-user');
        setUser(null);
      }
    }
  }, []);

  useEffect(() => {
    refreshUser().finally(() => setIsLoading(false));
  }, [refreshUser]);

  const login = async (email: string, password: string, mfaCode?: string) => {
    const response = await authAPI.login({ email, password, mfa_code: mfaCode });
    setTokens(response.access_token, response.refresh_token);
    await refreshUser();
  };

  const register = async (data: {
    email: string;
    password: string;
    organization_name: string;
    first_name: string;
    last_name: string;
  }) => {
    const response = await authAPI.register(data);
    setTokens(response.access_token, response.refresh_token);
    await refreshUser();
  };

  const logout = async () => {
    try {
      await authAPI.logout();
    } catch {
    } finally {
      clearTokens();
      if (typeof window !== 'undefined') {
        localStorage.removeItem('cloudvisor-user');
      }
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