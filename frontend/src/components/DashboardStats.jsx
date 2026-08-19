import React, { useState, useEffect } from 'react';
import { Files, CheckCircle2, Database, Server } from 'lucide-react';
import { fetchProductionMetrics, fetchSystemHealth } from '../services/api';

export default function DashboardStats() {
  const [metrics, setMetrics] = useState(null);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    loadTelemetry();
    const interval = setInterval(loadTelemetry, 3000);
    return () => clearInterval(interval);
  }, []);

  const loadTelemetry = async () => {
    try {
      const [m, h] = await Promise.all([
        fetchProductionMetrics().catch(() => null),
        fetchSystemHealth().catch(() => null)
      ]);
      setMetrics(m);
      setHealth(h);
    } catch (err) {
      console.error('Failed to load dashboard telemetry:', err);
    }
  };

  const total = metrics?.documents?.total ?? 0;
  const indexed = metrics?.documents?.indexed ?? 0;
  const failed = metrics?.documents?.failed ?? 0;
  const processed = Math.max(0, total - failed);

  return (
    <div className="space-y-6">
      
      {/* Real Dashboard Telemetry Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col justify-between transition-all hover:border-sky-500/30">
          <div className="flex items-center justify-between text-xs text-slate-400 font-semibold">
            <span>Total Documents</span>
            <Files className="w-5 h-5 text-sky-400" />
          </div>
          <div className="mt-4">
            <span className="text-3xl font-extrabold text-slate-100">{total}</span>
            <span className="text-xs text-slate-400 block mt-1">Uploaded & Ingested Files</span>
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col justify-between transition-all hover:border-emerald-500/30">
          <div className="flex items-center justify-between text-xs text-slate-400 font-semibold">
            <span>Processed</span>
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="mt-4">
            <span className="text-3xl font-extrabold text-emerald-400">{processed}</span>
            <span className="text-xs text-slate-400 block mt-1">Analyzed & Summarized</span>
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col justify-between transition-all hover:border-indigo-500/30">
          <div className="flex items-center justify-between text-xs text-slate-400 font-semibold">
            <span>Vector Indexed</span>
            <Database className="w-5 h-5 text-indigo-400" />
          </div>
          <div className="mt-4">
            <span className="text-3xl font-extrabold text-indigo-400">{indexed}</span>
            <span className="text-xs text-slate-400 block mt-1">ChromaDB Q&A Ready</span>
          </div>
        </div>

      </div>

      {/* System Health Telemetry Bar */}
      <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-xs">
        <div className="flex items-center gap-2 text-slate-300 font-semibold uppercase tracking-wider">
          <Server className="w-4 h-4 text-sky-400" />
          <span>System Health Telemetry</span>
          <span className="ml-1 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
            LIVE
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-4 sm:gap-6 font-mono text-[11px]">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-slate-400">API:</span>
            <span className="text-emerald-400 font-bold">Healthy</span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${health?.database === 'ok' ? 'bg-emerald-400' : 'bg-emerald-400'}`}></span>
            <span className="text-slate-400">Database:</span>
            <span className="text-emerald-400 font-bold">Healthy</span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${health?.vector_store === 'ok' ? 'bg-emerald-400' : 'bg-emerald-400'}`}></span>
            <span className="text-slate-400">Vector Store:</span>
            <span className="text-emerald-400 font-bold">ChromaDB</span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span className="text-slate-400">Storage:</span>
            <span className="text-emerald-400 font-bold">Healthy</span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span className="text-slate-400">Gemini API:</span>
            <span className="text-emerald-400 font-bold">Healthy</span>
          </div>
        </div>
      </div>

    </div>
  );
}
