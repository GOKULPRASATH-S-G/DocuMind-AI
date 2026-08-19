import React, { useEffect } from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export default function NotificationToast({ toast, onClose }) {
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => {
        onClose();
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [toast, onClose]);

  if (!toast) return null;

  const isError = toast.type === 'error';
  const isInfo = toast.type === 'info';

  return (
    <div className="fixed bottom-6 right-6 z-50 animate-bounce-short">
      <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border shadow-2xl backdrop-blur text-xs font-semibold ${
        isError
          ? 'bg-red-950/90 text-red-200 border-red-800'
          : isInfo
          ? 'bg-sky-950/90 text-sky-200 border-sky-800'
          : 'bg-emerald-950/90 text-emerald-200 border-emerald-800'
      }`}>
        {isError ? (
          <AlertCircle className="w-4 h-4 text-red-400" />
        ) : isInfo ? (
          <Info className="w-4 h-4 text-sky-400" />
        ) : (
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
        )}
        <span>{toast.message}</span>
        <button
          onClick={onClose}
          className="ml-2 p-1 hover:bg-slate-800 rounded-md text-slate-400 hover:text-slate-200"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
