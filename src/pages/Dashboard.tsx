import React, { useState, useEffect } from 'react';
import { Button } from '../components/ui/Button';
import { SeverityIndicator } from '../components/ui/SeverityIndicator';
import { RunScanModal } from '../components/RunScanModal';
import { Card, CardHeader, CardTitle } from '../components/ui/Card';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { Cloud, ShieldAlert, Server, Activity, Database, Key, CheckCircle, ShieldCheck, Cpu, Layers, Loader2, AlertTriangle } from 'lucide-react';
import { cn } from '../utils/cn';
import { fetchApi } from '../api/client';
import { DashboardSummary, AWSConnectionStatus } from '../types/api';

const ICONS: Record<string, any> = {
  Identity: Key,
  Storage: Database,
  Network: ShieldAlert,
  Compute: Layers,
  Database: Database,
  Monitoring: Activity,
};

const COLORS: Record<string, string> = {
  Identity: 'text-orange-500',
  Storage: 'text-emerald-500',
  Network: 'text-amber-500',
  Compute: 'text-blue-500',
  Database: 'text-indigo-500',
  Monitoring: 'text-violet-500',
};

const BG_COLORS: Record<string, string> = {
  Identity: 'bg-orange-500',
  Storage: 'bg-emerald-500',
  Network: 'bg-amber-500',
  Compute: 'bg-blue-500',
  Database: 'bg-indigo-500',
  Monitoring: 'bg-violet-500',
};

// Fake trend data until backend provides history
const MOCK_TREND = [
  { label: 'T-5', score: 61 },
  { label: 'T-4', score: 64 },
  { label: 'T-3', score: 63 },
  { label: 'T-2', score: 68 },
  { label: 'T-1', score: 69 },
];

