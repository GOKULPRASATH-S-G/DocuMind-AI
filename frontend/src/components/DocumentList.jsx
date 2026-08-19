import React, { useState } from 'react';
import { FileText, CheckCircle2, AlertTriangle, RefreshCw, Eye, Search, Trash2, Edit3 } from 'lucide-react';
import { deleteDocument } from '../services/api';

export default function DocumentList({ documents, onSelectDocument, onRefresh, onShowToast }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [deletingDocId, setDeletingDocId] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const getStatusBadge = (status) => {
    switch (status) {
      case 'APPROVED':
      case 'INDEXED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Ready
          </span>
        );
      case 'NEEDS_REVIEW':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Ready
          </span>
        );
      case 'PROCESSING':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/20 rounded-full">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            Processing
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20 rounded-full">
            <AlertTriangle className="w-3.5 h-3.5" />
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold bg-slate-800 text-slate-300 rounded-full border border-slate-700">
            Processing
          </span>
        );
    }
  };

  const getConfidenceBar = (confidence) => {
    const score = Math.round((confidence || 0) * 100);
    let colorClass = 'bg-emerald-500';
    if (score < 70) colorClass = 'bg-red-500';
    else if (score < 85) colorClass = 'bg-amber-500';

    return (
      <div className="flex items-center gap-2">
        <div className="w-16 h-2 bg-slate-700 rounded-full overflow-hidden">
          <div
            className={`h-full ${colorClass} transition-all duration-500`}
            style={{ width: `${score}%` }}
          ></div>
        </div>
        <span className="text-xs font-mono font-medium text-slate-300">{score}%</span>
      </div>
    );
  };

  const handleDeleteConfirm = async () => {
    if (!deletingDocId) return;
    setIsDeleting(true);
    try {
      await deleteDocument(deletingDocId);
      if (onShowToast) onShowToast({ type: 'success', message: 'Document deleted successfully.' });
      if (onRefresh) onRefresh();
      setDeletingDocId(null);
    } catch (err) {
      if (onShowToast) onShowToast({ type: 'error', message: err.message || 'Failed to delete document.' });
    } finally {
      setIsDeleting(false);
    }
  };

  const filteredDocs = documents.filter((doc) =>
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur space-y-4">
      
      {/* Header & Search Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <FileText className="w-5 h-5 text-sky-400" />
            Document Library ({filteredDocs.length})
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Manage your uploaded files and indexed knowledge.
          </p>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          {/* Search Input */}
          <div className="relative flex-1 sm:w-64">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by filename..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500 transition-all"
            />
          </div>

          <button
            onClick={onRefresh}
            className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-xl transition-all border border-slate-800"
            title="Refresh Library"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Document Table */}
      {filteredDocs.length === 0 ? (
        <div className="text-center py-12 text-slate-400 text-xs border border-dashed border-slate-800 rounded-xl bg-slate-950/40 space-y-2">
          <p className="font-semibold text-slate-300">
            {documents.length === 0 ? 'No documents yet.' : 'No matching documents found.'}
          </p>
          <p className="text-slate-500">
            {documents.length === 0 ? 'Upload a document above to get started.' : 'Try adjusting your search query.'}
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 text-[11px] uppercase font-semibold text-slate-400 border-b border-slate-800">
              <tr>
                <th className="px-4 py-3">Document Name</th>
                <th className="px-4 py-3">Document Type</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredDocs.map((doc) => (
                <tr key={doc.id} className="hover:bg-slate-800/30 transition-all">
                  <td className="px-4 py-3.5 font-medium text-slate-100 flex items-center gap-2">
                    <FileText className="w-4 h-4 text-sky-400 flex-shrink-0" />
                    <span className="truncate max-w-xs">{doc.filename}</span>
                  </td>

                  <td className="px-4 py-3.5 text-xs text-slate-400">
                    {doc.is_scanned ? (
                      <span className="text-amber-400 font-semibold">Scanned OCR</span>
                    ) : (
                      <span className="text-sky-400 font-semibold">Native PDF</span>
                    )}
                  </td>

                  <td className="px-4 py-3.5">{getStatusBadge(doc.processing_status)}</td>

                  <td className="px-4 py-3.5 text-right flex items-center justify-end gap-2">
                    {doc.processing_status === 'NEEDS_REVIEW' ? (
                      <button
                        onClick={() => onSelectDocument(doc.id)}
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white font-semibold rounded-lg transition-all shadow-sm"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                        Review
                      </button>
                    ) : (
                      <button
                        onClick={() => onSelectDocument(doc.id)}
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium rounded-lg border border-slate-700 transition-all"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        Open
                      </button>
                    )}

                    <button
                      onClick={() => setDeletingDocId(doc.id)}
                      className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-lg transition-colors"
                      title="Delete Document"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Delete Confirmation Modal Dialog */}
      {deletingDocId && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Trash2 className="w-5 h-5 text-red-400" />
              Delete Document?
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              This will remove the document and its indexed vector content. This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setDeletingDocId(null)}
                className="px-4 py-2 bg-slate-800 text-slate-300 hover:bg-slate-700 rounded-xl text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteConfirm}
                disabled={isDeleting}
                className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-red-600/20"
              >
                {isDeleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
