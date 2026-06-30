import React, { useState, useEffect } from 'react';
import { Sparkles, BarChart3, TrendingUp, PieChart, BarChart2, Activity } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import { DynamicDashboard } from '../components/dashboard/DynamicDashboard';
import api from '../api/axios';

const SUGGESTIONS = [
  { label: 'Show purchase trend', icon: <TrendingUp className="w-3.5 h-3.5" /> },
  { label: 'Show top vendors', icon: <BarChart2 className="w-3.5 h-3.5" /> },
  { label: 'Show PO status distribution', icon: <PieChart className="w-3.5 h-3.5" /> },
  { label: 'Show total PO value', icon: <Activity className="w-3.5 h-3.5" /> },
];

export const Dashboard = () => {
  const { activeConnection } = useAppStore();
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [dashboardData, setDashboardData] = useState<any>(null);

  useEffect(() => {
    console.log("Selected Connection in Dashboard:", activeConnection);
  }, [activeConnection]);

  const handleFetchDashboard = async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setError('Please enter a query.');
      return;
    }

    setLoading(true);
    setError('');
    console.log(`Fetching dashboard for query: "${searchQuery}"`);

    try {
      const response = await api.get('/dashboard', {
        params: {
          query: searchQuery,
          db_conn_id: activeConnection ? activeConnection.id : 1
        }
      });
      
      console.log("Dashboard Response:", response.data);
      if (response.data?.success && response.data?.type === 'dashboard') {
        setDashboardData(response.data.result);
      } else {
        setError(response.data?.message || 'Failed to fetch dashboard data.');
        setDashboardData(null);
      }
    } catch (err: any) {
      console.error("Dashboard fetch error:", err);
      setError(err.response?.data?.detail || 'Failed to fetch dashboard data. Make sure backend is running and active.');
      setDashboardData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleFetchDashboard(query);
  };

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion);
    handleFetchDashboard(suggestion);
  };

  return (
    <div className="min-h-screen bg-white text-[#0d0d0d] p-6 md:p-8 relative overflow-hidden">
      <div className="max-w-5xl mx-auto z-10 relative space-y-8">
        {/* Header */}
        <div className="flex items-center gap-4 pb-2 border-b border-[#e5e5e5]">
          <div className="w-12 h-12 bg-[#10a37f]/10 rounded-2xl flex items-center justify-center">
            <BarChart3 className="w-6 h-6 text-[#10a37f]" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-[#0d0d0d] tracking-tight">
              Dynamic Analytics
            </h1>
            <p className="text-sm text-[#6b6b6b] mt-1 font-medium">
              Ask questions to automatically generate insights and charts from your ERP data
            </p>
          </div>
        </div>

        {/* Input Area */}
        <div className="space-y-4">
          <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 bg-white border border-[#e5e5e5] p-2 rounded-[20px] shadow-sm focus-within:ring-2 focus-within:ring-[#10a37f]/20 transition-all">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={loading}
              placeholder={activeConnection ? "e.g., Show purchase trend over the last 6 months..." : "Select a database connection first..."}
              className="flex-1 bg-transparent border-none px-4 py-3 text-[15px] focus:outline-none text-[#0d0d0d] placeholder-[#8e8e8e] disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={loading || !activeConnection || !query.trim()}
              className="bg-[#0d0d0d] hover:bg-[#2f2f2f] text-white font-medium px-6 py-3 rounded-2xl transition-all duration-200 text-sm shrink-0 flex items-center justify-center gap-2 disabled:opacity-30 disabled:bg-[#e5e5e5] disabled:text-[#8e8e8e]"
            >
              {loading ? (
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Generate View
                </>
              )}
            </button>
          </form>

          {/* Suggestions */}
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s, idx) => (
              <button
                key={idx}
                type="button"
                disabled={loading || !activeConnection}
                onClick={() => handleSuggestionClick(s.label)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-[#f4f4f4] hover:bg-[#e5e5e5] border border-[#e5e5e5] rounded-full text-xs font-medium text-[#6b6b6b] transition-colors disabled:opacity-50"
              >
                {s.icon}
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* Error Notice */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 p-4 rounded-2xl text-sm flex items-center gap-3">
            <span className="text-lg">⚠️</span>
            {error}
          </div>
        )}

        {/* Chart View Area */}
        <div className="pt-2">
          {loading ? (
            <div className="h-[400px] bg-gradient-to-b from-[#f9f9f9] to-white border border-[#e5e5e5] rounded-3xl flex flex-col items-center justify-center text-[#6b6b6b] gap-4 shadow-sm">
              <div className="w-12 h-12 bg-white rounded-full shadow-sm flex items-center justify-center border border-[#e5e5e5]">
                <Sparkles className="w-6 h-6 text-[#10a37f] animate-pulse" />
              </div>
              <span className="text-sm font-medium">Analyzing intent and generating visualizations...</span>
            </div>
          ) : dashboardData ? (
            <div className="bg-white border border-[#e5e5e5] rounded-3xl p-6 md:p-8 shadow-sm transition-all">
              <DynamicDashboard result={dashboardData} />
            </div>
          ) : (
            <div className="h-[300px] bg-[#f9f9f9] border border-dashed border-[#e5e5e5] rounded-3xl flex flex-col items-center justify-center text-[#8e8e8e] gap-4">
              <div className="w-16 h-16 bg-white rounded-2xl shadow-sm border border-[#e5e5e5] flex items-center justify-center">
                <BarChart3 className="w-8 h-8 text-[#e5e5e5]" />
              </div>
              <p className="text-sm font-medium max-w-sm text-center">
                Select a suggestion or type a query above to dynamically generate a dashboard visual.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
