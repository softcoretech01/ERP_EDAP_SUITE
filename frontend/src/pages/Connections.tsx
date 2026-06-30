import React, { useState, useEffect } from 'react';
import api from '../api/axios';
import { Plus, Server, Database, User, Shield, Activity, RefreshCw, Trash2 } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';



export const Connections: React.FC = () => {
  const { aiMode, setAiMode, connections, fetchConnections, isFetchingConnections } = useAppStore();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({ name: '', host: '', port: 3306, user: '', password: '', db_name: '' });
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    const load = async () => {
      await fetchConnections();
    };
    load();
  }, [fetchConnections]);

  const handleCreateConnection = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      await api.post('/connections', formData);
      setIsModalOpen(false);
      setFormData({ name: '', host: '', port: 3306, user: '', password: '', db_name: '' });
      await fetchConnections(true);
    } catch (err) {
      console.error(err);
      alert('Failed to create connection');
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteConnection = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this connection?')) return;
    try {
      await api.delete(`/connections/${id}`);
      await fetchConnections(true);
    } catch (err) {
      console.error(err);
      alert('Failed to delete connection');
    }
  };

  return (
    <div className="flex-1 h-full overflow-auto bg-white text-[#0d0d0d] p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-[#0d0d0d]">
              Database Connections
            </h1>
            <p className="text-[#6b6b6b] mt-2">Manage your ERP data sources and agent access</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => setAiMode(aiMode === 'db' ? 'document' : 'db')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm ${
                aiMode === 'db' 
                  ? 'bg-blue-100 text-blue-700 hover:bg-blue-200' 
                  : 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
              }`}
              title="Toggle AI Chat Mode"
            >
              <Activity className="w-4 h-4" />
              {aiMode === 'db' ? 'Switch to Document AI' : 'Switch to Database AI'}
            </button>
            <button 
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-2 px-4 py-2 bg-[#10a37f] hover:bg-[#1a7f64] transition-colors rounded-lg text-sm font-medium text-white shadow-sm"
            >
              <Plus className="w-4 h-4" />
              New Connection
            </button>
          </div>
        </div>

        {isModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-2xl">
              <h2 className="text-xl font-bold mb-4">Add New Connection</h2>
              <form onSubmit={handleCreateConnection} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-[#6b6b6b] mb-1">Connection Name</label>
                  <input required type="text" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} className="w-full border border-[#e5e5e5] rounded-md px-3 py-2 text-sm focus:outline-none focus:border-[#10a37f]" placeholder="e.g. Production ERP" />
                </div>
                <div className="flex gap-4">
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-[#6b6b6b] mb-1">Host</label>
                    <input required type="text" value={formData.host} onChange={e => setFormData({...formData, host: e.target.value})} className="w-full border border-[#e5e5e5] rounded-md px-3 py-2 text-sm focus:outline-none focus:border-[#10a37f]" placeholder="localhost" />
                  </div>
                  <div className="w-24">
                    <label className="block text-sm font-medium text-[#6b6b6b] mb-1">Port</label>
                    <input required type="number" value={formData.port} onChange={e => setFormData({...formData, port: parseInt(e.target.value)})} className="w-full border border-[#e5e5e5] rounded-md px-3 py-2 text-sm focus:outline-none focus:border-[#10a37f]" />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#6b6b6b] mb-1">Username</label>
                  <input required type="text" value={formData.user} onChange={e => setFormData({...formData, user: e.target.value})} className="w-full border border-[#e5e5e5] rounded-md px-3 py-2 text-sm focus:outline-none focus:border-[#10a37f]" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#6b6b6b] mb-1">Password</label>
                  <input required type="password" value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} className="w-full border border-[#e5e5e5] rounded-md px-3 py-2 text-sm focus:outline-none focus:border-[#10a37f]" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#6b6b6b] mb-1">Database Name (Optional)</label>
                  <input type="text" value={formData.db_name} onChange={e => setFormData({...formData, db_name: e.target.value})} className="w-full border border-[#e5e5e5] rounded-md px-3 py-2 text-sm focus:outline-none focus:border-[#10a37f]" placeholder="Leave blank for all DBs" />
                </div>
                <div className="flex justify-end gap-3 mt-6">
                  <button type="button" onClick={() => setIsModalOpen(false)} className="px-4 py-2 text-sm font-medium text-[#6b6b6b] hover:text-[#0d0d0d]">Cancel</button>
                  <button type="submit" disabled={creating} className="px-4 py-2 bg-[#10a37f] hover:bg-[#1a7f64] text-white rounded-md text-sm font-medium disabled:opacity-50">
                    {creating ? 'Saving...' : 'Save Connection'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {isFetchingConnections ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw className="w-8 h-8 text-[#10a37f] animate-spin" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {connections.map(conn => (
              <div key={conn.id} className="bg-white border border-[#e5e5e5] rounded-xl p-6 hover:shadow-md transition-shadow group relative overflow-hidden">
                <div className="absolute top-0 left-0 w-1 h-full bg-[#10a37f] opacity-50 group-hover:opacity-100 transition-opacity" />
                
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-[#f4f4f4] rounded-lg border border-[#e5e5e5]">
                      <Database className="w-6 h-6 text-[#10a37f]" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-lg text-[#0d0d0d]">{conn.name}</h3>
                      <div className="flex gap-2 mt-1">
                        <span className="text-[10px] font-medium px-2 py-0.5 bg-[#f4f4f4] border border-[#e5e5e5] rounded text-[#6b6b6b] uppercase tracking-wider">
                          {conn.db_type}
                        </span>
                        <span className={`text-[10px] font-medium px-2 py-0.5 rounded uppercase tracking-wider ${
                          conn.connection_status === 'completed' ? 'bg-green-100 text-green-700' :
                          conn.connection_status === 'failed' ? 'bg-red-100 text-red-700' :
                          'bg-yellow-100 text-yellow-700 animate-pulse'
                        }`}>
                          {conn.connection_status === 'completed' ? 'Ready' : conn.connection_status}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2">

                    <button 
                      onClick={() => {
                        api.post(`/connections/${conn.id}/reindex`).then(() => fetchConnections(true));
                      }}
                      className="p-1.5 hover:bg-[#f4f4f4] rounded-md text-[#8e8e8e] hover:text-[#0d0d0d] transition-colors"
                      title="Re-index schema"
                    >
                      <RefreshCw className={`w-4 h-4 ${conn.connection_status === 'scanning' || conn.connection_status === 'indexing' ? 'animate-spin' : ''}`} />
                    </button>

                    <button 
                      onClick={() => handleDeleteConnection(conn.id)}
                      className="p-1.5 hover:bg-red-50 rounded-md text-[#8e8e8e] hover:text-red-600 transition-colors"
                      title="Delete connection"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="space-y-3 mt-6">
                  <div className="flex items-center gap-3 text-sm text-[#6b6b6b]">
                    <Server className="w-4 h-4" />
                    <span className="truncate">{conn.host}:{conn.port}</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-[#6b6b6b]">
                    <Shield className="w-4 h-4" />
                    <span className="truncate">All Databases</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-[#6b6b6b]">
                    <User className="w-4 h-4" />
                    <span className="truncate">{conn.user}</span>
                  </div>
                  
                  {conn.error_message && (
                    <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-600">
                      {conn.error_message}
                    </div>
                  )}
                  {conn.last_indexed_at && !conn.error_message && (
                    <div className="text-[10px] text-[#8e8e8e] mt-2">
                      Indexed: {new Date(conn.last_indexed_at).toLocaleString()}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
