import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Plus, LayoutDashboard, UploadCloud, ChevronDown, Sparkles, LogOut, Database } from 'lucide-react';
import { useAuthStore } from '../store/useAuthStore';
import { useAppStore } from '../store/useAppStore';
import { useChatStore } from '../store/useChatStore';
import api from '../api/axios';
import clsx from 'clsx';

export const Sidebar = () => {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { logout, user, token } = useAuthStore();
  const { activeConnection, setActiveConnection, sidebarOpen, connections, fetchConnections } = useAppStore();
  const { clearChat, setSessionId, setMessages, sessions, fetchSessions } = useChatStore();

  const [dbDropdownOpen, setDbDropdownOpen] = useState(false);

  useEffect(() => {
    if (token) {
      fetchConnections();
      fetchSessions();
    }
  }, [token, fetchConnections, fetchSessions]);



  const handleSelectSession = async (sessId: string) => {
    try {
      const res = await api.get(`/chat/sessions/${sessId}`);
      setSessionId(sessId);
      setMessages(res.data);
      navigate('/');
    } catch (err) {
      console.error('Error loading session messages', err);
    }
  };

  if (!sidebarOpen) return null;

  return (
    <div className="w-64 bg-[#f9f9f9] h-full flex flex-col border-r border-[#e5e5e5] z-20 text-[#0d0d0d]">
      {/* Header / Logo */}
      <div className="p-4 flex items-center gap-2 border-b border-[#e5e5e5]">
        <div className="w-8 h-8 bg-[#10a37f] rounded-md flex items-center justify-center shadow-sm">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        <span className="font-bold text-lg text-[#0d0d0d]">
          EDIP Suite
        </span>
      </div>

      {/* DB Selector */}
      <div className="px-4 py-3 relative border-b border-[#e5e5e5]">
        <div className="text-[10px] font-bold text-[#8e8e8e] uppercase tracking-wider mb-2">
          Database
        </div>
        <button
          onClick={() => setDbDropdownOpen(!dbDropdownOpen)}
          className="w-full flex items-center justify-between px-3 py-2 bg-white hover:bg-[#ececf1] border border-[#e5e5e5] rounded-md text-sm font-medium text-[#0d0d0d] transition-all duration-200 shadow-sm"
        >
          <div className="flex items-center gap-2 truncate">
            <Database className="w-3.5 h-3.5 text-[#10a37f]" />
            <span className="truncate">{activeConnection?.name || 'Select Database'}</span>
          </div>
          <ChevronDown className={`w-3.5 h-3.5 text-[#6b6b6b] transition-transform ${dbDropdownOpen ? 'rotate-180' : ''}`} />
        </button>
        
        {dbDropdownOpen && (
          <div className="absolute top-full left-4 right-4 mt-1 bg-white border border-[#e5e5e5] rounded-md shadow-lg z-50 py-1 max-h-48 overflow-y-auto">
            {connections.length === 0 ? (
              <div className="px-3 py-2 text-sm text-[#8e8e8e]">No connections</div>
            ) : (
              connections.map(conn => (
                <button
                  key={conn.id}
                  onClick={() => {
                    setActiveConnection(conn);
                    setDbDropdownOpen(false);
                  }}
                  className="w-full text-left px-3 py-2 text-sm text-[#0d0d0d] hover:bg-[#ececf1] transition-colors flex items-center justify-between"
                >
                  <span className="truncate">{conn.name}</span>
                  {activeConnection?.id === conn.id && (
                    <div className="w-1.5 h-1.5 rounded-full bg-[#10a37f]"></div>
                  )}
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="px-3 py-2 mt-2 space-y-1">
        <button
          onClick={() => {
            clearChat();
            navigate('/');
          }}
          className="w-full flex items-center gap-2 px-3 py-2.5 bg-white hover:bg-[#ececf1] border border-[#e5e5e5] rounded-md text-sm font-medium text-[#0d0d0d] transition-all duration-200 shadow-sm mb-2"
        >
          <Plus className="w-4 h-4 text-[#10a37f]" />
          New chat
        </button>

        <button
          onClick={() => navigate('/dashboard')}
          className={clsx(
            "w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-all duration-200",
            pathname === '/dashboard'
              ? "bg-[#ececf1] text-[#0d0d0d]"
              : "text-[#6b6b6b] hover:text-[#0d0d0d] hover:bg-[#ececf1]"
          )}
        >
          <LayoutDashboard className="w-4 h-4" />
          Dashboard
        </button>
        
        <button
          onClick={() => navigate('/connections')}
          className={clsx(
            "w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-all duration-200",
            pathname === '/connections'
              ? "bg-[#ececf1] text-[#0d0d0d]"
              : "text-[#6b6b6b] hover:text-[#0d0d0d] hover:bg-[#ececf1]"
          )}
        >
          <Database className="w-4 h-4" />
          Connections
        </button>

        <button
          onClick={() => navigate('/configuration')}
          className={clsx(
            "w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-all duration-200",
            pathname === '/configuration'
              ? "bg-[#ececf1] text-[#0d0d0d]"
              : "text-[#6b6b6b] hover:text-[#0d0d0d] hover:bg-[#ececf1]"
          )}
        >
          <LayoutDashboard className="w-4 h-4" />
          Configuration
        </button>

      </div>

      {/* Recents Section */}
      <div className="flex-1 overflow-y-auto px-3 py-2 mt-2">
        <div className="text-[10px] font-bold text-[#8e8e8e] uppercase tracking-wider mb-2 px-1">
          Recent Chats
        </div>
        <div className="space-y-0.5">
          {sessions.length === 0 ? (
            <div className="px-3 py-1 text-sm text-[#8e8e8e]">No recent chats</div>
          ) : (
            sessions.map((sess) => (
              <button
                key={sess.session_id}
                className={clsx(
                  "w-full text-left px-3 py-2 rounded-md text-sm transition-all duration-150 truncate block",
                  pathname === '/' && useChatStore.getState().sessionId === sess.session_id
                    ? "bg-[#ececf1] text-[#0d0d0d] font-medium"
                    : "text-[#6b6b6b] hover:text-[#0d0d0d] hover:bg-[#ececf1]"
                )}
                onClick={() => handleSelectSession(sess.session_id)}
              >
                {sess.title}
              </button>
            ))
          )}
        </div>
      </div>

      {/* Footer Area */}
      <div className="p-3 border-t border-[#e5e5e5] space-y-2 bg-[#f9f9f9]">

        {/* Uploaded Files Section */}
        <button
          onClick={() => navigate('/uploads')}
          className={clsx(
            "w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-all duration-200",
            pathname === '/uploads'
              ? "bg-[#ececf1] text-[#0d0d0d]"
              : "text-[#6b6b6b] hover:text-[#0d0d0d] hover:bg-[#ececf1]"
          )}
        >
          <UploadCloud className="w-4 h-4 text-[#10a37f]" />
          Uploaded Files
        </button>

        {/* User Card */}
        <div className="flex items-center gap-3 px-2 py-1">
          <div className="w-8 h-8 rounded-full bg-[#10a37f] flex items-center justify-center font-bold text-white text-sm shadow-sm">
            {user?.username?.substring(0, 1).toUpperCase() || 'K'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-[#0d0d0d] truncate">
              {user?.name || 'Kabilesh'}
            </p>
            <p className="text-[10px] text-[#8e8e8e] font-bold tracking-wide uppercase">
              {user?.role || 'Administrator'}
            </p>
          </div>
        </div>

        {/* Sign Out */}
        <button
          onClick={() => {
            logout();
            navigate('/login');
          }}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-white hover:bg-red-50 hover:text-red-600 border border-[#e5e5e5] hover:border-red-200 rounded-md text-sm font-medium text-[#6b6b6b] transition-all duration-300 shadow-sm"
        >
          <LogOut className="w-4 h-4" />
          Sign Out
        </button>
      </div>
    </div>
  );
};
