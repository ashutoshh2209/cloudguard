import React, { useState, useEffect, useCallback } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { DataTable } from '../components/ui/DataTable';
import { Download, Play, Calendar, Loader2, CheckCircle, AlertTriangle, XCircle, RefreshCw, Eye, Filter } from 'lucide-react';
import { scansApi } from '../api/scans';
import { reportsApi } from '../api/reports';
import { SecurityScan } from '../types/api';
import { RunScanModal } from '../components/RunScanModal';
import { ScanDetailModal } from '../components/ScanDetailModal';
import { useAuth } from '../context/AuthContext';

export function ScanHistory() {
  const { activeWorkspace } = useAuth();
  const [scans, setScans] = useState<SecurityScan[]>([]);
  const [loading, setLoading] = useState(true);
  const [isScanModalOpen, setIsScanModalOpen] = useState(false);
  const [selectedScanId, setSelectedScanId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [generatingReportFor, setGeneratingReportFor] = useState<string | null>(null);

  const isViewer = activeWorkspace?.role === 'VIEWER';

  const loadScans = useCallback(async () => {
    try {
      setLoading(true);
      const data = await scansApi.listScans({
        workspace_id: activeWorkspace?.id,
        status: statusFilter || undefined,
      });
      // Sort by started_at desc if backend doesn't
      data.sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());
      setScans(data);
    } catch (err) {
      console.error('Failed to load scans', err);
    } finally {
      setLoading(false);
    }
  }, [activeWorkspace?.id, statusFilter]);

  useEffect(() => {
    loadScans();
  }, [loadScans]);

  // Auto-refresh if any scan is running or queued
  useEffect(() => {
    const hasActiveScan = scans.some(s => s.status === 'RUNNING' || s.status === 'QUEUED' || s.status === 'PENDING');
    if (!hasActiveScan) return;

    const interval = setInterval(() => {
      scansApi.listScans({ 
        workspace_id: activeWorkspace?.id,
        status: statusFilter || undefined,
      })
        .then(data => {
          data.sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());
          setScans(data);
        })
        .catch(err => console.error(err));
    }, 4000);

    return () => clearInterval(interval);
  }, [scans, activeWorkspace?.id, statusFilter]);

  const handleGenerateReport = async (scanId: string) => {
    try {
      setGeneratingReportFor(scanId);
      await reportsApi.createReport(scanId);
      window.location.href = '/app/reports';
    } catch (err) {
      console.error('Failed to generate report', err);
      alert('Failed to generate report');
    } finally {
      setGeneratingReportFor(null);
    }
  };

  const columns: any[] = [
    {
      header: 'Scan ID',
      cell: (item: SecurityScan) => (
        <button 
          onClick={() => setSelectedScanId(item.id)}
          className="font-mono text-[13px] text-accent-10 font-bold hover:underline flex items-center gap-1.5 text-left"
          title="Click to view scan details"
        >
          <span>{item.id.substring(0, 8)}...</span>
        </button>
      ),
    },
    {
      header: 'Date',
      cell: (item: SecurityScan) => (
        <div className="flex items-center gap-2 text-content-secondary">
          <Calendar className="w-3 h-3" />
          <span className="text-[13px]">{new Date(item.started_at).toLocaleString()}</span>
        </div>
      ),
    },
    {
      header: 'Resources',
      cell: (item: SecurityScan) => (
        <span className="text-[13px] text-content font-medium">{item.summary?.resources_scanned || 0}</span>
      ),
    },
    {
      header: 'Checks (Pass / Fail / Err)',
      cell: (item: SecurityScan) => {
        const passed = item.summary?.checks_passed ?? Math.max(0, (item.summary?.checks_completed || 0) - (item.summary?.checks_failed || 0));
        const failed = item.summary?.checks_failed || 0;
        const errored = item.summary?.checks_errored || 0;
        return (
          <div className="flex items-center gap-2 text-[12px] font-mono">
            <span className="text-severity-secure-ink font-semibold">{passed}P</span>
            <span className="text-content-muted">/</span>
            <span className={failed > 0 ? 'text-severity-critical-ink font-semibold' : 'text-content-secondary'}>{failed}F</span>
            {errored > 0 && (
              <>
                <span className="text-content-muted">/</span>
                <span className="text-amber-500 font-semibold">{errored}E</span>
              </>
            )}
          </div>
        );
      },
    },
    {
      header: 'Score',
      cell: (item: SecurityScan) => (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[12px] font-bold bg-accent-subtle text-accent-10 border border-accent-border">
          {item.security_score !== null && item.security_score !== undefined ? item.security_score : 'N/A'}
        </span>
      ),
    },
    {
      header: 'Status',
      cell: (item: SecurityScan) => {
        let badgeClass = 'bg-accent-subtle text-accent-9 border border-accent-border';
        if (item.status === 'COMPLETED') {
          badgeClass = 'bg-severity-secure/10 text-severity-secure-ink border border-severity-secure/20';
        } else if (item.status === 'PARTIAL') {
          badgeClass = 'bg-amber-500/10 text-amber-600 border border-amber-500/20';
        } else if (item.status === 'FAILED') {
          badgeClass = 'bg-severity-critical/10 text-severity-critical-ink border border-severity-critical/20';
        } else if (item.status === 'RUNNING' || item.status === 'QUEUED') {
          badgeClass = 'bg-blue-500/10 text-blue-600 border border-blue-500/20 animate-pulse';
        }

        return (
          <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider ${badgeClass}`}>
            {item.status}
          </span>
        );
      },
    },
    {
      header: 'Actions',
      cell: (item: SecurityScan) => (
        <div className="flex justify-end gap-2">
          <Button 
            variant="ghost" 
            size="sm" 
            className="text-content-secondary hover:text-content" 
            onClick={() => setSelectedScanId(item.id)}
          >
            <Eye className="w-3.5 h-3.5 mr-1" />
            Details
          </Button>
          <Button 
            variant="ghost" 
            size="sm" 
            className="text-accent-9" 
            onClick={() => window.location.href=`/app/findings?scan_id=${item.id}`}
          >
            Findings
          </Button>
          {(item.status === 'COMPLETED' || item.status === 'PARTIAL') && (
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => handleGenerateReport(item.id)}
              disabled={generatingReportFor === item.id}
            >
              {generatingReportFor === item.id ? (
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              ) : null}
              Report
            </Button>
          )}
        </div>
      ),
      className: 'text-right',
    }
  ];

  return (
    <div className="h-full flex flex-col animate-in fade-in duration-300">
      <RunScanModal isOpen={isScanModalOpen} onClose={() => { setIsScanModalOpen(false); loadScans(); }} />
      <ScanDetailModal 
        isOpen={!!selectedScanId} 
        scanId={selectedScanId} 
        onClose={() => setSelectedScanId(null)} 
      />

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-content">Scan History</h1>
            {activeWorkspace && (
              <span className="text-[12px] font-medium text-content-secondary bg-surface-2 px-2.5 py-0.5 rounded-full border border-line">
                {activeWorkspace.name}
              </span>
            )}
          </div>
          <p className="text-[14px] text-content-secondary mt-1">Review deterministic security assessments and track posture changes over time.</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2 bg-surface-2 px-2.5 py-1.5 rounded-lg border border-line text-xs">
            <Filter className="w-3.5 h-3.5 text-content-muted" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              aria-label="Filter scans by status"
              className="bg-transparent text-content font-medium outline-none cursor-pointer text-xs"
            >
              <option value="" className="bg-surface-1 text-content">All Statuses</option>
              <option value="COMPLETED" className="bg-surface-1 text-content">Completed</option>
              <option value="PARTIAL" className="bg-surface-1 text-content">Partial</option>
              <option value="FAILED" className="bg-surface-1 text-content">Failed</option>
              <option value="RUNNING" className="bg-surface-1 text-content">Running</option>
              <option value="QUEUED" className="bg-surface-1 text-content">Queued</option>
            </select>
          </div>

          <Button 
            variant="outline" 
            size="sm" 
            className="flex items-center gap-2" 
            onClick={loadScans}
            disabled={loading}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button 
            variant="primary" 
            className="flex items-center gap-2" 
            onClick={() => setIsScanModalOpen(true)}
            disabled={isViewer}
            title={isViewer ? 'Viewer role cannot trigger scans' : 'Run security assessment'}
          >
            <Play className="w-4 h-4" />
            New Scan
          </Button>
        </div>
      </div>

      <Card className="flex-1 p-0 overflow-hidden flex flex-col bg-surface-1">
        {loading && scans.length === 0 ? (
          <div className="flex flex-1 items-center justify-center p-12">
            <Loader2 className="w-8 h-8 text-accent-9 animate-spin" />
          </div>
        ) : scans.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center p-12 text-center">
            <Calendar className="w-12 h-12 text-content-muted mb-4 opacity-50" />
            <h3 className="text-lg font-bold text-content mb-1">
              {statusFilter ? `No ${statusFilter.toLowerCase()} scans found` : 'No security scans yet'}
            </h3>
            <p className="text-[14px] text-content-secondary max-w-sm mb-6">
              {statusFilter 
                ? 'Try changing the status filter or run a new scan.'
                : 'Launch your first security scan to analyze AWS configurations against deterministic rules.'}
            </p>
            {!statusFilter && (
              <Button variant="primary" onClick={() => setIsScanModalOpen(true)} disabled={isViewer}>
                <Play className="w-4 h-4 mr-2" />
                Run First Scan
              </Button>
            )}
          </div>
        ) : (
          <DataTable data={scans} columns={columns} />
        )}
      </Card>
    </div>
  );
}
