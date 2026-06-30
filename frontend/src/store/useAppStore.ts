import { create } from 'zustand';
import api from '../api/axios';

export interface Connection {
  id: number;
  name: string;
  host: string;
  port: number;
  user: string;
  db_name: string;
  db_type: string;
  is_active: boolean;
  connection_status: string;
  last_indexed_at?: string;
  error_message?: string;
}

interface AppState {
  sidebarOpen: boolean;
  activeConnection: Connection | null;
  aiMode: 'db' | 'document';
  
  connections: Connection[];
  connectionsLoaded: boolean;
  isFetchingConnections: boolean;

  toggleSidebar: () => void;
  setActiveConnection: (conn: Connection | null) => void;
  setAiMode: (mode: 'db' | 'document') => void;
  fetchConnections: (force?: boolean) => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  sidebarOpen: true,
  activeConnection: null,
  aiMode: 'db',
  
  connections: [],
  connectionsLoaded: false,
  isFetchingConnections: false,

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setActiveConnection: (conn) => set({ activeConnection: conn, aiMode: 'db' }),
  setAiMode: (mode) => set({ aiMode: mode }),

  fetchConnections: async (force = false) => {
    const { connectionsLoaded, isFetchingConnections } = get();
    if (isFetchingConnections) return;
    if (connectionsLoaded && !force) return;

    set({ isFetchingConnections: true });
    try {
      const res = await api.get('/connections');
      set({ connections: res.data, connectionsLoaded: true });
      
      const currentActive = get().activeConnection;
      if (res.data.length > 0 && !currentActive) {
        set({ activeConnection: res.data[0] });
      } else if (res.data.length === 0 && currentActive) {
        set({ activeConnection: null });
      }
    } catch (err) {
      console.error('Error fetching connections', err);
    } finally {
      set({ isFetchingConnections: false });
    }
  }
}));
