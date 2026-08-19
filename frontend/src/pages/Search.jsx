import React, { useState } from 'react';
import { Search as SearchIcon, FileText, Database, Layers, Loader2, AlertCircle, Sparkles } from 'lucide-react';
import { searchVectorStore } from '../services/api';

export default function Search() {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchedQuery, setSearchedQuery] = useState('');

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsLoading(true);
    setError(null);
    try {
      const data = await searchVectorStore(query, topK);
      setResults(data.results || []);
      setSearchedQuery(query);
    } catch (err) {
      setError(err.message || 'Semantic search failed.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header Banner */}
      <div className="bg-slate-800/60 p-6 rounded-2xl border border-slate-700/80 backdrop-blur shadow-xl space-y-2">
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2.5">
          <Database className="w-6 h-6 text-sky-400" />
          Semantic Vector Store Search
        </h1>
        <p className="text-xs text-slate-400">
          Search indexed vector embeddings across approved documents. Results show exact page provenance and chunk source type (Text vs Table).
        </p>
      </div>

      {/* Search Bar Form */}
      <form onSubmit={handleSearch} className="bg-slate-900/80 p-4 rounded-2xl border border-slate-700/80 shadow-xl space-y-3">
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <SearchIcon className="w-5 h-5 absolute left-3.5 top-3.5 text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. What is the total invoice amount?"
              className="w-full pl-11 pr-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-sm text-slate-100 font-sans focus:outline-none focus:border-sky-500 transition-all"
            />
          </div>

          <div className="flex items-center gap-3 self-end sm:self-auto">
            <div className="flex items-center gap-2 text-xs text-slate-400 font-medium">
              <span>Top K:</span>
              <select
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="bg-slate-950 text-slate-200 border border-slate-700 rounded-lg px-2.5 py-2 text-xs focus:outline-none"
              >
                <option value={3}>3</option>
                <option value={5}>5</option>
                <option value={10}>10</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={isLoading || !query.trim()}
              className="px-5 py-3 bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-sky-600/20 flex items-center gap-2 transition-all disabled:opacity-50"
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
              Search Vector Index
            </button>
          </div>
        </div>
      </form>

      {error && (
        <div className="flex items-center gap-2 text-xs text-red-400 bg-red-500/10 p-3 rounded-lg border border-red-500/20">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Results Listing */}
      {searchedQuery && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-400 border-b border-slate-800 pb-2">
            <span>Results for: <strong className="text-sky-400 font-mono">"{searchedQuery}"</strong></span>
            <span>Found {results.length} relevant chunk(s)</span>
          </div>

          {results.length === 0 ? (
            <div className="p-12 text-center text-slate-400 text-sm border border-dashed border-slate-800 rounded-2xl bg-slate-900/40">
              No relevant chunks found for this query in the vector store. Make sure approved documents have been indexed!
            </div>
          ) : (
            <div className="space-y-4">
              {results.map((res, idx) => (
                <div key={res.chunk_id || idx} className="bg-slate-900/90 border border-slate-700/80 p-5 rounded-2xl space-y-3 shadow-xl hover:border-sky-500/40 transition-all">
                  
                  {/* Provenance Header */}
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2 font-semibold text-slate-200">
                      <FileText className="w-4 h-4 text-sky-400" />
                      <span>{res.filename}</span>
                      <span className="text-slate-500">•</span>
                      <span className="text-slate-400">Page {res.page_number}</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold ${
                        res.source_type === 'TABLE'
                          ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                          : 'bg-sky-500/10 text-sky-400 border border-sky-500/20'
                      }`}>
                        {res.source_type}
                      </span>

                      <span className="px-2.5 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded font-mono font-bold text-[11px]">
                        Score: {(res.score * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  {/* Chunk Text Content */}
                  <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800 text-xs font-mono text-slate-200 whitespace-pre-wrap leading-relaxed">
                    {res.text}
                  </div>

                  <div className="text-[11px] text-slate-500 font-mono flex items-center justify-between">
                    <span>Chunk ID: {res.chunk_id}</span>
                    <span>Document ID: {res.document_id}</span>
                  </div>

                </div>
              ))}
            </div>
          )}
        </div>
      )}

    </div>
  );
}
