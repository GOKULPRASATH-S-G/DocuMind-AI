import React, { useState } from 'react';
import { Settings as SettingsIcon, Terminal, ShieldCheck, Cpu, Database, Server, RefreshCw } from 'lucide-react';
import Evaluation from './Evaluation';
import Search from './Search';

export default function Settings({ onRefreshData, onShowToast }) {
  const [developerMode, setDeveloperMode] = useState(false);
  const [adminTab, setAdminTab] = useState('eval');

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      
      {/* Header */}
      <div className="bg-slate-900/60 p-6 rounded-2xl border border-slate-800 shadow-xl backdrop-blur flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-slate-800 text-sky-400 rounded-xl border border-slate-700">
            <SettingsIcon className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Application Settings & Configuration</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Manage system preferences, view environment details, and toggle Developer/Admin mode.
            </p>
          </div>
        </div>

        {/* Developer / Admin Mode Toggle Switch */}
        <div className="flex items-center gap-3 bg-slate-950 p-2 rounded-xl border border-slate-800">
          <div className="flex flex-col text-right text-xs">
            <span className="font-bold text-slate-200">Developer / Admin Mode</span>
            <span className="text-[10px] text-slate-500">Expose technical pipeline stages</span>
          </div>
          <button
            onClick={() => {
              const next = !developerMode;
              setDeveloperMode(next);
              if (onShowToast) {
                onShowToast({
                  type: 'info',
                  message: next ? 'Developer / Admin Mode enabled.' : 'Standard User Mode active.'
                });
              }
            }}
            className={`w-12 h-6 flex items-center rounded-full p-1 transition-all ${
              developerMode ? 'bg-sky-600 justify-end' : 'bg-slate-800 justify-start'
            }`}
          >
            <div className="w-4 h-4 rounded-full bg-white shadow-md"></div>
          </button>
        </div>
      </div>

      {/* System Environment Details Card */}
      <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2 border-b border-slate-800 pb-3">
          <Server className="w-4 h-4 text-sky-400" />
          System Infrastructure Specifications
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono">
          <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800">
            <span className="text-slate-500 block text-[10px] uppercase">Extraction Model</span>
            <span className="text-sky-300 font-bold">Gemini 2.5 Flash</span>
          </div>
          <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800">
            <span className="text-slate-500 block text-[10px] uppercase">OCR Engine</span>
            <span className="text-emerald-400 font-bold">Tesseract OCR</span>
          </div>
          <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800">
            <span className="text-slate-500 block text-[10px] uppercase">Vector Database</span>
            <span className="text-indigo-400 font-bold">ChromaDB Store</span>
          </div>
          <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800">
            <span className="text-slate-500 block text-[10px] uppercase">API Gateway</span>
            <span className="text-amber-400 font-bold">FastAPI + Uvicorn</span>
          </div>
        </div>
      </div>

      {/* Developer / Admin Section (Exposed when toggle is ON) */}
      {developerMode && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div className="flex items-center gap-2 font-bold text-sm text-amber-400">
              <Terminal className="w-5 h-5" />
              Developer / Admin Pipeline Inspector (Phases 1 - 9)
            </div>

            <div className="flex items-center gap-2 text-xs">
              <button
                onClick={() => setAdminTab('eval')}
                className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                  adminTab === 'eval'
                    ? 'bg-purple-600 text-white'
                    : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                Evaluation Benchmarks
              </button>
              <button
                onClick={() => setAdminTab('chroma')}
                className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                  adminTab === 'chroma'
                    ? 'bg-indigo-600 text-white'
                    : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                Vector Store Inspector
              </button>
            </div>
          </div>

          {adminTab === 'eval' ? (
            <Evaluation />
          ) : (
            <Search />
          )}
        </div>
      )}

    </div>
  );
}
