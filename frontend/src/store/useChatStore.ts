import { create } from 'zustand';
import api from '../api/axios';

export interface DashboardResponse {
  title: string;
  chartType: 'bar' | 'line' | 'pie' | 'table' | 'kpi';
  data: {
    labels: string[];
    datasets: {
      label: string;
      data: number[];
    }[];
  };
  summary: string;
}

export interface Message {
  id: string;
  session_id: string;
  sender: 'user' | 'assistant';
  content: string;
  type: 'chat' | 'dashboard' | 'error';
  dashboardData?: DashboardResponse;
  created_at: string;
}

export interface ChatSession {
  session_id: string;
  title: string;
  created_at: string;
}

interface ChatState {
  sessionId: string | null;
  messages: Message[];
  sessions: ChatSession[];
  sessionsLoaded: boolean;
  isFetchingSessions: boolean;
  setSessionId: (id: string | null) => void;
  addMessage: (message: Message) => void;
  setMessages: (messages: Message[]) => void;
  clearChat: () => void;
  fetchSessions: (force?: boolean) => Promise<void>;
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessionId: null,
  messages: [],
  sessions: [],
  sessionsLoaded: false,
  isFetchingSessions: false,
  setSessionId: (id) => set({ sessionId: id }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  setMessages: (messages) => set({ messages }),
  clearChat: () => set({ messages: [], sessionId: null }),
  fetchSessions: async (force = false) => {
    const { sessionsLoaded, isFetchingSessions } = get();
    if (isFetchingSessions) return;
    if (sessionsLoaded && !force) return;

    set({ isFetchingSessions: true });
    try {
      const res = await api.get('/chat/sessions');
      set({ sessions: res.data, sessionsLoaded: true });
    } catch (err) {
      console.error('Error fetching sessions', err);
    } finally {
      set({ isFetchingSessions: false });
    }
  }
}));

