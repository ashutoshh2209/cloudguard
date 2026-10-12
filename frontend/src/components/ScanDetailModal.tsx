import React, { useState, useEffect } from 'react';
import { X, Calendar, Shield, AlertCircle, CheckCircle2, XCircle, AlertTriangle, Layers, Clock, ExternalLink, Loader2, Sparkles } from 'lucide-react';
import { Button } from './ui/Button';
import { Card } from './ui/Card';
import { SeverityIndicator } from './ui/SeverityIndicator';
import { scansApi, ScanDetailResponse } from '../api/scans';
import { aiApi } from '../api/ai';
import { ScanAISummary } from '../types/api';

interface ScanDetailModalProps {
  scanId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export function ScanDetailModal({ scanId, isOpen, onClose }: ScanDetailModalProps) {
  const [scan, setScan] = useState<ScanDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'checks' | 'findings'>('overview');
  const [aiSummary, setAiSummary] = useState<ScanAISummary | null>(null);
  const [loadingAiSummary, setLoadingAiSummary] = useState(false);

  useEffect(() => {
    if (isOpen && scanId) {
      loadDetail(scanId);
      setAiSummary(null);
    } else {
      setScan(null);
      setError(null);
      setAiSummary(null);
    }
  }, [isOpen, scanId]);

  const loadDetail = async (id: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await scansApi.getScan(id);
      setScan(data);
    } catch (err: any) {
      console.error('Failed to load scan detail:', err);
      setError(err?.message || 'Failed to load scan details');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadAiSummary = async () => {
    if (!scan?.id) return;
    try {
      setLoadingAiSummary(true);
      const res = await aiApi.summarizeScan(scan.id);
      setAiSummary(res);
    } catch (err: any) {
      console.error('Failed to load AI summary:', err);
    } finally {
      setLoadingAiSummary(false);
    }
  };

  if (!isOpen) return null;

  const passed = scan?.summary?.checks_passed ?? Math.max(0, (scan?.summary?.checks_completed || 0) - (scan?.summary?.checks_failed || 0));
  const failed = scan?.summary?.checks_failed || 0;
  const errored = scan?.summary?.checks_errored || 0;
  const attempted = scan?.summary?.checks_attempted || 0;

  let durationStr = '—';
  if (scan?.started_at && scan?.completed_at) {
    const diffSec = Math.max(0, Math.round((new Date(scan.completed_at).getTime() - new Date(scan.started_at).getTime()) / 1000));
    durationStr = diffSec >= 60 ? `${Math.floor(diffSec / 60)}m ${diffSec % 60}s` : `${diffSec}s`;
  }

  return (
    <>
      <div 
        className="fixed inset-0 bg-[var(--scrim)] z-40 transition-opacity backdrop-blur-sm"
        onClick={onClose}
      />

      <div className="fixed inset-y-0 right-0 w-full sm:w-[680px] bg-surface-1 border-l border-line z-50 shadow-elev-4 flex flex-col animate-in slide-in-from-right-full duration-300">
        {/* Header */}
        <div className="px-6 py-4 border-b border-line flex items-center justify-between sticky top-0 bg-surface-1 z-10">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-accent-9" />
            <h2 className="text-[16px] font-bold text-content">Scan Assessment Details</h2>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 hover:bg-surface-3 text-content-muted hover:text-content rounded-md transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {loading ? (
          <div className="flex-1 flex flex-col items-center justify-center p-12">
            <Loader2 className="w-8 h-8 text-accent-9 animate-spin mb-2" />
            <p className="text-sm text-content-muted">Loading scan telemetry...</p>
          </div>
        ) : error ? (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
            <AlertTriangle className="w-12 h-12 text-rose-500 mb-3" />
            <h3 className="text-lg font-bold text-content mb-1">Scan not found or unauthorized</h3>
            <p className="text-sm text-content-secondary max-w-sm mb-6">{error}</p>
            <Button variant="outline" onClick={onClose}>Close</Button>
          </div>
        ) : scan ? (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Nav Tabs */}
            <div className="px-6 border-b border-line flex gap-6 bg-surface-2/40 text-sm">
              <button
                className={`py-3 font-semibold border-b-2 transition-colors ${
                  activeTab === 'overview'
                    ? 'border-accent-9 text-content'
                    : 'border-transparent text-content-muted hover:text-content'
                }`}
                onClick={() => setActiveTab('overview')}
              >
                Overview & Metrics
              </button>
              <button
                className={`py-3 font-semibold border-b-2 transition-colors ${
                  activeTab === 'checks'
                    ? 'border-accent-9 text-content'
                    : 'border-transparent text-content-muted hover:text-content'
                }`}
                onClick={() => setActiveTab('checks')}
              >
                Checks ({scan.check_results?.length || 0})
              </button>
              <button
                className={`py-3 font-semibold border-b-2 transition-colors ${
                  activeTab === 'findings'
                    ? 'border-accent-9 text-content'
                    : 'border-transparent text-content-muted hover:text-content'
                }`}
                onClick={() => setActiveTab('findings')}
              >
                Findings ({scan.findings?.length || 0})
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {activeTab === 'overview' && (
                <>
                  {/* Top Score Banner */}
                  <div className="p-5 bg-surface-2 rounded-xl border border-line flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold uppercase tracking-wider text-content-muted">Security Score</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          scan.status === 'COMPLETED'
                            ? 'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20'
                            : scan.status === 'PARTIAL'
                            ? 'bg-amber-500/10 text-amber-600 border border-amber-500/20'
                            : 'bg-rose-500/10 text-rose-600 border border-rose-500/20'
                        }`}>
                          {scan.status}
                        </span>
                      </div>
                      <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-extrabold text-content font-mono">
                          {scan.security_score !== null && scan.security_score !== undefined ? scan.security_score : 'N/A'}
                        </span>
                        <span className="text-sm font-semibold text-content-muted">/ 100</span>
                        {scan.security_rating && (
                          <span className="text-sm font-bold text-accent-10 ml-2">
                            ({scan.security_rating})
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex gap-6 text-sm">
                      <div>
                        <div className="text-[11px] font-bold uppercase tracking-wider text-content-muted">Coverage</div>
                        <div className="font-mono font-bold text-content mt-0.5">{scan.coverage_percentage}%</div>
                      </div>
                      <div>
                        <div className="text-[11px] font-bold uppercase tracking-wider text-content-muted">Duration</div>
                        <div className="font-mono font-bold text-content mt-0.5">{durationStr}</div>
                      </div>
                    </div>
                  </div>

                  {/* AI Summary Card */}
                  <div className="p-4 bg-surface-2 rounded-xl border border-line">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-accent-9" />
                        <span className="text-xs font-bold uppercase tracking-wider text-content">AI Security Summary</span>
                      </div>
                      {!aiSummary && (
                        <Button 
                          variant="outline" 
                          size="sm" 
                          onClick={handleLoadAiSummary}
                          disabled={loadingAiSummary}
                          className="text-xs"
                        >
                          {loadingAiSummary ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Sparkles className="w-3 h-3 mr-1" />}
                          Analyze With Copilot
                        </Button>
                      )}
                    </div>
                    {aiSummary ? (
                      <div className="text-xs space-y-2 mt-2">
                        <p className="text-content-secondary leading-relaxed">{aiSummary.summary}</p>
                        {aiSummary.recommended_actions && aiSummary.recommended_actions.length > 0 && (
                          <div className="mt-2 pt-2 border-t border-line">
                            <span className="font-bold text-content block mb-1">Recommended Actions:</span>
                            <ul className="list-disc list-inside space-y-1 text-content-secondary">
                              {aiSummary.recommended_actions.map((act, i) => (
                                <li key={i}>{act}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-xs text-content-muted">
                        Generate an automated AI executive summary and prioritized remediation sequence for this scan.
                      </p>
                    )}
                  </div>

                  {/* Metadata Grid */}
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="p-3 bg-surface-2 rounded-lg border border-line">
                      <span className="text-content-muted font-bold uppercase tracking-wider block mb-1">Scan ID</span>
                      <span className="font-mono text-content select-all break-all">{scan.id}</span>
                    </div>
                    <div className="p-3 bg-surface-2 rounded-lg border border-line">
                      <span className="text-content-muted font-bold uppercase tracking-wider block mb-1">AWS Account</span>
                      <span className="font-mono text-content select-all">{scan.account_id || scan.aws_connection_id || 'Primary'}</span>
                    </div>
                    <div className="p-3 bg-surface-2 rounded-lg border border-line">
                      <span className="text-content-muted font-bold uppercase tracking-wider block mb-1">Started At</span>
                      <span className="font-mono text-content-secondary">
                        {scan.started_at ? new Date(scan.started_at).toLocaleString() : '—'}
                      </span>
                    </div>
                    <div className="p-3 bg-surface-2 rounded-lg border border-line">
                      <span className="text-content-muted font-bold uppercase tracking-wider block mb-1">Completed At</span>
                      <span className="font-mono text-content-secondary">
                        {scan.completed_at ? new Date(scan.completed_at).toLocaleString() : 'In Progress'}
                      </span>
                    </div>
                  </div>

                  {/* Checks Breakdown */}
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-content-muted mb-2">Deterministic Checks</h4>
                    <div className="grid grid-cols-4 gap-2 text-center">
                      <div className="p-3 bg-surface-2 rounded-lg border border-line">
                        <div className="text-[11px] text-content-muted">Attempted</div>
                        <div className="text-lg font-bold font-mono text-content mt-1">{attempted}</div>
                      </div>
                      <div className="p-3 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                        <div className="text-[11px] text-emerald-600 font-semibold">Passed</div>
                        <div className="text-lg font-bold font-mono text-emerald-600 mt-1">{passed}</div>
                      </div>
                      <div className="p-3 bg-rose-500/10 rounded-lg border border-rose-500/20">
                        <div className="text-[11px] text-rose-600 font-semibold">Failed</div>
                        <div className="text-lg font-bold font-mono text-rose-600 mt-1">{failed}</div>
                      </div>
                      <div className="p-3 bg-amber-500/10 rounded-lg border border-amber-500/20">
                        <div className="text-[11px] text-amber-600 font-semibold">Errors</div>
                        <div className="text-lg font-bold font-mono text-amber-600 mt-1">{errored}</div>
                      </div>
                    </div>
                  </div>

                  {/* Findings Severity Summary */}
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-content-muted mb-2">Findings Severity Distribution</h4>
                    <div className="grid grid-cols-5 gap-2 text-center text-xs">
                      <div className="p-2.5 bg-red-500/10 text-red-600 border border-red-500/20 rounded-lg">
                        <div className="text-[10px] font-bold">CRIT</div>
                        <div className="text-base font-bold font-mono mt-0.5">{scan.summary?.critical || 0}</div>
                      </div>
                      <div className="p-2.5 bg-orange-500/10 text-orange-600 border border-orange-500/20 rounded-lg">
                        <div className="text-[10px] font-bold">HIGH</div>
                        <div className="text-base font-bold font-mono mt-0.5">{scan.summary?.high || 0}</div>
                      </div>
                      <div className="p-2.5 bg-amber-500/10 text-amber-600 border border-amber-500/20 rounded-lg">
                        <div className="text-[10px] font-bold">MED</div>
                        <div className="text-base font-bold font-mono mt-0.5">{scan.summary?.medium || 0}</div>
                      </div>
                      <div className="p-2.5 bg-blue-500/10 text-blue-600 border border-blue-500/20 rounded-lg">
                        <div className="text-[10px] font-bold">LOW</div>
                        <div className="text-base font-bold font-mono mt-0.5">{scan.summary?.low || 0}</div>
                      </div>
                      <div className="p-2.5 bg-emerald-500/10 text-emerald-600 border border-emerald-500/20 rounded-lg">
                        <div className="text-[10px] font-bold">INFO</div>
                        <div className="text-base font-bold font-mono mt-0.5">{scan.summary?.info || 0}</div>
                      </div>
                    </div>
                  </div>

                  {/* Category Scores */}
                  {scan.category_scores && Object.keys(scan.category_scores).length > 0 && (
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider text-content-muted mb-2">Category Scores</h4>
                      <div className="space-y-2">
                        {Object.entries(scan.category_scores).map(([cat, val]: any) => (
                          <div key={cat} className="flex items-center justify-between p-2.5 bg-surface-2 rounded-lg border border-line text-xs">
                            <span className="font-bold text-content">{cat}</span>
                            <div className="flex items-center gap-3">
                              <span className="text-content-muted">{val.findings || 0} findings</span>
                              <span className="font-mono font-bold text-accent-10">{val.score} / 100</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}

              {activeTab === 'checks' && (
                <div className="space-y-3">
                  {(!scan.check_results || scan.check_results.length === 0) ? (
                    <p className="text-sm text-content-muted text-center py-8">No checks recorded for this scan.</p>
                  ) : (
                    scan.check_results.map((cr) => (
                      <div key={cr.id} className="p-3 bg-surface-2 rounded-lg border border-line text-xs space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-content">{cr.rule_id}</span>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            cr.status === 'PASS'
                              ? 'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20'
                              : cr.status === 'FAIL'
                              ? 'bg-rose-500/10 text-rose-600 border border-rose-500/20'
                              : cr.status === 'ERROR'
                              ? 'bg-amber-500/10 text-amber-600 border border-amber-500/20'
                              : 'bg-slate-500/10 text-slate-500 border border-slate-500/20'
                          }`}>
                            {cr.status}
                          </span>
                        </div>
                        <div className="font-mono text-content-muted truncate">{cr.resource_id}</div>
                        {cr.message && <div className="text-content-secondary">{cr.message}</div>}
                      </div>
                    ))
                  )}
                </div>
              )}

              {activeTab === 'findings' && (
                <div className="space-y-3">
                  {(!scan.findings || scan.findings.length === 0) ? (
                    <p className="text-sm text-content-muted text-center py-8">No vulnerabilities identified in this scan.</p>
                  ) : (
                    scan.findings.map((f: any) => (
                      <div key={f.id || f.finding_id} className="p-3 bg-surface-2 rounded-lg border border-line text-xs space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-content">{f.title}</span>
                          <SeverityIndicator severity={f.severity as any} />
                        </div>
                        <div className="flex items-center gap-2 font-mono text-content-muted">
                          <span className="truncate max-w-xs">{f.resource_id}</span>
                          <span>•</span>
                          <span>Score: {f.risk_score}</span>
                          <span>•</span>
                          <span>{f.status}</span>
                        </div>
                        {f.description && <div className="text-content-secondary line-clamp-2">{f.description}</div>}
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-line bg-surface-1 flex items-center justify-between sticky bottom-0">
              <Button
                variant="outline"
                size="sm"
                className="flex items-center gap-1.5"
                onClick={() => window.location.href = `/app/findings?scan_id=${scan.id}`}
              >
                <ExternalLink className="w-3.5 h-3.5" />
                View in Findings Explorer
              </Button>
              <Button variant="ghost" size="sm" onClick={onClose}>
                Close
              </Button>
            </div>
          </div>
        ) : null}
      </div>
    </>
  );
}
