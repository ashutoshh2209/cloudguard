import React, { useState, useRef, useEffect } from 'react';
import { X, Send, Sparkles, Loader2, Bot, User } from 'lucide-react';
import { Button } from './ui/Button';
import { aiApi } from '../api/ai';
import { CopilotMessage } from '../types/api';
import { useAuth } from '../context/AuthContext';
import ReactMarkdown from 'react-markdown';

interface CopilotDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  scanId?: string;
}

export function CopilotDrawer({ isOpen, onClose, scanId }: CopilotDrawerProps) {
  const { activeWorkspace } = useAuth();
  const [messages, setMessages] = useState<CopilotMessage[]>([
    { role: 'assistant', content: 'Hello! I am CloudGuard Copilot. Ask me questions about your security posture or findings.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handleSend = async (messageText?: string) => {
    const textToSend = (messageText || input).trim();
    if (!textToSend || loading) return;
    
    const userMessage: CopilotMessage = { role: 'user', content: textToSend };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput('');
    setLoading(true);

    try {
      const response = await aiApi.askCopilot({
        message: userMessage.content,
        scan_id: scanId,
        workspace_id: activeWorkspace?.id,
        history: messages
      });
      
      setMessages([...newMessages, { role: 'assistant', content: response.answer }]);
    } catch (err: any) {
      console.error('Copilot error:', err);
      setMessages([...newMessages, { 
        role: 'assistant', 
        content: err.message || 'I am temporarily unavailable. Please try again later.' 
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!isOpen) return null;

  return (
    <>
      <div 
        className="fixed inset-0 bg-[var(--scrim)] z-40 transition-opacity backdrop-blur-sm"
        onClick={onClose}
      />
      
      <div className="fixed inset-y-0 right-0 w-[400px] bg-surface-1 border-l border-line z-50 shadow-elev-4 flex flex-col animate-in slide-in-from-right-full duration-300">
        
        {/* Header */}
        <div className="px-5 py-4 border-b border-line flex items-center justify-between bg-surface-1">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-accent-9" />
            <h2 className="text-[15px] font-bold text-content">Security Copilot</h2>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 hover:bg-surface-3 text-content-muted hover:text-content rounded-md transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scan Context */}
        {scanId && (
          <div className="px-5 py-2 bg-surface-2 border-b border-line text-[11px] font-mono text-content-muted flex items-center justify-between">
            <span>Analyzing Scan: {scanId.substring(0, 8)}</span>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-5 space-y-6 bg-canvas">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                msg.role === 'assistant' ? 'bg-accent-subtle text-accent-10 border border-accent-border' : 'bg-surface-3 text-content'
              }`}>
                {msg.role === 'assistant' ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
              </div>
              <div className={`text-[13px] leading-relaxed max-w-[80%] px-4 py-3 rounded-2xl ${
                msg.role === 'user' ? 'bg-surface-3 text-content' : 'bg-surface-1 border border-line text-content-secondary'
              }`}>
                {msg.role === 'assistant' ? (
                  <div className="prose prose-sm prose-invert max-w-none prose-p:leading-relaxed prose-pre:bg-surface-2 prose-pre:border prose-pre:border-line">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                ) : (
                  msg.content
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-accent-subtle text-accent-10 border border-accent-border flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4" />
              </div>
              <div className="text-[13px] bg-surface-1 border border-line px-4 py-3 rounded-2xl flex items-center gap-2 text-content-muted">
                <Loader2 className="w-3 h-3 animate-spin" />
                Thinking...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick prompt chips */}
        <div className="px-4 py-2 border-t border-line bg-surface-1/50 flex flex-wrap gap-1.5">
          <button 
            type="button"
            onClick={() => handleSend("What are my most critical risks?")}
            disabled={loading}
            className="text-[11px] px-2 py-0.5 rounded bg-surface-2 hover:bg-surface-3 text-content-secondary border border-line transition-colors"
          >
            Critical risks?
          </button>
          <button 
            type="button"
            onClick={() => handleSend("Why is my security score low?")}
            disabled={loading}
            className="text-[11px] px-2 py-0.5 rounded bg-surface-2 hover:bg-surface-3 text-content-secondary border border-line transition-colors"
          >
            Why is score low?
          </button>
          <button 
            type="button"
            onClick={() => handleSend("What should I fix first?")}
            disabled={loading}
            className="text-[11px] px-2 py-0.5 rounded bg-surface-2 hover:bg-surface-3 text-content-secondary border border-line transition-colors"
          >
            What to fix first?
          </button>
        </div>

        {/* Input */}
        <div className="p-4 bg-surface-1 border-t border-line">
          <div className="relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your security posture..."
              className="w-full bg-surface-2 border border-line rounded-lg pl-4 pr-12 py-3 text-[13px] text-content placeholder:text-content-muted focus:outline-none focus:border-accent-9/50 resize-none h-14"
              rows={1}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || loading}
              className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center rounded-md text-content-muted hover:text-content hover:bg-surface-3 disabled:opacity-50 transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <div className="text-[10px] text-content-muted text-center mt-2">
            AI-generated guidance. Verify changes before implementation.
          </div>
        </div>
      </div>
    </>
  );
}
