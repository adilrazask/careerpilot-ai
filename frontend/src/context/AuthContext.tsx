import React, { createContext, useContext, useState, useEffect } from 'react';
import { User } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  sessionTerminatedNotice: string | null;
  login: (email: string, password?: string) => Promise<void>;
  loginWithGoogle: (payload: { email?: string; name?: string; credential?: string; avatar?: string }) => Promise<void>;
  logout: () => Promise<void>;
  hasFeatureAccess: (featureId: string) => boolean;
  clearNotice: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('careerpilot_user');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return null;
      }
    }
    return null;
  });
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('careerpilot_auth_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [sessionTerminatedNotice, setSessionTerminatedNotice] = useState<string | null>(null);

  const fetchCurrentUser = async () => {
    const currentToken = localStorage.getItem('careerpilot_auth_token');
    if (!currentToken) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      const res = await api.getMe();
      setUser(res.user);
      localStorage.setItem('careerpilot_user', JSON.stringify(res.user));
    } catch (err: any) {
      console.warn('Authentication check failed:', err);
      // Handled by 401 interceptor
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCurrentUser();

    // Listen for real-time session termination events from API interceptor
    const handleSessionTerminated = (e: any) => {
      setUser(null);
      setToken(null);
      setSessionTerminatedNotice(
        e.detail || 'Your session was terminated by the administrator. Please log in again.'
      );
    };

    window.addEventListener('session-terminated', handleSessionTerminated);
    return () => {
      window.removeEventListener('session-terminated', handleSessionTerminated);
    };
  }, []);

  const login = async (email: string, password?: string) => {
    setIsLoading(true);
    setSessionTerminatedNotice(null);
    try {
      const res = await api.login(email, password);
      localStorage.setItem('careerpilot_auth_token', res.token);
      localStorage.setItem('careerpilot_user', JSON.stringify(res.user));
      setToken(res.token);
      setUser(res.user);
    } finally {
      setIsLoading(false);
    }
  };

  const loginWithGoogle = async (payload: { email?: string; name?: string; credential?: string; avatar?: string }) => {
    setIsLoading(true);
    setSessionTerminatedNotice(null);
    try {
      const res = await api.loginWithGoogle(payload);
      localStorage.setItem('careerpilot_auth_token', res.token);
      localStorage.setItem('careerpilot_user', JSON.stringify(res.user));
      setToken(res.token);
      setUser(res.user);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch {
      // Ignored
    } finally {
      localStorage.removeItem('careerpilot_auth_token');
      localStorage.removeItem('careerpilot_user');
      setUser(null);
      setToken(null);
    }
  };

  const hasFeatureAccess = (featureId: string): boolean => {
    if (!user) return false;
    if (user.role === 'admin' || user.email.toLowerCase() === 'adilrazask@gmail.com') return true;
    if (!user.allowed_features) return false;
    if (user.allowed_features.includes('*')) return true;
    return user.allowed_features.includes(featureId);
  };

  const clearNotice = () => setSessionTerminatedNotice(null);

  const refreshUser = async () => {
    await fetchCurrentUser();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        sessionTerminatedNotice,
        login,
        loginWithGoogle,
        logout,
        hasFeatureAccess,
        clearNotice,
        refreshUser
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
