import { create } from 'zustand';
import axios from 'axios';

export interface User {
  id: number;
  username: string;
  email: string;
  name: string;
  role: string;
}

interface AuthState {
  token: string | null;
  refreshTokenStr: string | null;
  user: User | null;
  setAuth: (token: string, refreshTokenStr: string, user: User) => void;
  logout: () => void;
  fetchUser: () => Promise<void>;
  refreshToken: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: localStorage.getItem('token') || null,
  refreshTokenStr: localStorage.getItem('refreshToken') || null,
  user: null,
  
  setAuth: (token, refreshTokenStr, user) => {
    localStorage.setItem('token', token);
    localStorage.setItem('refreshToken', refreshTokenStr);
    set({ token, refreshTokenStr, user });
  },
  
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    set({ token: null, refreshTokenStr: null, user: null });
  },
  
  fetchUser: async () => {
    const { token } = get();
    if (!token) return;
    try {
      const res = await axios.get('http://127.0.0.1:8000/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` }
      });
      set({ user: res.data });
    } catch (err: any) {
      console.error('Failed to fetch user profile, trying refresh:', err);
      // Attempt to refresh token if /me fails with 401
      if (err.response?.status === 401) {
        await get().refreshToken();
      }
    }
  },
  
  refreshToken: async () => {
    const { refreshTokenStr } = get();
    if (!refreshTokenStr) {
      get().logout();
      return;
    }
    try {
      const res = await axios.post('http://127.0.0.1:8000/api/auth/refresh', {
        refresh_token: refreshTokenStr
      });
      const { access_token, refresh_token: new_refresh_token, user } = res.data;
      get().setAuth(access_token, new_refresh_token, user);
    } catch (err) {
      console.error('Token refresh failed, logging out:', err);
      get().logout();
      // Force page redirect if refresh fails to clear state
      window.location.href = '/login';
    }
  }
}));
