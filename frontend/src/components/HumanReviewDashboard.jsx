import React, { useState, useEffect } from 'react';
import { CheckCircle2, XCircle, AlertTriangle, FileText, Save, Loader2, Info } from 'lucide-react';
import { fetchDocumentDetail, submitReviewApproval, getDocumentFileUrl } from '../services/api';

export default function HumanReviewDashboard({ documentId, onReviewComplete }) {
  const [docDetail, setDocDetail] = useState(null);
  const [fields, setFields] = useState({});
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (documentId) {
      loadDocument(documentId);
    }
  }, [documentId]);

  const loadDocument = async (id) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchDocumentDetail(id);
      setDocDetail(data);
      setFields(data.extracted_data || {});
    } catch (err) {
      setError(err.message || 'Failed to load document review workspace.');
    } finally {
      setLoading(false);
    }
  };

  const handleFieldChange = (key, value) => {
    setFields((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (action) => {
    setSubmitting(true);
    try {
      await submitReviewApproval(documentId, fields, notes, action);
      if (onReviewComplete) onReviewComplete();
    } catch (err) {
      setError(err.message || 'Failed to submit review decisions.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400 gap-3">
        <Loader2 className="w-6 h-6 animate-spin text-sky-400" />
        <span>Loading Document Workspace & Validation Queue...</span>
      </div>
    );
  }

  if (error || !docDetail) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-6 text-red-400 text-sm">
        {error || 'Document review unavailable.'}
      </div>
    );
  }

  const confidenceScores = docDetail.field_confidence_scores || {};
  const validationErrors = docDetail.validation_errors || [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-8rem)]">
      
      {/* Left Column: Original Document Viewer */}
      <div className="lg:col-span-6 bg-slate-800/40 border border-slate-700/60 rounded-2xl p-4 flex flex-col shadow-xl">
        <div className="flex items-center justify-between pb-3 border-b border-slate-700/60 mb-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-200 truncate">
            <FileText className="w-4 h-4 text-sky-400 flex-shrink-0" />
            <span className="truncate">{docDetail.filename}</span>
          </div>
          <span className="text-xs px-2.5 py-1 bg-slate-700 text-slate-300 rounded-full font-mono">
            {docDetail.is_scanned ? 'OCR Mode' : 'Native Text'}
          </span>
        </div>
        <div className="flex-1 bg-slate-900 rounded-xl overflow-hidden border border-slate-800">
          <iframe
            src={getDocumentFileUrl(docDetail.id)}
            title="Original Document View"
            className="w-full h-full border-0"
          />
        </div>
      </div>

      {/* Right Column: Extracted Fields & Human Correction Workspace */}
      <div className="lg:col-span-6 bg-slate-800/40 border border-slate-700/60 rounded-2xl p-6 flex flex-col shadow-xl overflow-y-auto">
        <div className="flex items-center justify-between border-b border-slate-700/60 pb-4 mb-4">
          <div>
            <h2 className="text-base font-semibold text-slate-200">
              Human Review & Field Validation Workspace
            </h2>
            <p className="text-xs text-slate-400">
              Review low-confidence fields, correct misread text, and confirm auto-extracted data.
            </p>
          </div>
          <div className="text-right">
            <span className="text-xs text-slate-400 block">Overall Score</span>
            <span className={`text-lg font-bold ${
              docDetail.overall_confidence >= 0.85 ? 'text-emerald-400' : 'text-amber-400'
            }`}>
              {Math.round(docDetail.overall_confidence * 100)}%
            </span>
          </div>
        </div>

        {/* Validation Errors Notice */}
        {validationErrors.length > 0 && (
          <div className="mb-4 bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 text-xs text-amber-300">
            <div className="flex items-center gap-2 font-semibold mb-1">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              {validationErrors.length} Validation Rule Violations Flagged:
            </div>
            <ul className="list-disc pl-5 space-y-1 text-amber-200/90">
              {validationErrors.map((err, idx) => (
                <li key={idx}>
                  <strong className="font-semibold">{err.field_name}:</strong> {err.error}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Dynamic Field Inputs */}
        <div className="space-y-4 flex-1">
          {Object.keys(fields).length === 0 ? (
            <div className="text-slate-400 text-sm py-8 text-center border border-dashed border-slate-700 rounded-xl">
              No extracted key-value fields detected.
            </div>
          ) : (
            Object.entries(fields).map(([key, value]) => {
              const fieldScore = confidenceScores[key]?.confidence_score ?? 0.85;
              const hasError = confidenceScores[key]?.is_valid === false;
              
              let badgeColor = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
              if (fieldScore < 0.70 || hasError) badgeColor = 'bg-red-500/10 text-red-400 border-red-500/20';
              else if (fieldScore < 0.85) badgeColor = 'bg-amber-500/10 text-amber-400 border-amber-500/20';

              return (
                <div key={key} className="p-3.5 bg-slate-900/50 rounded-xl border border-slate-700/50">
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-xs font-semibold text-slate-300 capitalize">
                      {key.replace(/_/g, ' ')}
                    </label>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${badgeColor}`}>
                      Conf: {Math.round(fieldScore * 100)}%
                    </span>
                  </div>

                  <input
                    type="text"
                    value={typeof value === 'object' ? JSON.stringify(value) : value}
                    onChange={(e) => handleFieldChange(key, e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 focus:border-sky-500 text-slate-100 text-sm rounded-lg px-3 py-2 outline-none transition-all"
                  />

                  {hasError && (
                    <p className="mt-1 text-[11px] text-red-400 flex items-center gap-1">
                      <Info className="w-3 h-3" />
                      {confidenceScores[key]?.validation_error}
                    </p>
                  )}
                </div>
              );
            })
          )}

          {/* Reviewer Notes Input */}
          <div className="pt-2">
            <label className="text-xs font-semibold text-slate-300 mb-1 block">
              Reviewer Notes (Optional)
            </label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Corrected misread OCR digit for invoice total..."
              className="w-full bg-slate-800 border border-slate-700 focus:border-sky-500 text-slate-100 text-xs rounded-lg p-2.5 outline-none transition-all"
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3 pt-6 mt-4 border-t border-slate-700/60">
          <button
            onClick={() => handleSubmit('APPROVED')}
            disabled={submitting}
            className="flex-1 py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm rounded-xl shadow-lg shadow-emerald-600/20 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
            Approve & Index into RAG
          </button>
          
          <button
            onClick={() => handleSubmit('REJECTED')}
            disabled={submitting}
            className="py-2.5 px-4 bg-slate-800 hover:bg-red-500/20 text-red-400 border border-slate-700 hover:border-red-500/30 font-medium text-sm rounded-xl transition-all flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <XCircle className="w-4 h-4" />
            Reject Document
          </button>
        </div>
      </div>
    </div>
  );
}
