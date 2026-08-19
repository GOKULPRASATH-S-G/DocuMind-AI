import React, { useState, useEffect } from 'react';
import { ShieldAlert, ShieldCheck, AlertCircle, RefreshCw, FileText, ArrowUpDown, Filter, ChevronRight } from 'lucide-react';
import { fetchReviews } from '../services/api';

export default function ReviewQueue({ onSelectDocument }) {
  const [reviews, setReviews] = useState([]);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState('NEEDS_REVIEW');
  const [sortBy, setSortBy] = useState('date_desc');
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadQueue = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchReviews(statusFilter, page, 20, sortBy);
      setReviews(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err.message || 'Failed to load human review queue.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, [statusFilter, sortBy, page]);

  return (
    <div className="space-y-6">
      
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-800/60 p-6 rounded-2xl border border-slate-700/80 backdrop-blur shadow-xl">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2.5">
            <ShieldAlert className="w-6 h-6 text-amber-400" />
            Human-in-the-Loop Review Queue
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Inspect documents flagged by validation rules or low confidence scores. Edit values, verify business rules, and approve/reject extractions.
          </p>
        </div>

        <button
          onClick={loadQueue}
          disabled={isLoading}
          className="self-start sm:self-center px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-xl text-xs font-semibold flex items-center gap-2 border border-slate-600 transition-all"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh Queue
        </button>
      </div>

      {/* Filter Tabs & Sorting Toolbar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 bg-slate-900/60 p-3 rounded-xl border border-slate-800">
        
        {/* Status Filter Badges */}
        <div className="flex items-center gap-2 overflow-x-auto">
          {['NEEDS_REVIEW', 'APPROVED', 'REJECTED', 'ALL'].map((st) => (
            <button
              key={st}
              onClick={() => { setStatusFilter(st); setPage(1); }}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
                statusFilter === st
                  ? 'bg-sky-600 text-white shadow-md shadow-sky-600/20'
                  : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
              }`}
            >
              {st === 'NEEDS_REVIEW' ? '⚠️ Needs Review' : st === 'APPROVED' ? '✅ Approved' : st === 'REJECTED' ? '❌ Rejected' : 'All Queue Items'}
            </button>
          ))}
        </div>

        {/* Sort Selector */}
        <div className="flex items-center gap-2 text-xs">
          <ArrowUpDown className="w-4 h-4 text-slate-400" />
          <span className="text-slate-400">Sort:</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="bg-slate-800 text-slate-200 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs font-medium focus:outline-none focus:border-sky-500"
          >
            <option value="date_desc">Newest First</option>
            <option value="confidence_asc">Lowest Confidence First</option>
            <option value="confidence_desc">Highest Confidence First</option>
            <option value="date_asc">Oldest First</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-xs text-red-400 bg-red-500/10 p-3 rounded-lg border border-red-500/20">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Queue Data Table */}
      <div className="bg-slate-900/80 border border-slate-700/80 rounded-2xl overflow-hidden shadow-xl">
        {isLoading ? (
          <div className="p-12 text-center text-slate-400 text-sm flex items-center justify-center gap-3">
            <RefreshCw className="w-5 h-5 animate-spin text-sky-400" />
            Loading review queue...
          </div>
        ) : reviews.length === 0 ? (
          <div className="p-12 text-center space-y-2">
            <ShieldCheck className="w-12 h-12 text-emerald-400 mx-auto opacity-80" />
            <h3 className="text-sm font-semibold text-slate-200">No items found in review queue</h3>
            <p className="text-xs text-slate-400">
              There are no documents matching the status filter "{statusFilter}".
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left text-slate-300">
              <thead className="bg-slate-950 text-slate-400 uppercase font-semibold border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Document</th>
                  <th className="px-4 py-3 text-center">Status</th>
                  <th className="px-4 py-3 text-center">Pipeline Confidence</th>
                  <th className="px-4 py-3 text-center">Flagged Fields</th>
                  <th className="px-4 py-3">Uploaded Date</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 font-sans">
                {reviews.map((item) => (
                  <tr
                    key={item.review_id}
                    onClick={() => onSelectDocument(item.document_id)}
                    className="hover:bg-slate-800/60 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-slate-100 flex items-center gap-2">
                      <FileText className="w-4 h-4 text-sky-400 flex-shrink-0" />
                      <span className="truncate max-w-xs">{item.filename}</span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold font-mono border ${
                        item.status === 'APPROVED'
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : item.status === 'REJECTED'
                          ? 'bg-red-500/10 text-red-400 border-red-500/20'
                          : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      }`}>
                        {item.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center font-mono font-bold">
                      <span className={`px-2 py-0.5 rounded ${
                        item.overall_confidence >= 0.85
                          ? 'text-emerald-400 bg-emerald-500/10'
                          : 'text-amber-400 bg-amber-500/10'
                      }`}>
                        {(item.overall_confidence * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center font-mono">
                      {item.flagged_fields > 0 ? (
                        <span className="text-amber-400 font-bold bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                          {item.flagged_fields}
                        </span>
                      ) : (
                        <span className="text-slate-500">0</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-[11px]">
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectDocument(item.document_id);
                        }}
                        className="px-3 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1 transition-all"
                      >
                        Inspect & Review
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}
