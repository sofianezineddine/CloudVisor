'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { adminAuthAPI } from '@/lib/api/admin-auth';

interface AdminUser {
  id: string;
  email: string;
  name: string;
  role: string;
  created_at: string;
}

interface AdminAuthContextType {
  user: AdminUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AdminAuthContext = createContext<AdminAuthContextType | undefined>(undefined);

const ACCESS_TOKEN_KEY = 'admin_access_token';
const REFRESH_TOKEN_KEY = 'admin_refresh_token';

function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

function setTokens(accessToken: string, refreshToken: string) {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AdminUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setUser(null);
      return;
    }

    try {
      const userData = await adminAuthAPI.getCurrentUser(token);
      setUser(userData);
    } catch {
      const refreshToken = getRefreshToken();
      if (refreshToken) {
        try {
          const tokens = await adminAuthAPI.refreshToken(refreshToken);
          setTokens(tokens.access_token, tokens.refresh_token);
          const newUserData = await adminAuthAPI.getCurrentUser(tokens.access_token);
          setUser(newUserData);
        } catch {
          clearTokens();
          setUser(null);
        }
      } else {
        clearTokens();
        setUser(null);
      }
    }
  }, []);

  useEffect(() => {
    refreshUser().finally(() => setIsLoading(false));
  }, [refreshUser]);

  const login = async (email: string, password: string) => {
    const response = await adminAuthAPI.login({ email, password });
    setTokens(response.access_token, response.refresh_token);
    await refreshUser();
  };

  const logout = async () => {
    try {
      await adminAuthAPI.logout();
    } catch {
      // Ignore logout errors
    } finally {
      clearTokens();
      setUser(null);
    }
  };

  return (
    <AdminAuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth() {
  const context = useContext(AdminAuthContext);
  if (context === undefined) {
    throw new Error('useAdminAuth must be used within an AuthProvider');
  }
  return context;
}
