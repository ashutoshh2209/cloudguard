import React, { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { SeverityIndicator } from '../components/ui/SeverityIndicator';
import { RunScanModal } from '../components/RunScanModal';
import { Card, CardHeader, CardTitle } from '../components/ui/Card';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import {
  Cloud,
  ShieldAlert,
  Activity,
  Database,
  Key,
  ShieldCheck,
  Layers,
  Loader2,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  RefreshCw,
  Clock,
} from 'lucide-react';
import { cn } from '../utils/cn';
import { fetchApi } from '../api/client';
import { DashboardSummary, AWSConnectionStatus } from '../types/api';
import { useAuth } from '../context/AuthContext';

const ICONS: Record<string, any> = {
  IDENTITY: Key,
  Identity: Key,
  STORAGE: Database,
  Storage: Database,
  NETWORK: ShieldAlert,
  Network: ShieldAlert,
  COMPUTE: Layers,
  Compute: Layers,
  DATABASE: Database,
  Database: Database,
  MONITORING: Activity,
  Monitoring: Activity,
};

const COLORS: Record<string, string> = {
  IDENTITY: 'text-orange-500',
  Identity: 'text-orange-500',
  STORAGE: 'text-emerald-500',
  Storage: 'text-emerald-500',
  NETWORK: 'text-amber-500',
  Network: 'text-amber-500',
  COMPUTE: 'text-blue-500',
  Compute: 'text-blue-500',
  DATABASE: 'text-indigo-500',
  Database: 'text-indigo-500',
  MONITORING: 'text-violet-500',
  Monitoring: 'text-violet-500',
};

const BG_COLORS: Record<string, string> = {
  IDENTITY: 'bg-orange-500',
  Identity: 'bg-orange-500',
  STORAGE: 'bg-emerald-500',
  Storage: 'bg-emerald-500',
  NETWORK: 'bg-amber-500',
  Network: 'bg-amber-500',
  COMPUTE: 'bg-blue-500',
  Compute: 'bg-blue-500',
  DATABASE: 'bg-indigo-500',
  Database: 'bg-indigo-500',
  MONITORING: 'bg-violet-500',
  Monitoring: 'bg-violet-500',
};

export function Dashboard() {
  const { activeWorkspace } = useAuth();
  const [isScanModalOpen, setIsScanModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [awsStatus, setAwsStatus] = useState<AWSConnectionStatus | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const wsQuery = activeWorkspace?.id ? `?workspace_id=${encodeURIComponent(activeWorkspace.id)}` : '';
      const [dashboardData, awsData] = await Promise.all([
        fetchApi<DashboardSummary>(`/dashboard/summary${wsQuery}`),
        fetchApi<AWSConnectionStatus>(`/aws/status${wsQuery}`)
      ]);
      setData(dashboardData);
      setAwsStatus(awsData);
    } catch (err: any) {
      console.error('Failed to load dashboard data:', err);
      setError(err?.message || 'Failed to load security posture data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [activeWorkspace?.id]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] gap-3">
        <Loader2 className="w-8 h-8 text-accent-9 animate-spin" />
        <p className="text-sm text-content-muted">Loading security dashboard...</p>
      </div>
    );
  }

  // Handle Error State
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[450px] text-center max-w-md mx-auto p-6 bg-surface-1 border border-line rounded-lg">
        <AlertTriangle className="w-12 h-12 text-rose-500 mb-3" />
        <h2 className="text-xl font-bold text-content mb-2">Unable to load dashboard</h2>
        <p className="text-sm text-content-secondary mb-6">{error}</p>
        <Button variant="primary" onClick={loadData} className="flex items-center gap-2">
          <RefreshCw className="w-4 h-4" />
          Retry
        </Button>
      </div>
    );
  }

  // Handle AWS Disconnected State
  if (!awsStatus?.connected) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] text-center max-w-lg mx-auto">
        <Cloud className="w-16 h-16 text-content-muted mb-4" />
        <h2 className="text-2xl font-bold text-content mb-2">AWS Not Connected</h2>
        <p className="text-content-secondary mb-8">
          Connect an AWS account in Settings to begin analyzing cloud security posture.
        </p>
        <Button variant="primary" onClick={() => window.location.href='/app/settings'}>
          Go to Settings
        </Button>
      </div>
    );
  }

  // Handle Unscored / Empty Scan State
  if (!data || data.rating === "Not Scored" || data.security_score === null || data.security_score === undefined) {
    return (
      <div className="space-y-8 animate-in fade-in duration-300">
        <RunScanModal isOpen={isScanModalOpen} onClose={() => { setIsScanModalOpen(false); loadData(); }} />
        
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-bold tracking-tight text-content">Security Overview</h1>
          <p className="text-[14px] text-content-secondary">
            Deterministic security posture monitoring for <span className="font-semibold text-content">{activeWorkspace?.name || 'Workspace'}</span>.
          </p>
        </div>

        <div className="flex flex-col items-center justify-center min-h-[320px] text-center max-w-lg mx-auto bg-surface-1 border border-line rounded-lg p-8">
          <ShieldAlert className="w-16 h-16 text-accent-9 mb-4" />
          <h2 className="text-2xl font-bold text-content mb-2">AWS Account Connected</h2>
          <p className="text-content-secondary mb-6">
            {data?.reason || "No security scans have been completed yet. Run a scan to discover resources and assess compliance."}
          </p>
          <Button variant="primary" onClick={() => setIsScanModalOpen(true)}>
            Start Security Scan
          </Button>
        </div>
      </div>
    );
  }

  const score = data.security_score;
  const isGood = score >= 75;
  const isOk = score >= 60 && score < 75;
  const scoreColor = isGood ? 'text-emerald-500' : (isOk ? 'text-blue-500' : 'text-orange-500');

  // Real historical trend data (zero fabricated points)
  const trendData = (data.score_trend || []).map(p => ({
    label: p.date,
    score: p.score,
    rating: p.rating,
    scan_id: p.scan_id,
  }));

  const totalChecks =
    (data.checks_summary?.passed || 0) +
    (data.checks_summary?.failed || 0) +
    (data.checks_summary?.errors || 0);

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <RunScanModal isOpen={isScanModalOpen} onClose={() => { setIsScanModalOpen(false); loadData(); }} />
      
      {/* Header & Operational Status */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight text-content">Security Overview</h1>
              {activeWorkspace && (
                <span className="text-[12px] font-medium text-content-secondary bg-surface-2 px-2.5 py-0.5 rounded-full border border-line">
                  {activeWorkspace.name}
                </span>
              )}
            </div>
            <p className="text-[14px] text-content-secondary mt-1">
              Deterministic risk engine score and vulnerability metrics.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={loadData} className="flex items-center gap-2">
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh
            </Button>
            <Button variant="primary" onClick={() => setIsScanModalOpen(true)}>
              Run Scan
            </Button>
          </div>
        </div>

        <div className="flex items-center gap-6 py-3 border-y border-line text-[12px] font-medium text-content-muted w-full overflow-x-auto no-scrollbar">
          <div className="flex items-center gap-2 flex-shrink-0">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-content font-semibold uppercase tracking-wider">AWS Connected</span>
          </div>
          <div className="w-px h-4 bg-slate-200 dark:bg-slate-700 flex-shrink-0" />
          <div className="flex items-center gap-2 flex-shrink-0">
            <Cloud className="w-4 h-4 text-content-muted" />
            <span className="text-content-secondary font-mono">{awsStatus?.account_id || 'AWS Account'}</span>
          </div>
          <div className="w-px h-4 bg-slate-200 dark:bg-slate-700 flex-shrink-0" />
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="text-content-muted uppercase tracking-wider">Resources:</span>
            <span className="font-mono text-content font-bold">{data.total_resources || 0}</span>
          </div>
          <div className="w-px h-4 bg-slate-200 dark:bg-slate-700 flex-shrink-0" />
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="text-content-muted uppercase tracking-wider">Checks:</span>
            <span className="font-mono text-content font-bold">{totalChecks}</span>
          </div>
          {data.last_scanned_at && (
            <>
              <div className="w-px h-4 bg-slate-200 dark:bg-slate-700 flex-shrink-0" />
              <div className="flex items-center gap-2 flex-shrink-0">
                <Clock className="w-3.5 h-3.5 text-content-muted" />
                <span className="text-content-muted">Last Scanned:</span>
                <span className="text-content-secondary font-mono text-[11px]">
                  {new Date(data.last_scanned_at).toLocaleString()}
                </span>
              </div>
            </>
          )}
          <div className="w-px h-4 bg-slate-200 dark:bg-slate-700 flex-shrink-0" />
          <div className="flex items-center gap-2 flex-shrink-0">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span className="text-emerald-600 font-semibold uppercase tracking-wider">
              {data.latest_scan_status || 'COMPLETED'}
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        
        {/* Security Posture Score */}
        <Card className="lg:col-span-1 flex flex-col items-center justify-center p-6 bg-surface-2 relative overflow-hidden">
          
          <div className="relative w-44 h-44 flex items-center justify-center mb-4">
            <div className="absolute inset-3 rounded-full border border-line bg-surface-1" />
            
            <svg className="absolute inset-0 w-full h-full -rotate-90 drop-shadow-[0_0_8px_rgba(96,165,250,0.4)]" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="44" fill="none" stroke="currentColor" strokeWidth="4" className="text-white/5" />
              <circle 
                cx="50" cy="50" r="44" fill="none" stroke="url(#blue-gradient)" strokeWidth="4" 
                strokeLinecap="round"
                strokeDasharray={`${(score / 100) * 276} 276`}
              />
              <defs>
                <linearGradient id="blue-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#60a5fa" />
                  <stop offset="100%" stopColor="#3b82f6" />
                </linearGradient>
              </defs>
            </svg>
            
            <div className="text-center relative z-10">
              <div className="text-[40px] font-bold tracking-tighter text-content drop-shadow-sm">{score}</div>
              <div className="text-[11px] font-bold text-content-muted uppercase tracking-widest mt-[-4px]">/ 100</div>
            </div>
          </div>
          
          <div className="text-center relative z-10 w-full space-y-1">
            <div className="text-[17px] font-bold text-content">{data.rating}</div>
            
            {/* Previous Score & Delta */}
            {data.previous_score !== null && data.previous_score !== undefined ? (
              <div className="flex items-center justify-center gap-1.5 text-[12px] font-medium">
                <span className="text-content-muted">Prev: {data.previous_score}</span>
                <span className="text-content-muted">•</span>
                {data.score_delta !== null && data.score_delta !== undefined && (
                  <span className={`inline-flex items-center gap-0.5 font-bold ${
                    data.score_delta > 0
                      ? 'text-emerald-500'
                      : data.score_delta < 0
                      ? 'text-rose-500'
                      : 'text-content-muted'
                  }`}>
                    {data.score_delta > 0 ? (
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    ) : data.score_delta < 0 ? (
                      <ArrowDownRight className="w-3.5 h-3.5" />
                    ) : (
                      <Minus className="w-3.5 h-3.5" />
                    )}
                    {data.score_delta > 0 ? `+${data.score_delta}` : data.score_delta}
                  </span>
                )}
              </div>
            ) : (
              <div className="text-[12px] text-content-muted">Baseline Assessment</div>
            )}
          </div>
        </Card>

        {/* Posture Trend */}
        <Card className="lg:col-span-3 flex flex-col p-6">
          <CardHeader className="flex flex-row items-center justify-between p-0 mb-4">
            <div>
              <CardTitle className="text-content">Security Posture Trend</CardTitle>
              <p className="text-[12px] text-content-muted mt-0.5">
                Deterministic security scores across completed scans.
              </p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => window.location.href='/app/scans'}>
              View History
            </Button>
          </CardHeader>

          <div className="flex-1 w-full min-h-[200px] flex items-center justify-center">
            {trendData.length >= 2 ? (
              <ResponsiveContainer width="100%" height={210}>
                <AreaChart data={trendData}>
                  <defs>
                    <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                  <XAxis 
                    dataKey="label" 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{ fill: '#64748b', fontSize: 11 }}
                    dy={8}
                  />
                  <YAxis 
                    domain={[0, 100]} 
                    axisLine={false} 
                    tickLine={false}
                    tick={{ fill: '#64748b', fontSize: 11 }}
                    dx={-8}
                  />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    itemStyle={{ color: '#f8fafc', fontSize: '13px', fontWeight: 600 }}
                    labelStyle={{ color: '#94a3b8', fontSize: '12px', marginBottom: '4px' }}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="score" 
                    stroke="#60a5fa" 
                    strokeWidth={2}
                    fillOpacity={1} 
                    fill="url(#colorScore)" 
                    activeDot={{ r: 5, stroke: 'rgba(96, 165, 250, 0.4)', strokeWidth: 3, fill: '#60a5fa' }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : trendData.length === 1 ? (
              <div className="flex flex-col items-center justify-center text-center p-6 bg-surface-2/50 border border-line rounded-lg w-full">
                <ShieldCheck className="w-8 h-8 text-accent-9 mb-2" />
                <div className="text-sm font-semibold text-content">1 Scan Completed (Score: {trendData[0].score})</div>
                <p className="text-xs text-content-muted mt-1 max-w-sm">
                  Historical trend graph will automatically render once additional scans are performed.
                </p>
              </div>
            ) : (
              <div className="text-xs text-content-muted">No completed scan history yet.</div>
            )}
          </div>
        </Card>

      </div>

      {/* Risk Summary Toolbar */}
      <div className="flex flex-col lg:flex-row bg-surface-2 border border-line rounded-lg divide-y lg:divide-y-0 lg:divide-x divide-line overflow-hidden">
        {[
          { label: 'CRITICAL', count: data.findings_summary?.critical || 0, color: 'text-red-400', bg: 'bg-red-500' },
          { label: 'HIGH', count: data.findings_summary?.high || 0, color: 'text-orange-400', bg: 'bg-orange-500' },
          { label: 'MEDIUM', count: data.findings_summary?.medium || 0, color: 'text-amber-400', bg: 'bg-amber-500' },
          { label: 'LOW', count: data.findings_summary?.low || 0, color: 'text-blue-400', bg: 'bg-blue-500' },
          { label: 'INFO', count: data.findings_summary?.info || 0, color: 'text-emerald-400', bg: 'bg-emerald-500' },
        ].map(risk => (
          <div
            key={risk.label}
            className="flex-1 flex flex-col p-4 hover:bg-surface-3 transition-colors cursor-pointer"
            onClick={() => window.location.href = `/app/findings?severity=${risk.label}`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className={cn("text-[11px] font-bold uppercase tracking-wider text-content-muted")}>{risk.label}</div>
              <div className={cn("w-1.5 h-1.5 rounded-full", risk.bg)} />
            </div>
            <div className={cn("text-3xl font-bold font-mono tracking-tight", risk.color)}>
              {risk.count < 10 && risk.count > 0 ? `0${risk.count}` : risk.count}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Recent Critical Findings */}
        <Card className="lg:col-span-2 p-0 overflow-hidden flex flex-col">
          <div className="p-5 border-b border-line flex items-center justify-between bg-surface-2/50">
            <div>
              <CardTitle className="text-content">Top Risk Findings</CardTitle>
              <p className="text-[12px] text-content-muted mt-0.5">Prioritized by deterministic risk score.</p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => window.location.href='/app/findings'}>
              View All ({data.total_findings || 0})
            </Button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <tbody className="divide-y divide-line">
                {(!data.top_risks || data.top_risks.length === 0) && (
                  <tr>
                    <td colSpan={4} className="px-5 py-8 text-center text-content-muted">
                      No active findings detected.
                    </td>
                  </tr>
                )}
                {data.top_risks?.map((item, idx) => (
                  <tr key={idx} className="hover:bg-surface-3 cursor-pointer transition-colors group" onClick={() => window.location.href=`/app/findings`}>
                    <td className="px-5 py-3">
                      <div className="text-[13px] font-bold text-content">{item.title}</div>
                      <div className="font-mono text-[11px] text-content-muted mt-0.5">{item.resource_name}</div>
                    </td>
                    <td className="px-5 py-3">
                      <SeverityIndicator severity={item.severity as any} />
                    </td>
                    <td className="px-5 py-3 text-[12px] font-mono font-medium text-content-secondary whitespace-nowrap">
                      Risk: {item.risk_score} ({item.priority})
                    </td>
                    <td className="px-5 py-3">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-surface-2 text-content-secondary border border-line group-hover:border-line-strong transition-colors">
                        OPEN
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Category Scores Breakdown */}
        <div className="space-y-6 flex flex-col">
          <Card className="p-5">
            <CardHeader className="p-0 mb-4">
              <CardTitle className="text-content">Category Scores</CardTitle>
              <p className="text-[12px] text-content-muted mt-0.5">Subsystem security ratings.</p>
            </CardHeader>
            <div className="space-y-4">
              {Object.keys(data.category_scores || {}).length === 0 && (
                <div className="text-xs text-content-muted text-center py-4">No category data recorded.</div>
              )}
              {Object.entries(data.category_scores || {}).map(([cat, info]) => {
                const Icon = ICONS[cat] || ShieldAlert;
                const fgColor = COLORS[cat] || 'text-blue-500';
                const bgColor = BG_COLORS[cat] || 'bg-blue-500';
                return (
                  <div key={cat} className="group">
                    <div className="flex items-center justify-between mb-1.5">
                      <div className={cn("flex items-center gap-2 text-[13px] font-bold", fgColor)}>
                        <Icon className="w-3.5 h-3.5" />
                        {cat}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] text-content-muted">{info.findings} findings</span>
                        <span className="text-[12px] font-bold text-content font-mono">{info.score}</span>
                      </div>
                    </div>
                    <div className="h-1.5 w-full bg-surface-3 rounded-full overflow-hidden shadow-inner">
                      <div className={cn("h-full rounded-full transition-all duration-700", bgColor)} style={{ width: `${info.score}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>

      </div>
    </div>
  );
}
