import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import { useAuthStore } from '../store/useAuthStore';
import api from '../api/axios';

export const Signup = () => {
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [orgName, _setOrgName] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { setAuth } = useAuthStore();
  const navigate = useNavigate();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await api.post('/auth/register', {
        username: email,
        email: email,
        password: password,
        full_name: fullName,
        organization: orgName
      });
      const { access_token, refresh_token, user } = response.data;
      setAuth(access_token, refresh_token, user);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f9f9f9] flex items-center justify-center p-4">
      <div className="max-w-[400px] w-full bg-white rounded-lg p-8 shadow-sm border border-[#e5e5e5]">
        <div className="flex flex-col items-center mb-8">
          <h1 className="text-3xl font-bold text-[#0d0d0d] tracking-tight mb-2">Create an account</h1>
          <p className="text-[#6b6b6b] text-sm">Welcome to EDIP Suite</p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 p-3 rounded mb-6 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleRegister} className="space-y-4">
          <div>
            <div className="relative">
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full bg-white border border-[#e5e5e5] rounded py-3 px-4 text-[#0d0d0d] placeholder-[#8e8e8e] focus:outline-none focus:border-[#10a37f] transition-all"
                placeholder="Full Name"
                required
              />
            </div>
          </div>

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
            {loading ? 'Creating...' : 'Continue'}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-[#6b6b6b]">
          Already have an account?{' '}
          <Link to="/login" className="text-[#10a37f] hover:underline">
            Log in
          </Link>
        </div>
      </div>
    </div>
  );
};
