import { useState, useEffect } from 'react';
import { Database, Save, Plus, Trash2, ArrowLeft } from 'lucide-react';
import api from '../api/axios';
import { useAppStore } from '../store/useAppStore';

const MODULES = ['Sales', 'Purchase', 'Inventory', 'Finance', 'HR'];

export const Configuration = () => {
  const { activeConnection } = useAppStore();
  const [selectedModule, setSelectedModule] = useState<string | null>(null);

  const [tablesByDb, setTablesByDb] = useState<Record<string, string[]>>({});
  const [availableDatabases, setAvailableDatabases] = useState<string[]>([]);
  const [databaseName, setDatabaseName] = useState<string>('');

  const [selectedTables, setSelectedTables] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(false);

  // Caches to prevent duplicate API requests
  const [configCache, setConfigCache] = useState<Record<string, any>>({});
  const [tablesFetchedForConn, setTablesFetchedForConn] = useState<number | null>(null);

  useEffect(() => {
    if (selectedModule && activeConnection?.id) {
      fetchData();
    }
  }, [selectedModule, activeConnection?.id]);

  const fetchData = async () => {
    if (!activeConnection || !selectedModule) return;
    try {
      // Fetch tables only if not already fetched for this connection
      if (tablesFetchedForConn !== activeConnection.id) {
        const res = await api.get(`/modules/tables?db_conn_id=${activeConnection.id}`);
        const tbd = res.data.tables_by_db;
        setTablesByDb(tbd);
        const dbs = Object.keys(tbd);
        setAvailableDatabases(dbs);
        setTablesFetchedForConn(activeConnection.id);

        if (!databaseName && dbs.length > 0) {
          setDatabaseName(res.data.database_name || dbs[0]);
        }
      }

      // Fetch module config from cache or API
      if (configCache[selectedModule]) {
        applyConfig(configCache[selectedModule]);
      } else {
        const configRes = await api.get(`/modules/config?module=${selectedModule}`);
        setConfigCache(prev => ({ ...prev, [selectedModule]: configRes.data }));
        applyConfig(configRes.data);
      }
    } catch (err) {
      console.error("Failed to fetch data", err);
    }
  };

  const applyConfig = (configData: any) => {
    if (configData && configData.tables.length > 0) {
      setDatabaseName(configData.database_name);
      setSelectedTables(configData.tables.map((t: string, i: number) => ({ id: `existing-${i}`, name: t })));
    } else {
      setSelectedTables([]);
    }
  };

  const handleAddRow = () => {
    setSelectedTables([...selectedTables, { id: Date.now().toString(), name: '' }]);
  };

  const handleRemoveRow = (id: string) => {
    setSelectedTables(selectedTables.filter(t => t.id !== id));
  };

  const handleTableSelect = (id: string, name: string) => {
    setSelectedTables(selectedTables.map(t => t.id === id ? { ...t, name } : t));
  };

  const handleSave = async () => {
    if (!selectedModule || !activeConnection || !databaseName) return;

    const tablesToSave = selectedTables.map(t => t.name).filter(n => n.trim() !== '');
    if (tablesToSave.length === 0) return;

    setLoading(true);
    try {
      await api.post('/modules/save', {
        module: selectedModule,
        database_name: databaseName,
        db_conn_id: activeConnection.id,
        tables: tablesToSave
      });
      alert('Module configuration saved and schema scanning queued in background!');

      // Clear cache for this module so it refetches next time if needed
      const newCache = { ...configCache };
      delete newCache[selectedModule];
      setConfigCache(newCache);

      // Do NOT set selectedModule(null) so we stay on the page
    } catch (err) {
      console.error("Save failed", err);
      alert('Failed to save module configuration.');
    } finally {
      setLoading(false);
    }
  };

  if (!selectedModule) {
    return (
      <div className="p-6 h-full overflow-y-auto">
        <h1 className="text-2xl font-bold mb-6 text-[#0d0d0d]">Module Configuration</h1>
        {!activeConnection && (
          <div className="p-4 bg-yellow-50 text-yellow-800 border border-yellow-200 rounded-md mb-6">
            Please connect to a database in the Connections tab first.
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {MODULES.map(mod => (
            <div
              key={mod}
              onClick={() => activeConnection && setSelectedModule(mod)}
              className={`p-6 rounded-xl border border-[#e5e5e5] bg-white shadow-sm flex flex-col items-center justify-center gap-4 transition-all duration-200 
                ${activeConnection ? 'cursor-pointer hover:shadow-md hover:border-[#10a37f]' : 'opacity-50 cursor-not-allowed'}`}
            >
              <div className="w-16 h-16 rounded-full bg-[#f4f4f4] flex items-center justify-center">
                <Database className="w-8 h-8 text-[#10a37f]" />
              </div>
              <h3 className="text-lg font-bold text-[#0d0d0d]">{mod} Module</h3>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 h-full overflow-y-auto bg-[#f9f9f9]">
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => setSelectedModule(null)}
          className="p-2 bg-white border border-[#e5e5e5] rounded-full hover:bg-[#ececf1] transition"
        >
          <ArrowLeft className="w-5 h-5 text-[#6b6b6b]" />
        </button>
        <h1 className="text-2xl font-bold text-[#0d0d0d]">Configure {selectedModule} Module</h1>
      </div>

      <div className="bg-white rounded-xl border border-[#e5e5e5] shadow-sm p-6 mb-6">
        <div className="mb-4">
          <label className="block text-sm font-bold text-[#0d0d0d] mb-1">Database Name</label>
          <select
            value={databaseName}
            onChange={(e) => setDatabaseName(e.target.value)}
            className="w-full md:w-1/2 p-2 bg-white border border-[#e5e5e5] rounded-md text-[#0d0d0d] focus:border-[#10a37f] focus:ring-1 focus:ring-[#10a37f] outline-none"
          >
            {availableDatabases.map(db => (
              <option key={db} value={db}>{db}</option>
            ))}
          </select>
        </div>

        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-[#0d0d0d]">Allowed Tables</h2>
          <button
            onClick={handleAddRow}
            className="flex items-center gap-2 px-3 py-1.5 bg-[#10a37f] text-white rounded-md text-sm hover:bg-[#0e8a6a] transition"
          >
            <Plus className="w-4 h-4" /> Add Row
          </button>
        </div>

        <div className="border border-[#e5e5e5] rounded-md overflow-hidden">
          <table className="w-full text-left">
            <thead className="bg-[#f9f9f9] border-b border-[#e5e5e5]">
              <tr>
                <th className="p-3 text-sm font-bold text-[#6b6b6b]">Database Name</th>
                <th className="p-3 text-sm font-bold text-[#6b6b6b]">Table Name</th>
                <th className="p-3 text-sm font-bold text-[#6b6b6b] w-20">Actions</th>
              </tr>
            </thead>
            <tbody>
              {selectedTables.map((row, _index) => (
                <tr key={row.id} className="border-b border-[#e5e5e5] last:border-b-0">
                  <td className="p-3">
                    <input
                      type="text"
                      value={databaseName}
                      disabled
                      className="w-full p-2 bg-[#f4f4f4] border border-[#e5e5e5] rounded-md text-[#6b6b6b]"
                    />
                  </td>
                  <td className="p-3">
                    <select
                      value={row.name}
                      onChange={(e) => handleTableSelect(row.id, e.target.value)}
                      className="w-full p-2 bg-white border border-[#e5e5e5] rounded-md text-[#0d0d0d] focus:border-[#10a37f] focus:ring-1 focus:ring-[#10a37f] outline-none"
                    >
                      <option value="">-- Select Table --</option>
                      {(tablesByDb[databaseName] || []).map(t => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                  </td>
                  <td className="p-3 text-center">
                    <button
                      onClick={() => handleRemoveRow(row.id)}
                      className="p-2 text-red-500 hover:bg-red-50 rounded-md transition"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
              {selectedTables.length === 0 && (
                <tr>
                  <td colSpan={3} className="p-6 text-center text-[#8e8e8e]">
                    No tables added yet. Click "Add Row" to start mapping tables to this module.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={loading || selectedTables.length === 0}
          className="flex items-center gap-2 px-6 py-2.5 bg-[#0d0d0d] text-white rounded-md hover:bg-[#2f2f2f] transition disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          {loading ? 'Saving & Scanning...' : 'Submit Configuration'}
        </button>
      </div>
    </div>
  );
};
