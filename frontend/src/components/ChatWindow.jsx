import React, { useState } from 'react';
import { Send, Bot, User, BookOpen, Sparkles, Loader2 } from 'lucide-react';
import { queryRag } from '../services/api';

export default function ChatWindow() {
  const [messages, setMessages] = useState([
    {
      sender: 'bot',
      text: 'Hello! I am your MultiModal Document RAG Assistant. Ask me any question about your processed documents, tables, or scanned invoices!',
      citations: []
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg = { sender: 'user', text: input, citations: [] };
    setMessages((prev) => [...prev, userMsg]);
    const currentQuestion = input;
    setInput('');
    setLoading(true);

    try {
      const res = await queryRag(currentQuestion);
      const botMsg = {
        sender: 'bot',
        text: res.answer,
        citations: res.citations || []
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          sender: 'bot',
          text: `Error processing question: ${err.message || 'Failed to query RAG database.'}`,
          citations: []
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto bg-slate-800/40 border border-slate-700/60 rounded-2xl flex flex-col h-[calc(100vh-8rem)] shadow-xl backdrop-blur">
      
      {/* Header */}
      <div className="p-4 border-b border-slate-700/60 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-xl">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-200">
              Source-Attributed RAG Intelligence
            </h2>
            <p className="text-xs text-slate-400">
              Retrieves semantic chunks from ChromaDB and synthesizes answers using Gemini.
            </p>
          </div>
        </div>
      </div>

      {/* Messages Stream */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex gap-3 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.sender === 'bot' && (
              <div className="w-8 h-8 rounded-full bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4" />
              </div>
            )}

            <div className={`max-w-2xl rounded-2xl p-4 text-sm ${
              msg.sender === 'user'
                ? 'bg-sky-600 text-white rounded-tr-none'
                : 'bg-slate-900 border border-slate-700/80 text-slate-200 rounded-tl-none'
            }`}>
              <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>

              {/* Citations list */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-4 pt-3 border-t border-slate-800 space-y-2">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-indigo-400">
                    <BookOpen className="w-3.5 h-3.5" />
                    Source References ({msg.citations.length}):
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {msg.citations.map((cite, cIdx) => (
                      <div
                        key={cIdx}
                        className="bg-slate-800/80 p-2.5 rounded-lg border border-slate-700/50 text-xs"
                      >
                        <div className="font-medium text-slate-200 truncate">
                          📄 {cite.document_name}
                        </div>
                        <div className="flex justify-between text-[11px] text-slate-400 mt-1">
                          <span>Page {cite.page_number}</span>
                          <span className="text-emerald-400 font-mono">
                            Score: {Math.round(cite.similarity_score * 100)}%
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 italic">
                          "{cite.chunk_snippet}"
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {msg.sender === 'user' && (
              <div className="w-8 h-8 rounded-full bg-sky-600/20 text-sky-400 border border-sky-500/30 flex items-center justify-center flex-shrink-0">
                <User className="w-4 h-4" />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex gap-3 justify-start">
            <div className="w-8 h-8 rounded-full bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center flex-shrink-0 animate-pulse">
              <Bot className="w-4 h-4" />
            </div>
            <div className="bg-slate-900 border border-slate-700/80 rounded-2xl rounded-tl-none p-4 text-xs text-slate-400 flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
              Retrieving context & generating answer...
            </div>
          </div>
        )}
      </div>

      {/* Input Bar */}
      <form onSubmit={handleSend} className="p-4 border-t border-slate-700/60 flex gap-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about your uploaded documents..."
          className="flex-1 bg-slate-900 border border-slate-700 focus:border-indigo-500 text-slate-100 text-sm rounded-xl px-4 py-2.5 outline-none transition-all"
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl text-sm font-medium transition-all shadow-lg shadow-indigo-600/25 flex items-center gap-2"
        >
          <Send className="w-4 h-4" />
          Ask
        </button>
      </form>

    </div>
  );
}
