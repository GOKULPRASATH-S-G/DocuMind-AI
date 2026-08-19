import React from 'react';
import { CheckCircle2, Clock, AlertTriangle, RefreshCw, XCircle } from 'lucide-react';

export default function DocumentTimeline({ status, isScanned = false, isIndexed = false }) {
  const steps = [
    { key: 'UPLOAD', label: 'Upload' },
    { key: 'PAGE_INGESTION', label: 'Page Ingestion' },
    { key: 'OCR', label: isScanned ? 'OCR Engine' : 'Text Extraction' },
    { key: 'EXTRACTION', label: 'Gemini Extraction' },
    { key: 'VALIDATION', label: 'Validation Rules' },
    { key: 'CONFIDENCE', label: 'Confidence Scoring' },
    { key: 'HUMAN_REVIEW', label: 'Human Review' },
    { key: 'INDEXING', label: 'Vector Indexing' },
    { key: 'RAG_READY', label: 'RAG Ready' },
  ];

  const getStepState = (stepKey) => {
    if (status === 'FAILED') {
      return { completed: false, active: false, failed: true };
    }
    if (status === 'APPROVED') {
      if (stepKey === 'RAG_READY' || stepKey === 'INDEXING') {
        return isIndexed ? { completed: true, active: false } : { completed: false, active: true };
      }
      return { completed: true, active: false };
    }
    if (status === 'NEEDS_REVIEW') {
      if (stepKey === 'HUMAN_REVIEW') return { completed: false, active: true, needsReview: true };
      if (['UPLOAD', 'PAGE_INGESTION', 'OCR', 'EXTRACTION', 'VALIDATION', 'CONFIDENCE'].includes(stepKey)) {
        return { completed: true, active: false };
      }
      return { completed: false, active: false };
    }
    if (status === 'PROCESSING') {
      if (stepKey === 'PAGE_INGESTION' || stepKey === 'OCR') return { completed: false, active: true };
      if (stepKey === 'UPLOAD') return { completed: true, active: false };
      return { completed: false, active: false };
    }
    // Default UPLOADED
    if (stepKey === 'UPLOAD') return { completed: true, active: false };
    return { completed: false, active: false };
  };

  return (
    <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-4 space-y-3">
      <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center justify-between border-b border-slate-800 pb-2">
        <span>Document Processing Pipeline Timeline</span>
        <span className="text-[11px] font-mono text-sky-400">State: {status}</span>
      </div>

      <div className="overflow-x-auto pb-1">
        <div className="flex items-center min-w-[700px] justify-between text-xs">
          {steps.map((s, idx) => {
            const state = getStepState(s.key);
            return (
              <React.Fragment key={s.key}>
                <div className="flex flex-col items-center gap-1 text-center">
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center font-bold text-xs border transition-all ${
                      state.completed
                        ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400'
                        : state.needsReview
                        ? 'bg-amber-500/20 border-amber-500 text-amber-400 animate-pulse'
                        : state.active
                        ? 'bg-sky-500/20 border-sky-500 text-sky-400 animate-pulse'
                        : state.failed
                        ? 'bg-red-500/20 border-red-500 text-red-400'
                        : 'bg-slate-800 border-slate-700 text-slate-500'
                    }`}
                  >
                    {state.completed ? (
                      <CheckCircle2 className="w-4 h-4" />
                    ) : state.needsReview ? (
                      <AlertTriangle className="w-4 h-4" />
                    ) : state.active ? (
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    ) : state.failed ? (
                      <XCircle className="w-4 h-4" />
                    ) : (
                      <Clock className="w-3.5 h-3.5" />
                    )}
                  </div>
                  <span
                    className={`text-[10px] font-medium whitespace-nowrap max-w-[75px] truncate ${
                      state.completed
                        ? 'text-emerald-400'
                        : state.needsReview
                        ? 'text-amber-400 font-bold'
                        : state.active
                        ? 'text-sky-400 font-bold'
                        : 'text-slate-500'
                    }`}
                  >
                    {s.label}
                  </span>
                </div>

                {idx < steps.length - 1 && (
                  <div
                    className={`flex-1 h-0.5 mx-1 transition-all ${
                      state.completed ? 'bg-emerald-500/60' : 'bg-slate-800'
                    }`}
                  ></div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
}
