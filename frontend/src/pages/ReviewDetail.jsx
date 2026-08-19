import React, { useState, useEffect } from 'react';
import { ShieldCheck, CheckCircle2, ArrowLeft, FileText, Loader2, Sparkles, MessageSquare } from 'lucide-react';
import { fetchReviewDetail, getDocumentFileUrl } from '../services/api';

export default function ReviewDetail({ documentId, onBack, onNavigate }) {
  const [detail, setDetail] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [blobUrl, setBlobUrl] = useState(null);

  const loadDetail = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchReviewDetail(documentId);
      setDetail(data);
    } catch (err) {
      setError(err.message || 'Failed to load document details.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (documentId) loadDetail();
  }, [documentId]);

  useEffect(() => {
    let active = true;
    if (documentId) {
      const directUrl = getDocumentFileUrl(documentId);
      const token = localStorage.getItem('token');
      fetch(directUrl, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      })
      .then(res => {
        if (!res.ok) throw new Error('File download failed');
        return res.blob();
      })
      .then(blob => {
        if (active) {
          const url = URL.createObjectURL(blob);
          setBlobUrl(url);
        }
      })
      .catch(err => {
        console.warn("Direct blob fetch fallback:", err);
        if (active) setBlobUrl(directUrl);
      });
    }
    return () => {
      active = false;
    };
  }, [documentId]);

  if (isLoading || !detail) {
    return (
      <div className="p-12 text-center text-slate-400 flex items-center justify-center gap-3 bg-slate-900/60 rounded-2xl border border-slate-800">
        <Loader2 className="w-6 h-6 animate-spin text-sky-400" />
        <span>Loading document view...</span>
      </div>
    );
  }

  const fileUrl = getDocumentFileUrl(documentId);

  // Extract structured data if available
  const extracted = detail.validated_data || detail.data || {};
  const docTitle = extracted.document_title || detail.filename;
  const docType = extracted.document_type || (detail.is_scanned ? 'Scanned Document' : 'Native PDF');
  const summaryText = extracted.summary;
  const keyTopics = extracted.key_topics || [];

  return (
    <div className="space-y-6">
      
      {/* Navigation Header */}
      <div className="flex items-center justify-between bg-slate-800/60 p-4 rounded-2xl border border-slate-700">
        <button
          onClick={onBack}
          className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Documents
        </button>

        <div className="flex items-center gap-3 text-xs">
          <span className="text-slate-400">Document:</span>
          <span className="font-semibold text-slate-200 flex items-center gap-1.5">
            <FileText className="w-4 h-4 text-sky-400" />
            {detail.filename}
          </span>
          <span className="px-2.5 py-0.5 rounded-full font-bold font-mono border bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
            Ready
          </span>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-xs text-red-400 bg-red-500/10 p-3 rounded-lg border border-red-500/20">
          <span>{error}</span>
        </div>
      )}

      {/* Main Split-Screen Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        
        {/* Left Pane: Original Document Viewer */}
        <div className="bg-slate-900/90 border border-slate-700/80 rounded-2xl p-4 space-y-3 shadow-xl h-[780px] flex flex-col">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5 text-xs font-semibold text-slate-300">
            <span>Original Document File View</span>
            <a
              href={fileUrl}
              target="_blank"
              rel="noreferrer"
              className="text-sky-400 hover:underline"
            >
              Open File in New Tab ↗
            </a>
          </div>

          <div className="flex-1 bg-slate-950 rounded-xl overflow-hidden border border-slate-800 relative">
            {detail.mime_type && detail.mime_type.startsWith('image/') ? (
              <img
                src={blobUrl || fileUrl}
                alt={detail.filename}
                className="w-full h-full object-contain p-2"
              />
            ) : (
              <iframe
                src={blobUrl || fileUrl}
                title={detail.filename}
                className="w-full h-full border-none"
              />
            )}
          </div>
        </div>

        {/* Right Pane: Document Intelligence Analysis & Summary */}
        <div className="space-y-5">
          
          {/* Document Ready Status Banner */}
          <div className="bg-emerald-500/10 border border-emerald-500/30 p-5 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <ShieldCheck className="w-8 h-8 text-emerald-400 flex-shrink-0" />
              <div>
                <h4 className="font-bold text-sm text-emerald-200 uppercase tracking-wide">
                  ✓ Document Processed & Indexed
                </h4>
                <p className="text-xs text-slate-300 mt-0.5">
                  Available in ChromaDB vector store for instant Grounded Q&A.
                </p>
              </div>
            </div>

            {onNavigate && (
              <button
                onClick={() => onNavigate('qa')}
                className="px-4 py-2.5 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-sky-500/25 flex items-center justify-center gap-2"
              >
                <MessageSquare className="w-4 h-4" /> Ask Questions
              </button>
            )}
          </div>

          {/* Clean Document Information & Executive Summary */}
          <div className="bg-slate-900/90 border border-slate-700/80 rounded-2xl p-6 space-y-5 shadow-xl">
            <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
              <Sparkles className="w-5 h-5 text-sky-400" />
              <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                Document Intelligence Analysis
              </h3>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/80">
                <span className="text-slate-400 text-[11px] block font-medium">Document Title</span>
                <span className="font-bold text-slate-100 text-sm mt-0.5 block">{docTitle}</span>
              </div>

              <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/80">
                <span className="text-slate-400 text-[11px] block font-medium">Document Category / Type</span>
                <span className="font-semibold text-sky-400 text-sm mt-0.5 block">{docType}</span>
              </div>
            </div>

            {summaryText && (
              <div>
                <span className="text-slate-400 text-[11px] font-semibold uppercase tracking-wider block mb-2">
                  Executive Summary
                </span>
                <p className="text-xs text-slate-300 bg-slate-950/80 p-4 rounded-xl border border-slate-800 leading-relaxed font-sans">
                  {summaryText}
                </p>
              </div>
            )}

            {keyTopics && keyTopics.length > 0 && (
              <div>
                <span className="text-slate-400 text-[11px] font-semibold uppercase tracking-wider block mb-2">
                  Key Topics
                </span>
                <div className="flex flex-wrap gap-2">
                  {keyTopics.map((t, idx) => (
                    <span key={idx} className="px-3 py-1 bg-sky-500/10 text-sky-300 border border-sky-500/20 rounded-lg text-xs font-medium">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

        </div>
      </div>

    </div>
  );
}
