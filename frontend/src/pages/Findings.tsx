import React, { useState, useEffect } from 'react';
import { SeverityIndicator } from '../components/ui/SeverityIndicator';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Search, Filter, Download, ChevronRight, X, AlertCircle, CheckCircle, Loader2, Sparkles } from 'lucide-react';
import { Finding, FindingExplanation } from '../types/api';
import { fetchApi } from '../api/client';
import { aiApi } from '../api/ai';

export function Findings() {
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  
  const [aiExplanation, setAiExplanation] = useState<FindingExplanation | null>(null);
  const [loadingAi, setLoadingAi] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  const loadFindings = async () => {
    try {
      setLoading(true);
      const queryParams = new URLSearchParams();
      if (statusFilter) queryParams.append('status', statusFilter);
      if (severityFilter) queryParams.append('severity', severityFilter);
      
      const data = await fetchApi<Finding[]>(`/scans/findings/?${queryParams.toString()}`);
      setFindings(data);
    } catch (err) {
      console.error('Failed to load findings:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFindings();
  }, [statusFilter, severityFilter]);

  // Reset AI state when selected finding changes
  useEffect(() => {
    setAiExplanation(null);
    setAiError(null);
  }, [selectedFinding]);

  const handleExplainFinding = async () => {
    if (!selectedFinding) return;
    try {
      setLoadingAi(true);
      setAiError(null);
      const explanation = await aiApi.explainFinding(selectedFinding.finding_id);
      setAiExplanation(explanation);
    } catch (err: any) {
      console.error('Failed to explain finding:', err);
      setAiError(err.message || 'AI analysis is temporarily unavailable.');
    } finally {
      setLoadingAi(false);
    }
  };

  const updateStatus = async (status: 'RESOLVED' | 'IGNORED') => {
    if (!selectedFinding) return;
    try {
      await fetchApi(`/scans/findings/${selectedFinding.finding_id}?status=${status}`, {
        method: 'PATCH'
      });
      setSelectedFinding(null);
      loadFindings();
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const filteredFindings = findings.filter(f => 
    f.title.toLowerCase().includes(search.toLowerCase()) ||
    f.resource_id.toLowerCase().includes(search.toLowerCase()) ||
    f.rule_id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="h-full flex flex-col animate-in fade-in duration-300 relative">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-content">Security Findings</h1>
          <p className="text-[14px] text-content-secondary mt-1">Review and manage identified security vulnerabilities across your infrastructure.</p>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 text-content-muted absolute left-3 top-1/2 -translate-y-1/2" />
            <input 
              type="text" 
              placeholder="Search findings..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full sm:w-64 bg-surface-1 border border-line rounded py-1.5 pl-9 pr-4 text-[13px] text-content-secondary placeholder:text-content-muted focus:outline-none focus:border-accent-9/50 shadow-sm transition-colors"
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
      <Card className="overflow-hidden flex-1 flex flex-col p-0 bg-surface-1">
        {loading ? (
          <div className="flex items-center justify-center p-12">
            <Loader2 className="w-8 h-8 text-accent-9 animate-spin" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-line bg-surface-2/50">
                  <th className="px-6 py-3 text-[12px] font-bold text-content-muted uppercase tracking-wider w-32">Severity</th>
                  <th className="px-6 py-3 text-[12px] font-bold text-content-muted uppercase tracking-wider">Finding</th>
                  <th className="px-6 py-3 text-[12px] font-bold text-content-muted uppercase tracking-wider">Resource</th>
                  <th className="px-6 py-3 text-[12px] font-bold text-content-muted uppercase tracking-wider">Category</th>
                  <th className="px-6 py-3 text-[12px] font-bold text-content-muted uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 w-10"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {filteredFindings.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-content-muted">
                      No findings found.
                    </td>
                  </tr>
                )}
                {filteredFindings.map((finding) => (
                  <tr 
                    key={finding.finding_id} 
                    onClick={() => setSelectedFinding(finding)}
                    className="hover:bg-surface-3 cursor-pointer transition-colors group"
                  >
                    <td className="px-6 py-3.5">
                      <SeverityIndicator severity={finding.severity as any} />
                    </td>
                    <td className="px-6 py-3.5">
                      <div className="text-[14px] font-bold text-content">{finding.title}</div>
                      <div className="text-[13px] text-content-muted mt-0.5 truncate max-w-md">{finding.rule_id}</div>
                    </td>
                    <td className="px-6 py-3.5 font-mono text-[12px] text-content-secondary">
                      {finding.resource_id}
                    </td>
                    <td className="px-6 py-3.5">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-surface-2 text-content-secondary border border-line">
                        {finding.category}
                      </span>
                    </td>
                    <td className="px-6 py-3.5">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-surface-2 text-content-secondary border border-line group-hover:border-line-strong transition-colors">
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
          
          <div className="fixed inset-y-0 right-0 w-[600px] bg-surface-1 border-l border-line z-40 shadow-elev-4 flex flex-col animate-in slide-in-from-right-full duration-300">
            {/* Drawer Header */}
            <div className="px-6 py-4 border-b border-line flex items-center justify-between sticky top-0 bg-surface-1 z-10">
              <h2 className="text-[16px] font-bold text-content">Finding Details</h2>
              <button 
                onClick={() => setSelectedFinding(null)}
                className="p-1.5 hover:bg-surface-3 text-content-muted hover:text-content rounded-md transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-8 overflow-y-auto">
              {/* Title & Severity */}
              <div>
                <div className="flex items-center gap-3 mb-3">
                  <SeverityIndicator severity={selectedFinding.severity as any} showLabel={false} />
                  <span className="text-[12px] font-bold uppercase tracking-widest text-content-muted">
                    {selectedFinding.severity} SEVERITY
                  </span>
                  <span className="text-[12px] font-bold uppercase tracking-widest text-content-muted ml-auto">
                    STATUS: {selectedFinding.status}
                  </span>
                </div>
                <h3 className="text-xl font-bold text-content leading-tight">
                  {selectedFinding.title}
                </h3>
              </div>

              {/* Meta Grid */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-surface-2 rounded-lg border border-line">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-content-muted mb-1">Resource ID</div>
                  <div className="font-mono text-[12px] text-content truncate" title={selectedFinding.resource_id}>
                    {selectedFinding.resource_id}
                  </div>
                </div>
                <div className="p-3 bg-surface-2 rounded-lg border border-line">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-content-muted mb-1">Category / Rule</div>
                  <div className="text-[13px] font-medium text-content">
                    {selectedFinding.category} / {selectedFinding.rule_id}
                  </div>
                </div>
              </div>

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

            {/* Drawer Footer */}
            {selectedFinding.status === 'OPEN' && (
              <div className="px-6 py-4 border-t border-line bg-surface-1 mt-auto sticky bottom-0">
                <div className="flex items-center gap-3">
                  <Button className="flex-1" onClick={() => updateStatus('RESOLVED')}>Mark as Resolved</Button>
                  <Button variant="outline" className="flex-1 bg-surface-1" onClick={() => updateStatus('IGNORED')}>Ignore / Suppress</Button>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
