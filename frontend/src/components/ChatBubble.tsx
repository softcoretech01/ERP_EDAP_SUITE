import React from 'react';
import { RefreshCw, Edit2, Sparkles, User, Send } from 'lucide-react';
import type { Message } from '../store/useChatStore';
import clsx from 'clsx';
import { DynamicDashboard } from './dashboard/DynamicDashboard';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatBubbleProps {
  message: Message;
  onEdit?: (id: string, content: string) => void;
  onRegenerate?: (id: string) => void;
}

export const ChatBubble: React.FC<ChatBubbleProps> = ({ message, onEdit, onRegenerate }) => {
  const isUser = message.sender === 'user';
  const [isEditing, setIsEditing] = React.useState(false);
  const [editVal, setEditVal] = React.useState(message.content);

  const handleSaveEdit = () => {
    if (onEdit && editVal.trim()) {
      onEdit(message.id, editVal);
    }
    setIsEditing(false);
  };

  return (
    <div className={clsx("flex w-full py-4 group", isUser ? "justify-end" : "justify-start")}>
      <div className={clsx("flex gap-4 max-w-[85%]", isUser ? "flex-row-reverse" : "flex-row")}>
        
        {/* Avatar */}
        <div className="flex-shrink-0 mt-1">
          {isUser ? (
            <div className="w-8 h-8 rounded-full bg-[#e5e5e5] flex items-center justify-center">
              <User className="w-4 h-4 text-[#6b6b6b]" />
            </div>
          ) : (
            <div className="w-8 h-8 rounded-full bg-[#10a37f] flex items-center justify-center shadow-sm">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
          )}
        </div>

        {/* Message Content Area */}
        <div className={clsx(
          "flex flex-col",
          isUser ? "items-end" : "items-start"
        )}>
          <div className={clsx(
            "text-[15px] leading-relaxed text-[#0d0d0d]",
            isUser ? "bg-[#f4f4f4] px-5 py-3 rounded-2xl rounded-tr-sm" : "pt-1.5"
          )}>
            {isEditing ? (
              <div className="space-y-3 min-w-[300px]">
                <textarea
                  value={editVal}
                  onChange={(e) => setEditVal(e.target.value)}
                  className="w-full bg-white border border-[#e5e5e5] rounded-lg p-3 text-sm text-[#0d0d0d] focus:outline-none focus:border-[#10a37f] resize-y"
                  rows={3}
                />
                <div className="flex gap-2 justify-end">
                  <button 
                    onClick={handleSaveEdit} 
                    className="p-1.5 bg-[#10a37f] hover:bg-[#1a7f64] rounded-md text-white transition-colors"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ) : (
              <div className="prose prose-p:leading-relaxed prose-pre:bg-[#f9f9f9] prose-pre:border prose-pre:border-[#e5e5e5] prose-pre:text-[#0d0d0d] max-w-none text-[#0d0d0d]">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.content}
                </ReactMarkdown>
              </div>
            )}

            {message.type === 'dashboard' && message.dashboardData && (
              <div className="mt-4 p-4 bg-white rounded-xl border border-[#e5e5e5] w-full shadow-sm">
                <DynamicDashboard result={message.dashboardData} />
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
            {isUser && onEdit && !isEditing && (
              <button 
                onClick={() => setIsEditing(true)}
                className="p-1.5 text-[#8e8e8e] hover:text-[#0d0d0d] hover:bg-[#f4f4f4] rounded-md transition-colors"
                title="Edit message"
              >
                <Edit2 className="w-3.5 h-3.5" />
              </button>
            )}
            {!isUser && onRegenerate && (
              <button 
                onClick={() => onRegenerate(message.id)}
                className="p-1.5 text-[#8e8e8e] hover:text-[#0d0d0d] hover:bg-[#f4f4f4] rounded-md transition-colors"
                title="Regenerate response"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
        
      </div>
    </div>
  );
};
