import React, { useState, useEffect } from 'react';
import {
  runEvaluation,
  fetchEvaluationRuns,
  fetchEvaluationRunDetail
} from '../services/api';

export default function Evaluation() {
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [currentRunDetail, setCurrentRunDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadEvaluationHistory();
  }, []);

  const loadEvaluationHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchEvaluationRuns();
      setRuns(data);
      if (data && data.length > 0) {
        setSelectedRunId(data[0].run_id);
        loadRunDetail(data[0].run_id);
      } else {
        setLoading(false);
      }
    } catch (err) {
      setError(err.message || 'Failed to load evaluation history');
      setLoading(false);
    }
  };

  const loadRunDetail = async (runId) => {
    try {
      setLoading(true);
      const detail = await fetchEvaluationRunDetail(runId);
      setCurrentRunDetail(detail);
    } catch (err) {
      setError(err.message || 'Failed to load run detail');
    } finally {
      setLoading(false);
    }
  };

  const handleRunNewEvaluation = async () => {
    try {
      setEvaluating(true);
      setError(null);
      const newRun = await runEvaluation('phase9_questions');
      await loadEvaluationHistory();
      setSelectedRunId(newRun.run_id);
      await loadRunDetail(newRun.run_id);
    } catch (err) {
      setError(err.message || 'Evaluation benchmark failed');
    } finally {
      setEvaluating(false);
    }
  };

  const handleSelectRun = (e) => {
    const runId = e.target.value;
    setSelectedRunId(runId);
    loadRunDetail(runId);
  };

  const failedQuestions = currentRunDetail?.results?.filter(r => !r.answer_correct) || [];

  return (
    <div style={{ padding: '2rem', maxWidth: '1280px', margin: '0 auto', color: '#f8fafc' }}>
      {/* Header & Benchmark Controls */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '2rem',
        padding: '1.5rem',
        background: 'rgba(15, 23, 42, 0.6)',
        borderRadius: '16px',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        backdropFilter: 'blur(12px)'
      }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.8rem', fontWeight: 700, background: 'linear-gradient(135deg, #60a5fa, #a855f7)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Phase 9: Evaluation & Observability Dashboard
          </h1>
          <p style={{ margin: '0.25rem 0 0', color: '#94a3b8', fontSize: '0.95rem' }}>
            Reproducible accuracy, retrieval quality, citation correctness, grounding, and latency metrics.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          {runs.length > 0 && (
            <select
              value={selectedRunId || ''}
              onChange={handleSelectRun}
              style={{
                background: '#1e293b',
                color: '#f8fafc',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                padding: '0.6rem 1rem',
                borderRadius: '8px',
                fontSize: '0.9rem',
                cursor: 'pointer'
              }}
            >
              {runs.map(r => (
                <option key={r.run_id} value={r.run_id}>
                  Run: {new Date(r.started_at).toLocaleString()} ({(r.accuracy * 100).toFixed(1)}%)
                </option>
              ))}
            </select>
          )}

          <button
            onClick={handleRunNewEvaluation}
            disabled={evaluating}
            style={{
              background: evaluating ? '#475569' : 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
              color: '#fff',
              border: 'none',
              padding: '0.65rem 1.4rem',
              borderRadius: '8px',
              fontWeight: 600,
              cursor: evaluating ? 'not-allowed' : 'pointer',
              boxShadow: '0 4px 14px rgba(59, 130, 246, 0.35)',
              transition: 'all 0.2s ease'
            }}
          >
            {evaluating ? 'Running Benchmark (12 Qs)...' : 'Run New Evaluation'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          padding: '1rem 1.25rem',
          background: 'rgba(239, 68, 68, 0.15)',
          border: '1px solid rgba(239, 68, 68, 0.4)',
          borderRadius: '12px',
          color: '#fca5a5',
          marginBottom: '1.5rem'
        }}>
          ⚠️ {error}
        </div>
      )}

      {loading && !currentRunDetail ? (
        <div style={{ textAlign: 'center', padding: '4rem', color: '#94a3b8' }}>
          Loading evaluation metrics...
        </div>
      ) : !currentRunDetail ? (
        <div style={{
          textAlign: 'center',
          padding: '4rem 2rem',
          background: 'rgba(15, 23, 42, 0.4)',
          borderRadius: '16px',
          border: '1px solid rgba(255, 255, 255, 0.08)'
        }}>
          <h3 style={{ color: '#cbd5e1' }}>No evaluation runs found</h3>
          <p style={{ color: '#64748b' }}>Click "Run New Evaluation" above to evaluate the multimodal RAG engine.</p>
        </div>
      ) : (
        <>
          {/* Main Metrics Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem', marginBottom: '2rem' }}>
            <MetricCard
              label="Overall Accuracy"
              value={`${(currentRunDetail.accuracy * 100).toFixed(1)}%`}
              subtext={`${currentRunDetail.passed_count}/${currentRunDetail.total_questions} passed`}
              color="#3b82f6"
            />
            <MetricCard
              label="Retrieval Recall@5"
              value={`${(currentRunDetail.recall_at_5 * 100).toFixed(1)}%`}
              subtext={`Recall@1: ${(currentRunDetail.recall_at_1 * 100).toFixed(1)}%`}
              color="#10b981"
            />
            <MetricCard
              label="Citation Accuracy"
              value={`${(currentRunDetail.citation_accuracy * 100).toFixed(1)}%`}
              subtext="Provenance verified"
              color="#8b5cf6"
            />
            <MetricCard
              label="Grounding Rate"
              value={`${(currentRunDetail.grounding_rate * 100).toFixed(1)}%`}
              subtext="Supported by evidence"
              color="#06b6d4"
            />
            <MetricCard
              label="Hallucination Rate"
              value={`${(currentRunDetail.hallucination_rate * 100).toFixed(1)}%`}
              subtext="Unsupported claims"
              color={currentRunDetail.hallucination_rate > 0 ? '#ef4444' : '#10b981'}
            />
          </div>

          {/* Section Grid: Modality & Pipeline Latencies */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
            {/* Modality Performance */}
            <div style={{
              background: 'rgba(15, 23, 42, 0.6)',
              padding: '1.5rem',
              borderRadius: '16px',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              backdropFilter: 'blur(12px)'
            }}>
              <h3 style={{ margin: '0 0 1.25rem', fontSize: '1.1rem', color: '#e2e8f0', fontWeight: 600 }}>
                Modality Performance Breakdown
              </h3>
              <ProgressBar label="TEXT" percentage={currentRunDetail.text_accuracy * 100} color="#60a5fa" />
              <ProgressBar label="TABLE" percentage={currentRunDetail.table_accuracy * 100} color="#34d399" />
              <ProgressBar label="OCR" percentage={currentRunDetail.ocr_accuracy * 100} color="#f59e0b" />
              <ProgressBar label="VISUAL" percentage={currentRunDetail.visual_accuracy * 100} color="#a78bfa" />
            </div>

            {/* Pipeline Latency & Stats */}
            <div style={{
              background: 'rgba(15, 23, 42, 0.6)',
              padding: '1.5rem',
              borderRadius: '16px',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              backdropFilter: 'blur(12px)'
            }}>
              <h3 style={{ margin: '0 0 1.25rem', fontSize: '1.1rem', color: '#e2e8f0', fontWeight: 600 }}>
                Pipeline Performance & Confidence
              </h3>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <StatRow label="Average QA Latency" value={`${currentRunDetail.avg_latency_ms} ms`} />
                <StatRow label="Recall@1" value={`${(currentRunDetail.recall_at_1 * 100).toFixed(1)}%`} />
                <StatRow label="Recall@3" value={`${(currentRunDetail.recall_at_3 * 100).toFixed(1)}%`} />
                <StatRow label="Dataset Evaluated" value={currentRunDetail.dataset_name} />
                <StatRow label="Run Timestamp" value={new Date(currentRunDetail.started_at).toLocaleString()} />
              </div>
            </div>
          </div>

          {/* Failed Questions Section */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.6)',
            padding: '1.5rem',
            borderRadius: '16px',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(12px)'
          }}>
            <h3 style={{ margin: '0 0 1rem', fontSize: '1.1rem', color: '#e2e8f0', fontWeight: 600 }}>
              Failed Test Analysis ({failedQuestions.length})
            </h3>

            {failedQuestions.length === 0 ? (
              <div style={{ color: '#34d399', background: 'rgba(52, 211, 153, 0.1)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(52, 211, 153, 0.2)' }}>
                🎉 All test cases passed successfully! Zero failed questions in this evaluation run.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {failedQuestions.map((q) => (
                  <div key={q.id} style={{
                    background: '#1e293b',
                    padding: '1rem 1.25rem',
                    borderRadius: '10px',
                    border: '1px solid rgba(239, 68, 68, 0.3)'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                      <span style={{ fontWeight: 600, color: '#f8fafc' }}>[{q.question_id}] {q.question}</span>
                      <span style={{ fontSize: '0.8rem', background: '#334155', padding: '0.2rem 0.6rem', borderRadius: '4px', color: '#94a3b8' }}>
                        {q.source_type}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.9rem', color: '#cbd5e1', marginBottom: '0.25rem' }}>
                      <strong style={{ color: '#34d399' }}>Expected:</strong> {q.expected_answer}
                    </div>
                    <div style={{ fontSize: '0.9rem', color: '#cbd5e1', marginBottom: '0.25rem' }}>
                      <strong style={{ color: '#fca5a5' }}>Actual:</strong> {q.actual_answer}
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#94a3b8', fontStyle: 'italic', marginTop: '0.4rem' }}>
                      Reason: {q.details?.answer_eval?.reason || 'Evaluation failure'}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function MetricCard({ label, value, subtext, color }) {
  return (
    <div style={{
      background: 'rgba(15, 23, 42, 0.6)',
      padding: '1.25rem',
      borderRadius: '14px',
      border: '1px solid rgba(255, 255, 255, 0.1)',
      backdropFilter: 'blur(12px)',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between'
    }}>
      <div style={{ fontSize: '0.85rem', color: '#94a3b8', fontWeight: 500 }}>{label}</div>
      <div style={{ fontSize: '2rem', fontWeight: 700, color: color, margin: '0.4rem 0 0.2rem' }}>{value}</div>
      <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{subtext}</div>
    </div>
  );
}

function ProgressBar({ label, percentage, color }) {
  return (
    <div style={{ marginBottom: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: '#cbd5e1', marginBottom: '0.35rem' }}>
        <span>{label}</span>
        <span style={{ fontWeight: 600 }}>{percentage.toFixed(1)}%</span>
      </div>
      <div style={{ background: '#334155', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
        <div style={{ background: color, height: '100%', width: `${Math.min(100, Math.max(0, percentage))}%`, transition: 'width 0.4s ease' }} />
      </div>
    </div>
  );
}

function StatRow({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', paddingBottom: '0.6rem' }}>
      <span style={{ color: '#94a3b8', fontSize: '0.9rem' }}>{label}</span>
      <span style={{ color: '#f8fafc', fontWeight: 600, fontSize: '0.9rem' }}>{value}</span>
    </div>
  );
}
