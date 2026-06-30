import React, { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, Sparkles } from 'lucide-react';
import { ChatBubble } from '../components/ChatBubble';
import { useChatStore } from '../store/useChatStore';
import type { Message } from '../store/useChatStore';
import { useAppStore } from '../store/useAppStore';
import api from '../api/axios';

export const Chat = () => {
  const { messages, addMessage, setMessages, sessionId, setSessionId, fetchSessions } = useChatStore();
  const { activeConnection, aiMode } = useAppStore();
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const askQuestion = async (queryText: string, customSessionId = sessionId) => {
    setLoading(true);

    try {
      const response = await api.post('/chat/ask', {
        query: queryText,
        db_conn_id: activeConnection ? activeConnection.id : 1,
        session_id: customSessionId,
        mode: aiMode
      });

      const resData = response.data;
      if (!resData.success) {
        addMessage({
          id: (Date.now() + 1).toString(),
          session_id: customSessionId || '',
          sender: 'assistant',
          type: 'error',
          content: resData.message || 'Sorry, I encountered an error.',
          created_at: new Date().toISOString()
        });
        return;
      }

      if (!sessionId && resData.session_id) {
        setSessionId(resData.session_id);
        fetchSessions(true);
      }

      let aiMsg: Message;
      if (resData.type === 'dashboard') {
        aiMsg = {
          id: (Date.now() + 1).toString(),
          session_id: resData.session_id,
          sender: 'assistant',
          type: 'dashboard',
          content: resData.result.summary || 'Dashboard generated.',
          dashboardData: resData.result,
          created_at: new Date().toISOString()
        };
      } else {
        aiMsg = {
          id: (Date.now() + 1).toString(),
          session_id: resData.session_id,
          sender: 'assistant',
          type: 'chat',
          content: resData.message || '',
          created_at: new Date().toISOString()
        };
      }

      addMessage(aiMsg);
    } catch (error: any) {
      addMessage({
        id: (Date.now() + 1).toString(),
        session_id: customSessionId || '',
        sender: 'assistant',
        type: 'error',
        content: error.response?.data?.message || error.message || 'Sorry, I encountered an error. Ensure your backend is running and the DB connection is active.',
        created_at: new Date().toISOString()
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      session_id: sessionId || '',
      sender: 'user',
      type: 'chat',
      content: input,
      created_at: new Date().toISOString()
    };

    addMessage(userMsg);
    setInput('');
    await askQuestion(userMsg.content);
  };

  const handleEditMessage = async (id: string, newContent: string) => {
    // Find index of the edited message
    const index = messages.findIndex((m) => m.id === id);
    if (index === -1) return;

    const editedMsg = messages[index];
    try {
      if (sessionId && editedMsg.created_at) {
        await api.delete(`/chat/sessions/${sessionId}/edit`, {
          data: { 
            edited_message_time: editedMsg.created_at,
            old_content: editedMsg.content
          }
        });
      }
    } catch (error) {
      console.error("Failed to update branch on backend:", error);
    }

    // Slice messages up to (but excluding) the edited message
    const updatedMessages = messages.slice(0, index);
    
    // Add the newly edited user message to the UI immediately
    const editedUserMsg: Message = {
      id: Date.now().toString(),
      session_id: sessionId || '',
      sender: 'user',
      type: 'chat',
      content: newContent,
      created_at: new Date().toISOString()
    };
    setMessages([...updatedMessages, editedUserMsg]);
    
    await askQuestion(newContent);
  };

  const handleRegenerateMessage = async (id: string) => {
    // Find index of the assistant message to regenerate
    const index = messages.findIndex((m) => m.id === id);
    if (index <= 0) return;

    // The user query is the message right before the assistant message
    const userQueryMessage = messages[index - 1];
    if (userQueryMessage.sender !== 'user') return;

    try {
      const assistantMsg = messages[index];
      if (sessionId && assistantMsg.created_at) {
        await api.delete(`/chat/sessions/${sessionId}/edit`, {
          data: { edited_message_time: assistantMsg.created_at }
        });
      }
    } catch (error) {
      console.error("Failed to regenerate branch on backend:", error);
    }

    // Slice messages to exclude the old assistant response
    const updatedMessages = messages.slice(0, index);
    setMessages(updatedMessages);

    await askQuestion(userQueryMessage.content);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !activeConnection) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    const uploadNotice: Message = {
      id: Date.now().toString(),
      session_id: sessionId || '',
      sender: 'user',
      type: 'chat',
      content: `Uploaded file: ${file.name}`,
      created_at: new Date().toISOString()
    };
    addMessage(uploadNotice);

    try {
      const response = await api.post('/uploads/document', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      addMessage({
        id: (Date.now() + 1).toString(),
        session_id: sessionId || '',
        sender: 'assistant',
        type: 'chat',
        content: response.data.message || `Successfully indexed ${file.name} for RAG context.`,
        created_at: new Date().toISOString()
      });
    } catch (err: any) {
      addMessage({
        id: (Date.now() + 1).toString(),
        session_id: sessionId || '',
        sender: 'assistant',
        type: 'error',
        content: `Failed to upload document: ${err.response?.data?.detail || err.message}`,
        created_at: new Date().toISOString()
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white text-[#0d0d0d] relative overflow-hidden">
      {/* Header with Mode Toggle */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[#e5e5e5] bg-white z-20">
        <div className="flex items-center gap-3">
          <Sparkles className="w-5 h-5 text-[#10a37f]" />
          <h2 className="text-lg font-semibold text-[#0d0d0d]">
            {aiMode === 'document' ? 'Document AI' : 'Database AI'}
          </h2>
        </div>
        <button
          onClick={() => {
            useAppStore.getState().setAiMode(aiMode === 'db' ? 'document' : 'db');
          }}
          className={`px-4 py-1.5 text-sm font-bold rounded-lg transition-colors border shadow-sm ${
            aiMode === 'db' 
              ? 'bg-white border-[#e5e5e5] text-[#0d0d0d] hover:bg-[#f4f4f4]' 
              : 'bg-[#10a37f] border-[#10a37f] text-white hover:bg-[#1a7f64]'
          }`}
        >
          {aiMode === 'db' ? 'Switch to Document Mode' : 'Switch to Database Mode'}
        </button>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 overflow-y-auto px-4 md:px-0 py-6 pb-40 z-10">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center select-none pt-[15vh]">
            <div className="w-16 h-16 bg-[#f9f9f9] border border-[#e5e5e5] rounded-full flex items-center justify-center mb-6 shadow-sm">
              <Sparkles className="w-8 h-8 text-[#10a37f]" />
            </div>
            <h1 className="text-2xl md:text-3xl font-semibold text-[#0d0d0d] tracking-tight mb-3">
              How can I help you today?
            </h1>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-2">
            {messages.map((msg) => (
              <ChatBubble 
                key={msg.id} 
                message={msg} 
                onEdit={handleEditMessage} 
                onRegenerate={handleRegenerateMessage}
              />
            ))}
          </div>
        )}

        {(loading || uploading) && (
          <div className="max-w-3xl mx-auto p-4 flex gap-4 items-center">
            <div className="flex-shrink-0 mt-1">
              <div className="w-8 h-8 rounded-full bg-[#10a37f] flex items-center justify-center shadow-sm animate-pulse">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
            </div>
            <div className="flex-1 space-y-2">
              <div className="h-2.5 bg-[#f4f4f4] rounded w-1/3 animate-pulse" />
              <div className="h-2.5 bg-[#f4f4f4] rounded w-1/2 animate-pulse" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Centered Floating Input Container */}
      <div className="absolute bottom-0 left-0 right-0 p-4 md:p-6 bg-gradient-to-t from-white via-white/90 to-transparent z-10">
        <div className="max-w-3xl mx-auto relative">
          <form
            onSubmit={handleSend}
            className="flex items-end gap-2 bg-[#f4f4f4] rounded-[24px] py-3 px-4 focus-within:ring-1 focus-within:ring-[#e5e5e5] transition-all duration-200"
          >
            {/* Hidden Input File */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              className="hidden"
              accept=".pdf,.txt,.csv,.doc,.docx,.xls,.xlsx"
            />

            {/* Attachment Button */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading || (aiMode === 'db' && !activeConnection)}
              className="p-1.5 text-[#6b6b6b] hover:text-[#0d0d0d] bg-transparent rounded-full disabled:opacity-30 transition-colors"
            >
              <Paperclip className="w-5 h-5" />
            </button>

            {/* Chat Input Field */}
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend(e as any);
                }
              }}
              disabled={loading || (aiMode === 'db' && !activeConnection)}
              placeholder={(aiMode === 'document' || activeConnection) ? "Message EDIP..." : "Select a database connection first..."}
              className="flex-1 bg-transparent border-none text-[#0d0d0d] focus:outline-none focus:ring-0 placeholder-[#8e8e8e] text-[15px] max-h-[200px] py-1.5 resize-none disabled:opacity-50 overflow-y-auto"
              rows={1}
              style={{ minHeight: '40px' }}
            />

            {/* Send Button */}
            <button
              type="submit"
              disabled={!input.trim() || loading || (aiMode === 'db' && !activeConnection)}
              className="p-2 bg-[#0d0d0d] hover:bg-[#2f2f2f] text-white rounded-full transition-all duration-200 disabled:opacity-30 disabled:bg-[#e5e5e5] disabled:text-[#8e8e8e] mb-0.5"
            >
              <Send className="w-4 h-4 ml-0.5" />
            </button>
          </form>

          {/* Legal/System text */}
          <div className="text-center text-[10px] text-slate-500 font-medium mt-3 tracking-wider">
            EDIP AI Assistant V2 can make mistakes. Verify critical data.
          </div>
        </div>
      </div>
    </div>
  );
};
