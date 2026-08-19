import React, { useState, useEffect, useRef } from 'react';
import {
  MessageSquare,
  Send,
  FileText,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  X,
  ExternalLink,
  Layers,
  Filter,
  Sparkles,
  Info,
  ChevronRight
} from 'lucide-react';
import { askQA, fetchDocuments } from '../services/api';

export default function QA({ onSelectDocument }) {
  const [messages, setMessages] = useState([
    {
      sender: 'ai',
      answer: 'Welcome! I am your Grounded RAG Assistant. Ask me any question, and I will synthesize an answer strictly derived from document evidence with exact page citations.',
      citations: [],
      insufficient_evidence: false,
      confidence: 1.0,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [topK, setTopK] = useState(5);
  const [selectedDocId, setSelectedDocId] = useState('');
  const [approvedDocs, setApprovedDocs] = useState([]);
  const [inspectCitation, setInspectCitation] = useState(null);

  const chatEndRef = useRef(null);

  useEffect(() => {
    loadApprovedDocuments();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const loadApprovedDocuments = async () => {
    try {
      const docs = await fetchDocuments();
      // Filter for approved / indexed documents
      const indexed = docs.filter(
        d => d.processing_status === 'APPROVED' || d.processing_status === 'INDEXED'
      );
      setApprovedDocs(indexed);
    } catch (err) {
      console.error('Failed to load documents for filter:', err);
    }
  };

  const handleSend = async (queryText = inputQuery) => {
    const q = queryText.trim();
    if (!q || loading) return;

    setError(null);
    setInputQuery('');
    const userMsg = {
      sender: 'user',
      text: q,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await askQA(q, topK, selectedDocId || null);
      const aiMsg = {
        sender: 'ai',
        answer: res.answer,
        citations: res.citations || [],
        insufficient_evidence: res.insufficient_evidence || false,
        confidence: res.confidence,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch (err) {
      setError(err.message || 'Failed to generate answer.');
    } finally {
      setLoading(false);
    }
  };

  const sampleQuestions = [
    'What is the total invoice amount?',
    'Who is the client?',
    'What services were provided?',
    'Summarize this document.',
    'What items were purchased?'
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-10rem)] max-w-6xl mx-auto space-y-4">
      
      {/* Header & Filter Bar */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-xl backdrop-blur flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 rounded-xl">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              Ask your documents
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-medium">
                Grounded RAG Active
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Strictly grounded answers with page attribution & source evidence
            </p>
          </div>
        </div>

        {/* Filter Controls */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-800/80 px-3 py-1.5 rounded-xl border border-slate-700/60 text-xs">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400 font-medium">Document:</span>
            <select
              value={selectedDocId}
              onChange={e => setSelectedDocId(e.target.value)}
              className="bg-transparent text-slate-200 font-medium focus:outline-none cursor-pointer"
            >
              <option value="" className="bg-slate-900 text-slate-200">
                All Approved Documents ({approvedDocs.length})
              </option>
              {approvedDocs.map(doc => (
                <option key={doc.id} value={doc.id} className="bg-slate-900 text-slate-200">
                  {doc.filename} ({doc.id.slice(0, 8)} • {doc.processing_status})
                </option>
              ))}

            </select>
          </div>

          <div className="flex items-center gap-2 bg-slate-800/80 px-3 py-1.5 rounded-xl border border-slate-700/60 text-xs">
            <Layers className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400 font-medium">Top-K:</span>
            <select
              value={topK}
              onChange={e => setTopK(Number(e.target.value))}
              className="bg-transparent text-slate-200 font-medium focus:outline-none cursor-pointer"
            >
              <option value={3} className="bg-slate-900">Top 3 Chunks</option>
              <option value={5} className="bg-slate-900">Top 5 Chunks</option>
              <option value={10} className="bg-slate-900">Top 10 Chunks</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Chat Stream Container */}
      <div className="flex-1 bg-slate-900/60 border border-slate-800 rounded-2xl p-6 overflow-y-auto space-y-6 shadow-inner backdrop-blur custom-scrollbar">
        {messages.map((msg, index) => (
          <div key={index} className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
            
            {/* Sender Metadata */}
            <div className="flex items-center gap-2 mb-1 px-1 text-xs text-slate-400">
              <span className="font-semibold text-slate-300">
                {msg.sender === 'user' ? 'You' : 'Grounded AI Assistant'}
              </span>
              <span>•</span>
              <span>{msg.timestamp}</span>
            </div>

            {/* Bubble Content */}
            <div
              className={`max-w-3xl rounded-2xl p-4 border transition-all ${
                msg.sender === 'user'
                  ? 'bg-sky-600/90 text-white border-sky-500/40 shadow-lg shadow-sky-600/20'
                  : msg.insufficient_evidence
                  ? 'bg-slate-800/90 border-amber-500/40 text-slate-200'
                  : 'bg-slate-800/90 border-slate-700/60 text-slate-200 shadow-md'
              }`}
            >
              {msg.sender === 'user' ? (
                <p className="text-sm font-medium whitespace-pre-wrap">{msg.text}</p>
              ) : (
                <div className="space-y-4">
                  {/* Status Badges */}
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-700/50 pb-2.5">
                    {msg.insufficient_evidence ? (
                      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs font-semibold">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        Insufficient Document Evidence
                      </div>
                    ) : (
                      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-semibold">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Evidence Grounded Answer
                      </div>
                    )}

                    {msg.confidence !== null && msg.confidence !== undefined && (
                      <div className="text-xs text-slate-400 font-mono">
                        Grounding Confidence: <span className="text-sky-400 font-bold">{(msg.confidence * 100).toFixed(0)}%</span>
                      </div>
                    )}
                  </div>

                  {/* Text Content */}
                  <p className="text-sm leading-relaxed text-slate-100 whitespace-pre-wrap font-sans">
                    {msg.answer}
                  </p>

                  {/* Source Citations */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-slate-700/50 space-y-2">
                      <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5 text-indigo-400" />
                        Verified Source Citations ({msg.citations.length})
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {msg.citations.map((citation, cIdx) => {
                          const isVisual = citation.source_type === 'VISUAL' || Boolean(citation.image_id);
                          const isTable = citation.source_type === 'TABLE';

                          return (
                            <button
                              key={cIdx}
                              onClick={() => setInspectCitation(citation)}
                              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs transition-all shadow-sm ${
                                isVisual
                                  ? 'bg-purple-950/60 border-purple-800/60 hover:bg-purple-900/60 hover:border-purple-500 text-purple-300'
                                  : isTable
                                  ? 'bg-emerald-950/60 border-emerald-800/60 hover:bg-emerald-900/60 hover:border-emerald-500 text-emerald-300'
                                  : 'bg-indigo-950/60 border-indigo-800/60 hover:bg-indigo-900/60 hover:border-indigo-500 text-indigo-300'
                              }`}
                            >
                              <span>{isVisual ? '📊' : isTable ? '📋' : '📄'}</span>
                              <span className="font-medium truncate max-w-[180px]">
                                {isVisual ? 'Visual Evidence' : isTable ? 'Table Evidence' : 'Text Evidence'}
                              </span>
                              <span className="text-slate-400 text-[11px] truncate max-w-[120px]">
                                ({citation.filename})
                              </span>
                              <span className="px-1.5 py-0.5 rounded bg-slate-900/80 text-slate-200 text-[10px] font-bold">
                                Page {citation.page_number}
                              </span>
                              <ChevronRight className="w-3 h-3 text-slate-400" />
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Loading Skeleton */}
        {loading && (
          <div className="flex flex-col items-start space-y-2 animate-pulse">
            <div className="text-xs text-slate-400">Grounded AI Assistant is retrieving & synthesizing...</div>
            <div className="bg-slate-800/80 border border-slate-700/60 rounded-2xl p-4 max-w-lg space-y-3">
              <div className="h-4 bg-slate-700 rounded w-3/4"></div>
              <div className="h-4 bg-slate-700 rounded w-1/2"></div>
              <div className="h-3 bg-slate-700/60 rounded w-full"></div>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Quick Prompts & Input Bar */}
      <div className="space-y-2">
        {/* Sample Question Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
          <span className="text-slate-400 font-medium flex items-center gap-1 shrink-0">
            <HelpCircle className="w-3.5 h-3.5" /> Sample Questions:
          </span>
          {sampleQuestions.map((sq, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(sq)}
              disabled={loading}
              className="shrink-0 px-3 py-1 bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white rounded-full border border-slate-700/60 transition-all font-medium"
            >
              {sq}
            </button>
          ))}
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-3 bg-red-950/80 border border-red-800/80 rounded-xl text-xs text-red-300 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-400" />
              <span>{error}</span>
            </div>
            <button onClick={() => setError(null)} className="text-red-400 hover:text-red-200">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Input Text Box */}
        <form
          onSubmit={e => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-3 bg-slate-900 border border-slate-800 p-2 rounded-2xl shadow-xl focus-within:border-sky-500/60 transition-all"
        >
          <input
            type="text"
            value={inputQuery}
            onChange={e => setInputQuery(e.target.value)}
            placeholder="What would you like to know?"
            disabled={loading}
            className="flex-1 bg-transparent px-3 py-2 text-slate-100 placeholder-slate-500 text-sm focus:outline-none"
          />

          <button
            type="submit"
            disabled={!inputQuery.trim() || loading}
            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white font-semibold text-sm rounded-xl shadow-lg shadow-sky-500/25 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            <Send className="w-4 h-4" />
            Ask
          </button>
        </form>
      </div>

      {/* Citation Inspector Modal */}
      {inspectCitation && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-5 shadow-2xl animate-in fade-in zoom-in-95 duration-150 max-h-[90vh] overflow-y-auto">
            
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 rounded-xl">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Source Citation Details</h3>
                  <p className="text-xs text-slate-400">Verifiable document provenance & chunk evidence</p>
                </div>
              </div>
              <button
                onClick={() => setInspectCitation(null)}
                className="p-1 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Citation Metadata Grid */}
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700/50 space-y-1">
                <span className="text-slate-400 font-medium">Filename</span>
                <p className="text-slate-200 font-bold truncate">{inspectCitation.filename}</p>
              </div>

              <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700/50 space-y-1">
                <span className="text-slate-400 font-medium">Page Number</span>
                <p className="text-indigo-400 font-bold">Page {inspectCitation.page_number}</p>
              </div>

              <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700/50 space-y-1">
                <span className="text-slate-400 font-medium">Source Type</span>
                <p className="text-emerald-400 font-bold font-mono uppercase">{inspectCitation.source_type || 'TEXT'}</p>
              </div>

              <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700/50 space-y-1">
                <span className="text-slate-400 font-medium">Image ID</span>
                <p className="text-purple-400 font-bold font-mono truncate">{inspectCitation.image_id || 'N/A'}</p>
              </div>

              <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700/50 space-y-1 col-span-2">
                <span className="text-slate-400 font-medium">Document ID</span>
                <p className="text-slate-300 font-mono text-[11px] truncate">{inspectCitation.document_id}</p>
              </div>
            </div>

            {/* Visual Evidence Image Viewer */}
            {(inspectCitation.source_type === 'VISUAL' || inspectCitation.image_id) && (
              <div className="space-y-2">
                <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider flex items-center gap-1.5">
                  📊 Extracted Visual Artifact Image
                </span>
                <div className="bg-slate-950 p-2 rounded-xl border border-purple-900/60 flex justify-center items-center overflow-hidden">
                  <img
                    src={`/api/v1/documents/${inspectCitation.document_id}/images/${inspectCitation.image_id || 'img_1'}`}
                    alt="Visual Artifact Evidence"
                    className="max-h-64 object-contain rounded-lg shadow-md"
                    onError={(e) => {
                      e.target.onerror = null;
                      e.target.style.display = 'none';
                    }}
                  />
                </div>
              </div>
            )}

            {/* Quoted Evidence Snippet */}
            <div className="space-y-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Retrieved Evidence Snippet
              </span>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs text-slate-200 font-mono leading-relaxed max-h-48 overflow-y-auto whitespace-pre-wrap">
                {inspectCitation.quoted_evidence}
              </div>
            </div>


            {/* Modal Actions */}
            <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
              {onSelectDocument && inspectCitation.document_id && (
                <button
                  onClick={() => {
                    const docId = inspectCitation.document_id;
                    setInspectCitation(null);
                    onSelectDocument(docId);
                  }}
                  className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition-all"
                >
                  <ExternalLink className="w-4 h-4" />
                  Inspect Document in Queue
                </button>
              )}
              <button
                onClick={() => setInspectCitation(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl"
              >
                Close
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