export function Dashboard() {
  const [isScanModalOpen, setIsScanModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [awsStatus, setAwsStatus] = useState<AWSConnectionStatus | null>(null);

  const loadData = async () => {
    try {
      const [dashboardData, awsData] = await Promise.all([
        fetchApi<DashboardSummary>('/dashboard'),
        fetchApi<AWSConnectionStatus>('/aws/status')
      ]);
      setData(dashboardData);
      setAwsStatus(awsData);
      
      // Inject current score into mock trend
      if (dashboardData.security_score !== undefined && dashboardData.security_score !== null) {
        MOCK_TREND.push({ label: 'Now', score: dashboardData.security_score });
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <Loader2 className="w-8 h-8 text-accent-9 animate-spin" />
      </div>
    );
  }

  // Handle Empty States
  if (!awsStatus?.connected) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] text-center max-w-lg mx-auto">
        <Cloud className="w-16 h-16 text-content-muted mb-4" />
        <h2 className="text-2xl font-bold text-content mb-2">AWS Not Connected</h2>
        <p className="text-content-secondary mb-8">
          Connect an AWS account in Settings to begin analyzing your cloud security posture.
        </p>
        <Button variant="primary" onClick={() => window.location.href='/app/settings'}>
          Go to Settings
        </Button>
      </div>
    );
  }

  if (!data || data.rating === "Not Scored") {
    return (
      <div className="space-y-8 animate-in fade-in duration-300">
        <RunScanModal isOpen={isScanModalOpen} onClose={() => { setIsScanModalOpen(false); loadData(); }} />
        
        <div className="flex flex-col gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-content">Security Overview</h1>
            <p className="text-[14px] text-content-secondary mt-1">Monitor and improve your AWS security posture in real-time.</p>
          </div>
        </div>

        <div className="flex flex-col items-center justify-center min-h-[300px] text-center max-w-lg mx-auto bg-surface-1 border border-line rounded-lg p-8">
          <ShieldAlert className="w-16 h-16 text-accent-9 mb-4" />
          <h2 className="text-2xl font-bold text-content mb-2">Your AWS account is connected</h2>
          <p className="text-content-secondary mb-8">
            {data?.reason || "Run your first security scan to discover risks."}
          </p>
          <Button variant="primary" onClick={() => setIsScanModalOpen(true)}>
            Start Security Scan
          </Button>
        </div>
      </div>
    );
  }

  const score = data.security_score || 0;
  const isGood = score >= 80;
  const isOk = score >= 60 && score < 80;
  const scoreColor = isGood ? 'text-emerald-500' : (isOk ? 'text-blue-500' : 'text-orange-500');

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <RunScanModal isOpen={isScanModalOpen} onClose={() => { setIsScanModalOpen(false); loadData(); }} />
      
      {/* Header & Operational Status */}
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-content">Security Overview</h1>
            <p className="text-[14px] text-content-secondary mt-1">Monitor and improve your AWS security posture in real-time.</p>
          </div>
          <Button variant="primary" onClick={() => setIsScanModalOpen(true)}>
            Run Scan
          </Button>
        </div>

        <div className="flex items-center gap-8 py-3 border-y border-line text-[12px] font-medium text-content-muted w-full overflow-x-auto no-scrollbar">
          <div className="flex items-center gap-2 flex-shrink-0">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-content font-semibold uppercase tracking-wider">AWS Connected</span>
          </div>
          <div className="w-px h-4 bg-slate-200 flex-shrink-0"></div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <Cloud className="w-4 h-4 text-content-muted" />
            <span className="text-content-secondary">{awsStatus?.account_id}</span>
          </div>
          <div className="w-px h-4 bg-slate-200 flex-shrink-0"></div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="text-content-muted uppercase tracking-wider">Checks Run:</span>
            <span className="font-mono text-content-secondary font-bold">{data.checks_summary?.passed || 0 + (data.checks_summary?.failed || 0)}</span>
          </div>
          <div className="w-px h-4 bg-slate-200 flex-shrink-0"></div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span className="text-emerald-600 font-semibold uppercase tracking-wider">Scanned</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        
        {/* Security Posture Score */}
        <Card className="lg:col-span-1 flex flex-col items-center justify-center p-8 bg-surface-2 relative overflow-hidden">
          
          <div className="relative w-48 h-48 flex items-center justify-center mb-6">
            <div className="absolute inset-4 rounded-full border border-line bg-surface-1" />
            
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
              <div className="text-[44px] font-bold tracking-tighter text-content drop-shadow-sm">{score}</div>
              <div className="text-[12px] font-bold text-content-muted uppercase tracking-widest mt-[-4px]">/ 100</div>
            </div>
          </div>
          
          <div className="text-center relative z-10 w-full">
            <div className="text-[16px] font-bold text-content mb-1">{data.rating}</div>
            <div className="text-[13px] text-emerald-600 font-bold flex items-center justify-center gap-1">
              Latest Scan
            </div>
            
            <div className="h-8 w-full mt-4 opacity-50">
               <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={MOCK_TREND.slice(-7)}>
                  <Area type="monotone" dataKey="score" stroke="#3b82f6" fill="url(#sparkGradient)" strokeWidth={2} />
                  <defs>
                    <linearGradient id="sparkGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </Card>

        {/* Posture Trend */}
        <Card className="lg:col-span-3 flex flex-col">
          <CardHeader className="flex flex-row items-center justify-between mb-4">
            <CardTitle className="text-content">Security Posture Trend</CardTitle>
            <div className="flex bg-surface-3 p-0.5 rounded-lg border border-line">
              <button className="px-3 py-1 text-[11px] font-medium bg-surface-1 text-content rounded shadow-sm border border-line">7D</button>
            </div>
          </CardHeader>
          <div className="flex-1 w-full min-h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={MOCK_TREND}>
                <defs>
                  <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.15}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                <XAxis 
                  dataKey="label" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: '#64748b', fontSize: 12 }}
                  dy={10}
                />
                <YAxis 
                  domain={[40, 100]} 
                  axisLine={false} 
                  tickLine={false}
                  tick={{ fill: '#64748b', fontSize: 12 }}
                  dx={-10}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)' }}
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
                  activeDot={{ r: 6, stroke: 'rgba(96, 165, 250, 0.3)', strokeWidth: 4, fill: '#60a5fa' }}
                />
              </AreaChart>
            </ResponsiveContainer>
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
          <div key={risk.label} className="flex-1 flex flex-col p-4 hover:bg-surface-3 transition-colors cursor-pointer">
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
            <CardTitle className="text-content">Top Risk Findings</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => window.location.href='/app/findings'}>View all</Button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <tbody className="divide-y divide-line">
                {data.top_risks?.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-5 py-8 text-center text-content-muted">
                      No findings detected!
                    </td>
                  </tr>
                )}
                {data.top_risks?.map((item, idx) => (
                  <tr key={idx} className="hover:bg-surface-3 cursor-pointer transition-colors group" onClick={() => window.location.href=`/app/findings?id=${item.finding_id}`}>
                    <td className="px-5 py-3">
                      <div className="text-[13px] font-bold text-content">{item.title}</div>
                      <div className="font-mono text-[11px] text-content-muted mt-0.5">{item.resource_name}</div>
                    </td>
                    <td className="px-5 py-3">
                      <SeverityIndicator severity={item.severity as any} />
                    </td>
                    <td className="px-5 py-3 text-[12px] font-medium text-content-muted whitespace-nowrap">Score: {item.risk_score}</td>
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

        <div className="space-y-6 flex flex-col">
          {/* Top Risk Categories */}
          <Card>
            <CardHeader className="mb-5"><CardTitle className="text-content">Category Scores</CardTitle></CardHeader>
            <div className="space-y-5">
              {Object.entries(data.category_scores || {}).map(([cat, info]) => {
                const Icon = ICONS[cat] || ShieldAlert;
                const fgColor = COLORS[cat] || 'text-blue-500';
                const bgColor = BG_COLORS[cat] || 'bg-blue-500';
                return (
                  <div key={cat} className="group">
                    <div className="flex items-center justify-between mb-2">
                      <div className={cn("flex items-center gap-2 text-[13px] font-bold", fgColor)}>
                        <Icon className="w-4 h-4" />
                        {cat}
                      </div>
                      <span className="text-[12px] font-bold text-content">{info.score}</span>
                    </div>
                    <div className="h-1.5 w-full bg-surface-3 rounded-full overflow-hidden shadow-inner">
                      <div className={cn("h-full rounded-full transition-all duration-1000", bgColor)} style={{ width: `${info.score}%` }} />
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
