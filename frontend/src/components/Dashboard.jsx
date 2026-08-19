import React, { useState } from 'react';
import { UploadCloud, File, CheckCircle2, AlertTriangle, AlertCircle, Loader2, Sparkles, ChevronDown, ChevronUp, ArrowRight, ShieldCheck } from 'lucide-react';
import { uploadDocument, processDocument, extractStructuredData, indexDocument } from '../services/api';
import DashboardStats from './DashboardStats';

export default function Dashboard({ onNavigate, onShowToast, onRefreshData }) {
  const [file, setFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [progressPercent, setProgressPercent] = useState(0);
  const [statusMessage, setStatusMessage] = useState('');
  const [resultDoc, setResultDoc] = useState(null);
  const [extractedData, setExtractedData] = useState(null);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const [technicalLogs, setTechnicalLogs] = useState([]);
  const [error, setError] = useState(null);

  const stepsList = [
    { label: 'Upload complete', detail: 'File received and verified.' },
    { label: 'Reading pages', detail: 'Extracting page layouts and native text.' },
    { label: 'Detecting document type', detail: 'Checking text layer vs scanned image OCR.' },
    { label: 'Extracting information', detail: 'Running Gemini multimodal extraction.' },
    { label: 'Validating information', detail: 'Scoring confidence and checking rules.' },
    { label: 'Preparing for questions', detail: 'Building vector index for grounded RAG.' },
  ];

  const appendLog = (msg) => {
    setTechnicalLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
  };

  const handleFileDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const selected = e.dataTransfer.files[0];
      setFile(selected);
      startAutoProcessing(selected);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      startAutoProcessing(selected);
    }
  };

  const startAutoProcessing = async (selectedFile) => {
    setIsProcessing(true);
    setError(null);
    setResultDoc(null);
    setExtractedData(null);
    setTechnicalLogs([]);
    setCurrentStep(1);
    setProgressPercent(15);
    setStatusMessage('Uploading document...');
    appendLog(`Starting upload for file: ${selectedFile.name}`);

    try {
      // Step 1: Upload Document
      const doc = await uploadDocument(selectedFile);
      setResultDoc(doc);
      appendLog(`Document uploaded successfully. ID: ${doc.id}`);
      if (onShowToast) onShowToast({ type: 'success', message: 'Document upload complete.' });

      // Step 2: Page Ingestion & OCR
      setCurrentStep(2);
      setProgressPercent(35);
      setStatusMessage('Reading pages & running OCR fallback if scanned...');
      appendLog('Triggering page ingestion and OCR detection...');
      const ingestRes = await processDocument(doc.id);
      const isScanned = ingestRes?.summary?.ocr_pages > 0 || ingestRes?.summary?.native_pages === 0;
      appendLog(`Page ingestion complete. Total pages: ${ingestRes?.summary?.total_pages}, Scanned OCR: ${isScanned}`);

      // Step 3 & 4: Structured LLM Extraction & Validation
      setCurrentStep(3);
      setProgressPercent(60);
      setStatusMessage(isScanned ? 'Scanned document detected — Reading using OCR & Gemini Vision...' : 'Extracting key fields & financial summary...');
      appendLog('Triggering Gemini structured extraction and business rule validation...');
      const structRes = await extractStructuredData(doc.id);
      setExtractedData(structRes);
      appendLog(`Extraction complete. Status: ${structRes.status}, Confidence: ${(structRes.overall_confidence * 100).toFixed(1)}%`);

      // Step 5 & 6: Vector Indexing (if approved/ready)
      setCurrentStep(5);
      setProgressPercent(85);
      setStatusMessage('Validating information & indexing for Q&A...');

      if (structRes.status === 'APPROVED' || structRes.status === 'INDEXED') {
        appendLog('Document approved. Upserting chunks into ChromaDB vector store...');
        await indexDocument(doc.id).catch((err) => appendLog(`Auto-index warning: ${err.message}`));
      }

      setCurrentStep(6);
      setProgressPercent(100);
      setStatusMessage(structRes.status === 'APPROVED' ? 'Document ready!' : 'Document requires review');
      appendLog(`Pipeline finished cleanly. Final status: ${structRes.status}`);

      if (onShowToast) {
        onShowToast({
          type: structRes.status === 'APPROVED' ? 'success' : 'info',
          message: structRes.status === 'APPROVED' ? 'Document is ready to ask questions.' : 'Document requires review verification.'
        });
      }
      if (onRefreshData) onRefreshData();

    } catch (err) {
      setError(err.message || 'We couldn\'t finish processing this document.');
      appendLog(`Pipeline error: ${err.message}`);
      if (onShowToast) onShowToast({ type: 'error', message: 'Document processing failed.' });
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-8">
      
      {/* Dashboard Top Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/60 p-6 rounded-2xl border border-slate-800 shadow-xl backdrop-blur">
        <div>
          <h1 className="text-2xl font-black text-slate-100 flex items-center gap-2.5">
            <Sparkles className="w-6 h-6 text-sky-400" />
            DocuMind AI
          </h1>
          <p className="text-xs font-semibold text-sky-400 uppercase tracking-widest mt-0.5">
            Multimodal Document Intelligence
          </p>
          <p className="text-xs text-slate-400 mt-1.5 max-w-xl">
            Upload, analyze, summarize, and ask questions about your documents.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => document.getElementById('dash-file-upload')?.click()}
            className="px-5 py-2.5 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-sky-500/25 transition-all flex items-center gap-2"
          >
            <UploadCloud className="w-4 h-4" />
            + Upload Documents
          </button>
        </div>
      </div>



      {/* Drag and Drop Upload Area */}
      {!isProcessing && !extractedData && (
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleFileDrop}
          className="border-2 border-dashed border-slate-700/80 hover:border-sky-500/60 rounded-2xl p-8 text-center transition-all bg-slate-900/40 shadow-xl space-y-4 cursor-pointer"
          onClick={() => document.getElementById('dash-file-upload')?.click()}
        >
          <input
            type="file"
            id="dash-file-upload"
            className="hidden"
            accept=".pdf,.png,.jpg,.jpeg,.tiff"
            onChange={handleFileSelect}
          />
          <div className="p-4 bg-sky-500/10 rounded-2xl text-sky-400 w-16 h-16 mx-auto flex items-center justify-center border border-sky-500/20">
            <UploadCloud className="w-8 h-8" />
          </div>

          <div>
            <h3 className="text-base font-bold text-slate-200">Upload your documents</h3>
            <p className="text-xs text-slate-400 mt-1">
              Drag and drop PDF files here or <span className="text-sky-400 font-semibold hover:underline">Browse Files</span>
            </p>
          </div>

          <div className="pt-2 border-t border-slate-800/80 max-w-md mx-auto">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">Supports:</span>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 text-xs text-slate-300 font-medium">
              <span className="flex items-center gap-1.5 justify-center"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Text PDFs</span>
              <span className="flex items-center gap-1.5 justify-center"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Scanned PDFs</span>
              <span className="flex items-center gap-1.5 justify-center"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Tables</span>
              <span className="flex items-center gap-1.5 justify-center"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Images</span>
              <span className="flex items-center gap-1.5 justify-center"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Reports</span>
              <span className="flex items-center gap-1.5 justify-center"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Invoices</span>
            </div>
          </div>
        </div>
      )}

      {/* Automatic Pipeline Processing State Screen */}
      {isProcessing && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-sky-500/10 rounded-xl text-sky-400 border border-sky-500/20">
                <Loader2 className="w-6 h-6 animate-spin text-sky-400" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-100">Understanding your document</h3>
                <span className="text-xs font-mono text-slate-400">{file?.name}</span>
              </div>
            </div>
            <span className="text-xs font-bold font-mono text-sky-400 bg-slate-950 px-3 py-1 rounded-lg border border-slate-800">
              {progressPercent}%
            </span>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-slate-950 h-2.5 rounded-full overflow-hidden border border-slate-800">
            <div
              className="h-full bg-gradient-to-r from-sky-500 to-indigo-600 transition-all duration-500 rounded-full"
              style={{ width: `${progressPercent}%` }}
            ></div>
          </div>

          {/* Progress Steps Checklist */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs pt-2">
            {stepsList.map((step, idx) => {
              const isDone = currentStep > idx + 1 || (currentStep === 6 && progressPercent === 100);
              const isCurrent = currentStep === idx + 1 && progressPercent < 100;
              return (
                <div
                  key={idx}
                  className={`p-3 rounded-xl border flex items-start gap-2.5 transition-all ${
                    isDone
                      ? 'bg-emerald-950/20 border-emerald-800/40 text-emerald-300'
                      : isCurrent
                      ? 'bg-sky-950/30 border-sky-600/50 text-sky-200'
                      : 'bg-slate-950/40 border-slate-800/60 text-slate-500'
                  }`}
                >
                  {isDone ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                  ) : isCurrent ? (
                    <Loader2 className="w-4 h-4 text-sky-400 animate-spin flex-shrink-0 mt-0.5" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-slate-700 flex-shrink-0 mt-0.5" />
                  )}
                  <div>
                    <span className="font-semibold block">{step.label}</span>
                    <span className="text-[10px] text-slate-400 font-mono">{step.detail}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Optional Expandable Technical Details Drawer */}
          <div className="pt-2 border-t border-slate-800">
            <button
              onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
              className="text-xs text-slate-400 hover:text-slate-200 font-medium flex items-center gap-1.5 transition-colors"
            >
              {showTechnicalDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              {showTechnicalDetails ? 'Hide technical details' : 'View processing details'}
            </button>

            {showTechnicalDetails && (
              <div className="mt-3 bg-slate-950 border border-slate-800 rounded-xl p-4 font-mono text-[11px] text-sky-300 space-y-1 max-h-40 overflow-y-auto">
                {technicalLogs.map((log, lIdx) => (
                  <div key={lIdx}>{log}</div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Completion Card State */}
      {extractedData && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-5">
          <div className="p-4 rounded-xl border flex flex-col md:flex-row md:items-center justify-between gap-4 bg-emerald-500/10 border-emerald-500/30 text-emerald-300">
            <div className="flex items-center gap-3">
              <ShieldCheck className="w-8 h-8 text-emerald-400 flex-shrink-0" />
              <div>
                <h4 className="font-bold text-sm uppercase tracking-wide text-emerald-200">
                  ✓ Document Processed & Ready for Q&A
                </h4>
                <p className="text-xs text-slate-300 mt-0.5">
                  Your document has been analyzed, summarized, and indexed into ChromaDB.
                </p>
              </div>
            </div>

            <button
              onClick={() => onNavigate('qa')}
              className="px-5 py-2.5 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white rounded-xl text-xs font-bold flex items-center justify-center gap-2 shadow-lg shadow-sky-500/25"
            >
              Ask Questions About This Document <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          {/* Document Summary & Key Topics Card */}
          {extractedData.data && (
            <div className="bg-slate-950/60 p-5 rounded-xl border border-slate-800 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-slate-400 block text-[11px]">Document Title:</span>
                  <span className="font-bold text-slate-100 text-sm">{extractedData.data.document_title || resultDoc?.filename || 'Untitled Document'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Document Category / Type:</span>
                  <span className="font-semibold text-sky-400">{extractedData.data.document_type || 'General Document'}</span>
                </div>
              </div>

              {extractedData.data.summary && (
                <div>
                  <span className="text-slate-400 block text-[11px] mb-1 font-semibold uppercase tracking-wider">Executive Summary:</span>
                  <p className="text-xs text-slate-300 bg-slate-900/80 p-3.5 rounded-lg border border-slate-800 leading-relaxed">
                    {extractedData.data.summary}
                  </p>
                </div>
              )}

              {extractedData.data.key_topics && extractedData.data.key_topics.length > 0 && (
                <div>
                  <span className="text-slate-400 block text-[11px] mb-1.5 font-semibold uppercase tracking-wider">Key Topics:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {extractedData.data.key_topics.map((topic, tIdx) => (
                      <span key={tIdx} className="px-2.5 py-1 bg-sky-500/10 text-sky-300 border border-sky-500/20 rounded-md text-[11px] font-medium">
                        {topic}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-800">
            <button
              onClick={() => {
                setExtractedData(null);
                setResultDoc(null);
                setFile(null);
              }}
              className="text-sky-400 hover:underline font-semibold"
            >
              + Upload another document
            </button>

            <button
              onClick={() => onNavigate('documents')}
              className="text-slate-400 hover:text-slate-200 hover:underline"
            >
              View all documents →
            </button>
          </div>
        </div>
      )}

      {/* Friendly Error State */}
      {error && (
        <div className="bg-red-950/30 border border-red-800/60 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center gap-3 text-red-400">
            <AlertCircle className="w-6 h-6 flex-shrink-0" />
            <div>
              <h4 className="font-bold text-sm text-slate-100">Something went wrong</h4>
              <p className="text-xs text-red-300 mt-0.5 font-medium">{error}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {file && (
              <button
                onClick={() => startAutoProcessing(file)}
                className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white text-xs font-semibold rounded-xl shadow-md"
              >
                Try Again
              </button>
            )}
            <button
              onClick={() => {
                setError(null);
                setFile(null);
              }}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
