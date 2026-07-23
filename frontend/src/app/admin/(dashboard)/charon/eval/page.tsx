'use client';

import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import type { EvalSetResponse, EvalRunResponse, EvalResult } from '@/types';

export default function CharonEvalPage() {
  const [evalSet, setEvalSet] = useState<EvalSetResponse | null>(null);
  const [run, setRun] = useState<EvalRunResponse | null>(null);
  const [loadingSet, setLoadingSet] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');

  const loadSet = useCallback(async () => {
    setLoadingSet(true);
    const r = await api.getEvalSet();
    if (r.error) setError(r.error);
    else if (r.data) setEvalSet(r.data);
    setLoadingSet(false);
  }, []);

  useEffect(() => {
    loadSet();
  }, [loadSet]);

  const handleRun = async () => {
    setRunning(true);
    setError('');
    const r = await api.runEval();
    if (r.error) {
      setError(r.error);
    } else if (r.data) {
      setRun(r.data);
    }
    setRunning(false);
  };

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Charon Q/A Evaluation</h1>
          <p className="text-sm text-[var(--muted)]">
            Run a curated set of customer questions through the live Charon pipeline
            and check whether the answers contain the expected keywords.
          </p>
        </div>
        <button
          onClick={handleRun}
          disabled={running}
          className="px-4 py-2 bg-[var(--primary)] hover:bg-[var(--primary-dark)] text-black font-semibold rounded-lg text-sm transition-colors disabled:opacity-50"
        >
          {running ? 'Running…' : 'Run eval'}
        </button>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-500/40 text-red-300 rounded-lg p-3 text-sm">
          {error}
        </div>
      )}

      {run && (
        <div className="grid grid-cols-3 gap-4">
          <SummaryCard label="Total" value={run.total} />
          <SummaryCard label="Passed" value={run.passed} accent="green" />
          <SummaryCard label="Failed" value={run.failed} accent="red" />
        </div>
      )}

      {run && (
        <div className="rounded-lg border border-[var(--border)] overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-[var(--surface)]">
              <tr>
                <th className="text-left p-3 w-20">Status</th>
                <th className="text-left p-3">Question</th>
                <th className="text-left p-3">Answer excerpt</th>
                <th className="text-left p-3 w-20">Latency</th>
              </tr>
            </thead>
            <tbody>
              {run.results.map((r) => (
                <tr key={r.id} className="border-t border-[var(--border)] align-top">
                  <td className="p-3">
                    {r.passed ? (
                      <span className="text-green-400 font-semibold">PASS</span>
                    ) : (
                      <span className="text-red-400 font-semibold">FAIL</span>
                    )}
                  </td>
                  <td className="p-3">
                    <div className="font-medium">{r.question}</div>
                    {r.missing_keywords.length > 0 && (
                      <div className="text-xs text-red-400 mt-1">
                        Missing: {r.missing_keywords.join(', ')}
                      </div>
                    )}
                    {r.matched_scenario && (
                      <div className="text-xs text-blue-400 mt-1">
                        scenario: {r.matched_scenario}
                      </div>
                    )}
                  </td>
                  <td className="p-3 text-[var(--muted)]">{r.answer.slice(0, 200)}{r.answer.length > 200 ? '…' : ''}</td>
                  <td className="p-3 text-[var(--muted)]">{r.latency_ms}ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!run && evalSet && (
        <div className="rounded-lg border border-[var(--border)] p-4">
          <h2 className="font-semibold mb-2">{evalSet.name}</h2>
          <p className="text-sm text-[var(--muted)] mb-3">{evalSet.description}</p>
          <p className="text-sm">
            {evalSet.questions.length} questions. Click <strong>Run eval</strong> to grade
            Charon against this set.
          </p>
        </div>
      )}

      {loadingSet && <div className="text-[var(--muted)] text-sm">Loading…</div>}
    </div>
  );
}

function SummaryCard({ label, value, accent }: { label: string; value: number; accent?: 'green' | 'red' }) {
  const color =
    accent === 'green' ? 'text-green-400' :
    accent === 'red' ? 'text-red-400' : 'text-[var(--foreground)]';
  return (
    <div className="rounded-lg border border-[var(--border)] p-4">
      <div className="text-xs uppercase tracking-wider text-[var(--muted)]">{label}</div>
      <div className={`text-3xl font-bold mt-1 ${color}`}>{value}</div>
    </div>
  );
}