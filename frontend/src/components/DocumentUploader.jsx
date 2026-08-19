import React, { useState } from 'react';
import { UploadCloud, File, FileText, AlertCircle, Loader2, CheckCircle2, AlertTriangle, ShieldCheck, ShieldAlert, Sparkles, Table as TableIcon } from 'lucide-react';
import { uploadDocument, processDocument, extractStructuredData } from '../services/api';

export default function DocumentUploader({ onUploadComplete }) {
  const [file, setFile] = useState(null);
  const [uploadedDoc, setUploadedDoc] = useState(null);
  const [extractionResult, setExtractionResult] = useState(null);
  const [structuredResult, setStructuredResult] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setUploadedDoc(null);
      setExtractionResult(null);
      setStructuredResult(null);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    setError(null);
    try {
      const doc = await uploadDocument(file);
      setUploadedDoc(doc);
    } catch (err) {
      setError(err.message || 'Failed to upload document.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleProcess = async () => {
    if (!uploadedDoc) return;
    setIsProcessing(true);
    setError(null);
    try {
      const result = await processDocument(uploadedDoc.id);
      setExtractionResult(result);
      if (onUploadComplete) onUploadComplete();
    } catch (err) {
      setError(err.message || 'Processing failed.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleStructuredExtract = async () => {
    if (!uploadedDoc) return;
    setIsExtracting(true);
    setError(null);
    try {
      const res = await extractStructuredData(uploadedDoc.id);
      setStructuredResult(res);
    } catch (err) {
      setError(err.message || 'Structured LLM extraction failed.');
    } finally {
      setIsExtracting(false);
    }
  };

  return (
    <div className="bg-slate-800/40 border border-slate-700/60 rounded-2xl p-6 shadow-xl backdrop-blur space-y-6">
      
      {/* Header */}
      <div>
        <h2 className="text-base font-semibold text-slate-200 flex items-center gap-2">
          <UploadCloud className="w-5 h-5 text-sky-400" />
          Multimodal Document Intelligence
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Upload PDFs, scanned documents, reports, and images for automated analysis, summary, and instant vector Q&A.
        </p>
      </div>

      {/* Upload Dropzone */}
      <div className="border-2 border-dashed border-slate-700 hover:border-sky-500/50 rounded-xl p-6 text-center transition-all bg-slate-900/30">
        <input
          type="file"
          id="file-upload"
          className="hidden"
          accept=".pdf,.png,.jpg,.jpeg,.tiff"
          onChange={handleFileChange}
        />
        <label
          htmlFor="file-upload"
          className="cursor-pointer flex flex-col items-center justify-center gap-3"
        >
          <div className="p-3 bg-sky-500/10 rounded-full text-sky-400">
            <File className="w-8 h-8" />
          </div>
          <div>
            <span className="text-sm font-medium text-sky-400 hover:underline">
              Click to select a document
            </span>
            <span className="text-sm text-slate-400"> or drag and drop</span>
          </div>
          <p className="text-xs text-slate-500">
            PDFs, Scanned Documents, Images (PNG, JPG, TIFF)
          </p>
        </label>

        {file && (
          <div className="mt-4 inline-flex items-center gap-3 px-4 py-2 bg-slate-800 rounded-lg text-sm text-slate-200 border border-slate-700">
            <File className="w-4 h-4 text-sky-400" />
            <span className="font-medium">{file.name}</span>
            <span className="text-xs text-slate-400">
              ({(file.size / 1024).toFixed(1)} KB)
            </span>
          </div>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-2 text-xs text-red-400 bg-red-500/10 p-3 rounded-lg border border-red-500/20">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-3">
        {file && !uploadedDoc && (
          <button
            onClick={handleUpload}
            disabled={isUploading}
            className="flex-1 py-2.5 px-4 bg-sky-600 hover:bg-sky-500 text-white font-medium text-sm rounded-xl shadow-lg shadow-sky-600/25 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <UploadCloud className="w-4 h-4" />}
            Upload Document (POST /api/v1/documents/upload)
          </button>
        )}

        {uploadedDoc && (
          <div className="w-full bg-slate-900/60 p-4 rounded-xl border border-slate-700/80 space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">Source Document ID:</span>
              <span className="font-mono text-sky-400 font-semibold">{uploadedDoc.id}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">Filename:</span>
              <span className="text-slate-200">{uploadedDoc.filename}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">Status:</span>
              <span className="px-2 py-0.5 bg-sky-500/10 text-sky-400 border border-sky-500/20 rounded-full font-semibold">
                {uploadedDoc.processing_status}
              </span>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <button
                onClick={handleProcess}
                disabled={isProcessing}
                className="flex-1 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm rounded-xl shadow-lg shadow-indigo-600/25 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Extracting Pages & Tables...
                  </>
                ) : (
                  'Phase 2: Page Ingestion'
                )}
              </button>

              <button
                onClick={handleStructuredExtract}
                disabled={isExtracting || !extractionResult}
                className="flex-1 py-2.5 px-4 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium text-sm rounded-xl shadow-lg shadow-purple-600/25 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                title={!extractionResult ? "Must run page ingestion first" : "Extract & validate with Gemini"}
              >
                {isExtracting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Validating & Scoring...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 text-amber-300" />
                    Phase 4: Extract, Validate & Score Confidence
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Phase 4 Validation & Confidence Display */}
      {structuredResult && (
        <div className="bg-slate-900 border border-slate-700/80 rounded-xl p-5 space-y-5 shadow-2xl">
          
          {/* Status Decision Banner */}
          <div className={`flex items-center justify-between p-4 rounded-xl border ${
            structuredResult.status === 'APPROVED' 
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' 
              : 'bg-amber-500/10 border-amber-500/30 text-amber-300'
          }`}>
            <div className="flex items-center gap-3">
              {structuredResult.status === 'APPROVED' ? (
                <ShieldCheck className="w-7 h-7 text-emerald-400" />
              ) : (
                <ShieldAlert className="w-7 h-7 text-amber-400" />
              )}
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-base tracking-wide uppercase">
                    Status: {structuredResult.status}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded font-mono bg-slate-900/60 border border-slate-700">
                    Threshold: 85%
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  {structuredResult.status === 'APPROVED'
                    ? 'Document passed all deterministic business rules and high confidence threshold.'
                    : 'Document routed to Human Review due to validation rule errors or lower confidence.'}
                </p>
              </div>
            </div>

            <div className="text-right">
              <span className="text-xs text-slate-400 block uppercase">Overall Confidence</span>
              <span className={`text-2xl font-black font-mono ${
                structuredResult.overall_confidence >= 0.85 ? 'text-emerald-400' : 'text-amber-400'
              }`}>
                {(structuredResult.overall_confidence * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          {/* Hard Errors & Warnings Alerts */}
          {structuredResult.hard_errors && structuredResult.hard_errors.length > 0 && (
            <div className="space-y-2 bg-red-500/10 border border-red-500/30 p-3.5 rounded-lg text-xs">
              <span className="font-semibold text-red-400 flex items-center gap-1.5 uppercase">
                <AlertCircle className="w-4 h-4" />
                Hard Errors ({structuredResult.hard_errors.length}) — Forces Human Review
              </span>
              <ul className="list-disc list-inside text-red-300 space-y-1 font-mono">
                {structuredResult.hard_errors.map((err, idx) => (
                  <li key={idx}>
                    <strong className="text-red-200">[{err.field}]</strong> {err.message}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {structuredResult.warnings && structuredResult.warnings.length > 0 && (
            <div className="space-y-2 bg-amber-500/10 border border-amber-500/20 p-3.5 rounded-lg text-xs">
              <span className="font-semibold text-amber-400 flex items-center gap-1.5 uppercase">
                <AlertTriangle className="w-4 h-4" />
                Warnings ({structuredResult.warnings.length})
              </span>
              <ul className="list-disc list-inside text-amber-300 space-y-1 font-mono">
                {structuredResult.warnings.map((warn, idx) => (
                  <li key={idx}>
                    <strong className="text-amber-200">[{warn.field}]</strong> {warn.message}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Field-Level Confidence Breakdown Table */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-sky-400" />
              Field-Level Confidence Breakdown
            </h4>
            <div className="overflow-x-auto rounded-lg border border-slate-800">
              <table className="w-full text-xs text-left text-slate-300">
                <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800">
                  <tr>
                    <th className="px-3 py-2">Field Name</th>
                    <th className="px-3 py-2">Extracted Value</th>
                    <th className="px-3 py-2 text-center">Confidence</th>
                    <th className="px-3 py-2 text-center">Validation Status</th>
                    <th className="px-3 py-2">Formula Weights</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {Object.entries(structuredResult.fields || {}).map(([fName, fRes]) => (
                    <tr key={fName} className={!fRes.is_valid ? 'bg-red-500/5' : ''}>
                      <td className="px-3 py-2 font-sans font-medium text-slate-200">{fName}</td>
                      <td className="px-3 py-2 text-slate-300 max-w-xs truncate">
                        {typeof fRes.value === 'object' ? JSON.stringify(fRes.value) : String(fRes.value ?? 'null')}
                      </td>
                      <td className="px-3 py-2 text-center">
                        <span className={`px-2 py-0.5 rounded font-bold ${
                          fRes.confidence_score >= 0.85 ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                        }`}>
                          {(fRes.confidence_score * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="px-3 py-2 text-center">
                        {fRes.is_valid ? (
                          <span className="text-emerald-400 font-semibold flex items-center justify-center gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Valid
                          </span>
                        ) : (
                          <span className="text-red-400 font-semibold flex items-center justify-center gap-1" title={fRes.validation_error}>
                            <AlertCircle className="w-3.5 h-3.5" /> Error
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-[11px] text-slate-400 font-mono">
                        Src:{fRes.c_source} | Val:{fRes.c_validation} | Fmt:{fRes.c_format} | LLM:{fRes.c_llm}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}

      {/* Phase 2 Page Ingestion Summary */}
      {extractionResult && (
        <div className="bg-slate-900/80 border border-slate-700 rounded-xl p-5 space-y-5">
          <div className="flex items-center justify-between border-b border-slate-700 pb-3">
            <div className="flex items-center gap-2 font-semibold text-slate-200">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              Phase 2: Page Ingestion Summary
            </div>
            <div className="flex items-center gap-2">
              {(extractionResult?.summary?.ocr_pages > 0 || extractionResult?.summary?.native_pages === 0) && (
                <span className="px-3 py-1 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-full text-xs font-bold flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-amber-400" /> SCANNED DOCUMENT DETECTED
                </span>
              )}
              <span className="px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full text-xs font-bold">
                {extractionResult?.summary?.status || 'EXTRACTED'}
              </span>
            </div>
          </div>

          {(extractionResult?.summary?.ocr_pages > 0 || extractionResult?.summary?.native_pages === 0) && (
            <div className="bg-amber-950/20 border border-amber-800/40 rounded-lg p-3.5 space-y-2.5">
              <div className="text-xs font-semibold text-amber-300 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-amber-400" />
                Scanned PDF Mode Active — Tesseract OCR & Gemini Vision Fallback Pipeline
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                <div className="bg-slate-900/90 border border-slate-800 rounded-md p-2 flex items-center justify-between text-slate-300">
                  <span>OCR Processing</span>
                  <span className="text-emerald-400 font-bold flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> Complete</span>
                </div>
                <div className="bg-slate-900/90 border border-slate-800 rounded-md p-2 flex items-center justify-between text-slate-300">
                  <span>Visual Extraction</span>
                  <span className="text-emerald-400 font-bold flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> Complete</span>
                </div>
                <div className="bg-slate-900/90 border border-slate-800 rounded-md p-2 flex items-center justify-between text-slate-300">
                  <span>Structured Extraction</span>
                  <span className="text-emerald-400 font-bold flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> Complete</span>
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-slate-800/80 p-3 rounded-lg border border-slate-700/60 text-center">
              <span className="text-xs text-slate-400 block">Total Pages</span>
              <span className="text-lg font-bold text-slate-100">{extractionResult?.summary?.total_pages ?? extractionResult?.total_pages ?? 0}</span>
            </div>
            <div className="bg-slate-800/80 p-3 rounded-lg border border-slate-700/60 text-center">
              <span className="text-xs text-slate-400 block">Native Text Pages</span>
              <span className="text-lg font-bold text-sky-400">{extractionResult?.summary?.native_pages ?? 0}</span>
            </div>
            <div className="bg-slate-800/80 p-3 rounded-lg border border-slate-700/60 text-center">
              <span className="text-xs text-slate-400 block">Scanned OCR Pages</span>
              <span className="text-lg font-bold text-amber-400">{extractionResult?.summary?.ocr_pages ?? 0}</span>
            </div>
            <div className="bg-slate-800/80 p-3 rounded-lg border border-slate-700/60 text-center">
              <span className="text-xs text-slate-400 block">Tables Found</span>
              <span className="text-lg font-bold text-indigo-400">{extractionResult?.summary?.tables_found ?? extractionResult?.tables?.length ?? 0}</span>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
