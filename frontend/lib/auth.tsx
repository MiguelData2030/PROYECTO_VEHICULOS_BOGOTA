'use client';

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface User {
  id: number;
  username: string;
  email: string;
  is_admin: boolean;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = useCallback(async (t: string) => {
    try {
      const { data } = await axios.get<User>(`${API_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      setUser(data);
    } catch {
      localStorage.removeItem('token');
      setToken(null);
      setUser(null);
    }
  }, []);

  useEffect(() => {
    const stored = localStorage.getItem('token');
    if (stored) {
      setToken(stored);
      fetchUser(stored).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [fetchUser]);

  const login = async (username: string, password: string) => {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);

    const { data } = await axios.post<{ access_token: string }>(
      `${API_URL}/auth/login`,
      params,
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
    );

    localStorage.setItem('token', data.access_token);
    setToken(data.access_token);
    await fetchUser(data.access_token);
  };

  const register = async (username: string, email: string, password: string) => {
    await axios.post(`${API_URL}/auth/register`, {
      username,
      email,
      password,
      is_admin: true,
    });
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
