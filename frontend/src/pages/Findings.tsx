import React, { useState, useEffect } from 'react';
import { SeverityIndicator } from '../components/ui/SeverityIndicator';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Search, ChevronRight, X, AlertCircle, CheckCircle, Loader2, Sparkles, Shield, RotateCcw } from 'lucide-react';
import { Finding, FindingExplanation } from '../types/api';
import { findingsApi } from '../api/findings';
import { aiApi } from '../api/ai';
import { useAuth } from '../context/AuthContext';

export function Findings() {
  const { activeWorkspace } = useAuth();
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');
  
  const [aiExplanation, setAiExplanation] = useState<FindingExplanation | null>(null);
  const [loadingAi, setLoadingAi] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  const isViewer = activeWorkspace?.role === 'VIEWER';

  const loadFindings = async () => {
    try {
      setLoading(true);
      const data = await findingsApi.list({
        workspace_id: activeWorkspace?.id,
        status: statusFilter || undefined,
        severity: severityFilter || undefined,
        priority: priorityFilter || undefined,
      });
      setFindings(data);
    } catch (err) {
      console.error('Failed to load findings:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFindings();
  }, [activeWorkspace?.id, statusFilter, severityFilter, priorityFilter]);

  // Reset AI state when selected finding changes
  useEffect(() => {
    setAiExplanation(null);
    setAiError(null);
  }, [selectedFinding]);

  const handleExplainFinding = async () => {
    if (!selectedFinding) return;
    const findingId = selectedFinding.finding_id || (selectedFinding as any).id;
    try {
      setLoadingAi(true);
      setAiError(null);
      const explanation = await aiApi.explainFinding(findingId);
      setAiExplanation(explanation);
    } catch (err: any) {
      console.error('Failed to explain finding:', err);
      setAiError(err.message || 'AI analysis is temporarily unavailable.');
    } finally {
      setLoadingAi(false);
    }
  };

  const updateStatus = async (status: 'OPEN' | 'RESOLVED' | 'IGNORED') => {
    if (!selectedFinding) return;
    const findingId = selectedFinding.finding_id || (selectedFinding as any).id;
    try {
      await findingsApi.updateStatus(findingId, status);
      setSelectedFinding(null);
      loadFindings();
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const filteredFindings = findings.filter(f => 
    (f.title || '').toLowerCase().includes(search.toLowerCase()) ||
    (f.resource_id || '').toLowerCase().includes(search.toLowerCase()) ||
    (f.rule_id || '').toLowerCase().includes(search.toLowerCase()) ||
    (f.service || '').toLowerCase().includes(search.toLowerCase())
  );

  const getPriorityBadgeClass = (priority?: string) => {
    switch (priority) {
      case 'P1':
        return 'bg-rose-500/10 text-rose-600 border-rose-500/20';
      case 'P2':
        return 'bg-amber-500/10 text-amber-600 border-amber-500/20';
      case 'P3':
        return 'bg-blue-500/10 text-blue-600 border-blue-500/20';
      case 'P4':
      default:
        return 'bg-slate-500/10 text-slate-600 border-slate-500/20';
    }
  };

  return (
    <div className="h-full flex flex-col animate-in fade-in duration-300 relative">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-content">Security Findings</h1>
          <p className="text-[14px] text-content-secondary mt-1">
            Deterministic risk evaluation and active vulnerabilities for{' '}
            <span className="font-semibold text-content">{activeWorkspace?.name || 'Workspace'}</span>.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 text-content-muted absolute left-3 top-1/2 -translate-y-1/2" />
            <input 
              type="text" 
              placeholder="Search findings..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full sm:w-60 bg-surface-1 border border-line rounded py-1.5 pl-9 pr-4 text-[13px] text-content-secondary placeholder:text-content-muted focus:outline-none focus:border-accent-9/50 shadow-sm transition-colors"
            />
          </div>
          
          <select 
            className="bg-surface-1 border border-line rounded py-1.5 px-3 text-[13px] text-content focus:outline-none focus:border-accent-9/50"
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            <option value="">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
            <option value="INFO">Info</option>
          </select>

          <select 
            className="bg-surface-1 border border-line rounded py-1.5 px-3 text-[13px] text-content focus:outline-none focus:border-accent-9/50"
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
          >
            <option value="">All Priorities</option>
            <option value="P1">P1 (Immediate)</option>
            <option value="P2">P2 (High)</option>
            <option value="P3">P3 (Medium)</option>
            <option value="P4">P4 (Low)</option>
          </select>
          
          <select 
            className="bg-surface-1 border border-line rounded py-1.5 px-3 text-[13px] text-content focus:outline-none focus:border-accent-9/50"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="OPEN">Open</option>
            <option value="RESOLVED">Resolved</option>
            <option value="IGNORED">Ignored</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <Card className="overflow-hidden flex-1 flex flex-col p-0 bg-surface-1 border border-line">
        {loading ? (
          <div className="flex items-center justify-center p-12">
            <Loader2 className="w-8 h-8 text-accent-9 animate-spin" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-line bg-surface-2/50">
                  <th className="px-6 py-3 text-[12px] font-bold text-content-muted uppercase tracking-wider w-28">Severity</th>
                  <th className="px-6 py-3 text-[12px] font-bold text-content-muted uppercase tracking-wider w-24">Priority</th>
                  <th className="px-6 py-3 text-[12px] font-bold text-content-muted uppercase tracking-wider">Finding</th>
                  <th className="px-6 py-3 text-[12px] font-bold text-content-muted uppercase tracking-wider">Resource / Service</th>
                  <th className="px-6 py-3 text-[12px] font-bold text-content-muted uppercase tracking-wider">Category</th>
                  <th className="px-6 py-3 text-[12px] font-bold text-content-muted uppercase tracking-wider w-24">Risk Score</th>
                  <th className="px-6 py-3 text-[12px] font-bold text-content-muted uppercase tracking-wider w-24">Status</th>
                  <th className="px-6 py-3 w-10"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {filteredFindings.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-6 py-12 text-center text-content-muted">
                      No findings found matching the criteria.
                    </td>
                  </tr>
                )}
                {filteredFindings.map((finding) => (
                  <tr 
                    key={finding.finding_id || (finding as any).id} 
                    onClick={() => setSelectedFinding(finding)}
                    className="hover:bg-surface-3 cursor-pointer transition-colors group"
                  >
                    <td className="px-6 py-3.5">
                      <SeverityIndicator severity={finding.severity as any} />
                    </td>
                    <td className="px-6 py-3.5">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold border ${getPriorityBadgeClass(finding.priority)}`}>
                        {finding.priority || 'P4'}
                      </span>
                    </td>
                    <td className="px-6 py-3.5">
                      <div className="text-[14px] font-bold text-content">{finding.title}</div>
                      <div className="text-[12px] text-content-muted mt-0.5 truncate max-w-md">{finding.rule_id}</div>
                    </td>
                    <td className="px-6 py-3.5 font-mono text-[12px] text-content-secondary">
                      <div className="truncate max-w-[200px]" title={finding.resource_id}>{finding.resource_id}</div>
                      <div className="text-[11px] text-content-muted uppercase">{finding.service || 'aws'}</div>
                    </td>
                    <td className="px-6 py-3.5">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-surface-2 text-content-secondary border border-line uppercase">
                        {finding.category}
                      </span>
                    </td>
                    <td className="px-6 py-3.5 font-mono text-[13px] font-semibold text-content">
                      {finding.risk_score !== undefined && finding.risk_score !== null ? (
                        <span>{finding.risk_score}</span>
                      ) : (
                        <span className="text-content-muted">—</span>
                      )}
                    </td>
                    <td className="px-6 py-3.5">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider border ${
                        finding.status === 'RESOLVED'
                          ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20'
                          : finding.status === 'IGNORED'
                          ? 'bg-slate-500/10 text-slate-500 border-slate-500/20'
                          : 'bg-rose-500/10 text-rose-600 border-rose-500/20'
                      }`}>
                        {finding.status}
                      </span>
                    </td>
                    <td className="px-6 py-3.5 text-right">
                      <ChevronRight className="w-4 h-4 text-content-muted group-hover:text-content-secondary transition-colors" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Drawer Overlay */}
      {selectedFinding && (
        <>
          <div 
            className="fixed inset-0 bg-[var(--scrim)] z-30 transition-opacity backdrop-blur-sm"
            onClick={() => setSelectedFinding(null)}
          />
          
          <div className="fixed inset-y-0 right-0 w-full sm:w-[620px] bg-surface-1 border-l border-line z-40 shadow-elev-4 flex flex-col animate-in slide-in-from-right-full duration-300">
            {/* Drawer Header */}
            <div className="px-6 py-4 border-b border-line flex items-center justify-between sticky top-0 bg-surface-1 z-10">
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-accent-9" />
                <h2 className="text-[16px] font-bold text-content">Finding Details</h2>
              </div>
              <button 
                onClick={() => setSelectedFinding(null)}
                className="p-1.5 hover:bg-surface-3 text-content-muted hover:text-content rounded-md transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6 overflow-y-auto flex-1">
              {/* Title & Severity */}
              <div>
                <div className="flex flex-wrap items-center gap-2 mb-3">
                  <SeverityIndicator severity={selectedFinding.severity as any} showLabel={true} />
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold border ${getPriorityBadgeClass(selectedFinding.priority)}`}>
                    Priority: {selectedFinding.priority || 'P4'}
                  </span>
                  {selectedFinding.risk_score !== undefined && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-surface-2 border border-line text-content">
                      Risk Score: {selectedFinding.risk_score} / 100
                    </span>
                  )}
                  <span className="text-[12px] font-bold uppercase tracking-widest text-content-muted ml-auto">
                    {selectedFinding.status}
                  </span>
                </div>
                <h3 className="text-xl font-bold text-content leading-tight">
                  {selectedFinding.title}
                </h3>
              </div>

              {/* Meta Grid */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-surface-2 rounded-lg border border-line">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-content-muted mb-1">Resource ID</div>
                  <div className="font-mono text-[12px] text-content truncate" title={selectedFinding.resource_id}>
                    {selectedFinding.resource_id}
                  </div>
                </div>
                <div className="p-3 bg-surface-2 rounded-lg border border-line">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-content-muted mb-1">Category / Rule</div>
                  <div className="text-[13px] font-medium text-content truncate" title={selectedFinding.rule_id}>
                    {selectedFinding.category} / {selectedFinding.rule_id}
                  </div>
                </div>
                <div className="p-3 bg-surface-2 rounded-lg border border-line">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-content-muted mb-1">Service & Region</div>
                  <div className="text-[13px] font-medium text-content uppercase">
                    {selectedFinding.service || 'aws'} ({selectedFinding.region || 'global'})
                  </div>
                </div>
                <div className="p-3 bg-surface-2 rounded-lg border border-line">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-content-muted mb-1">Detection Time</div>
                  <div className="text-[12px] font-mono text-content-secondary truncate">
                    {selectedFinding.detected_at || (selectedFinding as any).created_at || 'Recently'}
                  </div>
                </div>
              </div>

              {/* Risk Factors */}
              {(selectedFinding as any).risk_factors && (selectedFinding as any).risk_factors.length > 0 && (
                <div>
                  <h4 className="text-[12px] font-bold uppercase tracking-wider text-content-muted mb-2">
                    Calculated Risk Factors
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {(selectedFinding as any).risk_factors.map((factor: string, i: number) => (
                      <span key={i} className="px-2.5 py-1 text-[11px] font-medium bg-amber-500/10 text-amber-600 border border-amber-500/20 rounded-md">
                        {factor}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Impact & Remediation */}
              <div className="space-y-6">
                <div>
                  <h4 className="text-[13px] font-bold uppercase tracking-wider text-content-muted mb-2 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-severity-critical-ink" />
                    Security Risk & Description
                  </h4>
                  <div className="p-3 bg-severity-critical/10 text-severity-critical-ink border border-severity-critical/20 rounded-lg text-[13px] leading-relaxed whitespace-pre-wrap">
                    {selectedFinding.description || 'No description provided.'}
                  </div>
                </div>
                
                <div>
                  <h4 className="text-[13px] font-bold uppercase tracking-wider text-content-muted mb-2 flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-severity-secure-ink" />
                    Recommended Remediation
                  </h4>
                  <div className="p-3 bg-surface-2 border border-line rounded-lg text-[13px] text-content-secondary leading-relaxed whitespace-pre-wrap">
                    {selectedFinding.recommendation || 'No remediation provided.'}
                  </div>
                </div>

                {/* Evidence */}
                {(selectedFinding as any).evidence && Object.keys((selectedFinding as any).evidence || {}).length > 0 && (
                  <div>
                    <h4 className="text-[13px] font-bold uppercase tracking-wider text-content-muted mb-2">
                      Technical Evidence
                    </h4>
                    <pre className="p-3 bg-surface-2 border border-line rounded-lg text-[11px] font-mono text-content-secondary overflow-x-auto max-h-48">
                      {JSON.stringify((selectedFinding as any).evidence, null, 2)}
                    </pre>
                  </div>
                )}

                {/* AI Explanation Section */}
                <div className="pt-4 border-t border-line">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="text-[13px] font-bold uppercase tracking-wider text-content flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-accent-9" />
                      AI Security Analysis
                    </h4>
                    {!aiExplanation && !loadingAi && (
                      <Button variant="outline" size="sm" onClick={handleExplainFinding} className="text-xs">
                        Explain this finding
                      </Button>
                    )}
                  </div>

                  {loadingAi && (
                    <div className="flex items-center gap-3 p-4 bg-surface-2 rounded-lg border border-line text-content-secondary text-sm">
                      <Loader2 className="w-4 h-4 animate-spin text-accent-9" />
                      Analyzing finding...
                    </div>
                  )}

                  {aiError && (
                    <div className="p-4 bg-severity-critical/10 border border-severity-critical/20 rounded-lg text-sm text-severity-critical-ink">
                      {aiError}
                    </div>
                  )}

                  {aiExplanation && (
                    <div className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-300">
                      <div className="p-4 bg-surface-2 border border-line rounded-lg">
                        <div className="text-sm font-bold text-content mb-1">Why this matters</div>
                        <p className="text-sm text-content-secondary leading-relaxed">{aiExplanation.why_it_matters}</p>
                        
                        {aiExplanation.attack_scenario && (
                          <div className="mt-4">
                            <div className="text-sm font-bold text-content mb-1">Potential Attack Scenario</div>
                            <p className="text-sm text-content-secondary leading-relaxed">{aiExplanation.attack_scenario}</p>
                          </div>
                        )}
                        
                        <div className="mt-4">
                          <div className="text-sm font-bold text-content mb-2">Recommended Actions</div>
                          <ul className="list-disc pl-4 space-y-1">
                            {aiExplanation.recommended_actions.map((action, i) => (
                              <li key={i} className="text-sm text-content-secondary">{action}</li>
                            ))}
                          </ul>
                        </div>
                        
                        {aiExplanation.caveats && aiExplanation.caveats.length > 0 && (
                          <div className="mt-4 pt-4 border-t border-line/50">
                            <div className="text-xs font-bold text-content-muted mb-1 uppercase tracking-wider">Caveats</div>
                            <ul className="list-disc pl-4 space-y-1">
                              {aiExplanation.caveats.map((caveat, i) => (
                                <li key={i} className="text-xs text-content-muted italic">{caveat}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                      <div className="text-xs text-center text-content-muted">
                        AI-generated guidance based on the selected CloudGuard scan. Verify changes against your AWS architecture before implementation.
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Drawer Footer Actions */}
            <div className="px-6 py-4 border-t border-line bg-surface-1 mt-auto sticky bottom-0">
              {isViewer ? (
                <p className="text-xs text-content-muted text-center">
                  Viewer role is read-only and cannot alter finding statuses.
                </p>
              ) : selectedFinding.status === 'OPEN' ? (
                <div className="flex items-center gap-3">
                  <Button className="flex-1" onClick={() => updateStatus('RESOLVED')}>
                    Mark as Resolved
                  </Button>
                  <Button variant="outline" className="flex-1 bg-surface-1" onClick={() => updateStatus('IGNORED')}>
                    Ignore / Suppress
                  </Button>
                </div>
              ) : (
                <div className="flex items-center gap-3">
                  <Button variant="outline" className="flex-1 flex items-center justify-center gap-2" onClick={() => updateStatus('OPEN')}>
                    <RotateCcw className="w-4 h-4" />
                    Reopen Finding
                  </Button>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
