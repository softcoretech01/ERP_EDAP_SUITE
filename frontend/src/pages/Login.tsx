import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import { useAuthStore } from '../store/useAuthStore';
import api from '../api/axios';

export const Login = () => {
  const [email, setEmail] = useState('kabil@gmail.com');
  const [password, setPassword] = useState('password123');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { setAuth } = useAuthStore();
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const params = new URLSearchParams();
      params.append('username', email);
      params.append('password', password);

      const response = await api.post('/auth/login', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      const { access_token, refresh_token, user } = response.data;
      
      setAuth(access_token, refresh_token, user);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f9f9f9] flex items-center justify-center p-4">
      <div className="max-w-[400px] w-full bg-white rounded-lg p-8 shadow-sm border border-[#e5e5e5]">
        <div className="flex flex-col items-center mb-8">
          <h1 className="text-3xl font-bold text-[#0d0d0d] tracking-tight mb-2">Welcome back</h1>
          <p className="text-[#6b6b6b] text-sm">Log in to EDIP Suite</p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 p-3 rounded mb-6 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <div className="relative">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-white border border-[#e5e5e5] rounded py-3 px-4 text-[#0d0d0d] placeholder-[#8e8e8e] focus:outline-none focus:border-[#10a37f] transition-all"
                placeholder="Email address"
                required
              />
            </div>
          </div>

          <div>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-white border border-[#e5e5e5] rounded py-3 px-4 text-[#0d0d0d] placeholder-[#8e8e8e] focus:outline-none focus:border-[#10a37f] transition-all"
                placeholder="Password"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8e8e8e] hover:text-[#0d0d0d]"
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#10a37f] hover:bg-[#1a7f64] text-white font-medium py-3 rounded transition-colors mt-2 disabled:opacity-70"
          >
            {loading ? 'Logging in...' : 'Continue'}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-[#6b6b6b]">
          Don't have an account?{' '}
          <Link to="/signup" className="text-[#10a37f] hover:underline">
            Sign up
          </Link>
        </div>
      </div>
    </div>
  );
};
