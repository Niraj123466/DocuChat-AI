import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL 
  ? `${import.meta.env.VITE_API_URL}/api/v1` 
  : 'http://127.0.0.1:8000/api/v1';

const TOKEN_KEY = 'docuchat_jwt';
const USER_KEY = 'docuchat_user';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem(USER_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  // Validate existing token on mount
  useEffect(() => {
    let isMounted = true;
    const validateToken = async () => {
      const savedToken = localStorage.getItem(TOKEN_KEY);
      if (!savedToken) {
        if (isMounted) setIsAuthLoading(false);
        return;
      }
      try {
        const res = await fetch(`${API_BASE}/auth/me`, {
          headers: { Authorization: `Bearer ${savedToken}` }
        });
        if (res.ok) {
          const profile = await res.json();
          if (isMounted) {
            setUser(profile);
            localStorage.setItem(USER_KEY, JSON.stringify(profile));
          }
        } else {
          // Token expired or invalid
          if (isMounted) {
            setToken(null);
            setUser(null);
            localStorage.removeItem(TOKEN_KEY);
            localStorage.removeItem(USER_KEY);
          }
        }
      } catch (err) {
        console.warn('Could not verify auth session:', err);
      } finally {
        if (isMounted) setIsAuthLoading(false);
      }
    };

    validateToken();
    return () => { isMounted = false; };
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Authentication failed' }));
      throw new Error(err.detail || 'Invalid email or password');
    }

    const data = await res.json();
    setToken(data.access_token);
    setUser(data.user);
    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    setIsAuthModalOpen(false);
    return data.user;
  }, []);

  const register = useCallback(async (name, email, password) => {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Registration failed' }));
      throw new Error(err.detail || 'Could not register account');
    }

    const data = await res.json();
    setToken(data.access_token);
    setUser(data.user);
    localStorage.setItem(TOKEN_KEY, data.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    setIsAuthModalOpen(false);
    return data.user;
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }, []);

  // Authenticated fetch wrapper
  const authFetch = useCallback(async (url, options = {}) => {
    const headers = { ...(options.headers || {}) };
    const currentToken = token || localStorage.getItem(TOKEN_KEY);
    if (currentToken) {
      headers['Authorization'] = `Bearer ${currentToken}`;
    }

    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) {
      logout();
      setIsAuthModalOpen(true);
    }
    return res;
  }, [token, logout]);

  const value = {
    token,
    user,
    isAuthenticated: !!token && !!user,
    isAuthLoading,
    isAuthModalOpen,
    setIsAuthModalOpen,
    login,
    register,
    logout,
    authFetch
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
