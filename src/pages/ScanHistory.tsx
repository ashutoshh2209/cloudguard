import React, { useState, useEffect } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { DataTable } from '../components/ui/DataTable';
import { Download, Play, Calendar, Loader2 } from 'lucide-react';
import { fetchApi } from '../api/client';
import { reportsApi } from '../api/reports';
import { SecurityScan } from '../types/api';
import { RunScanModal } from '../components/RunScanModal';

export function ScanHistory() {
  const [scans, setScans] = useState<SecurityScan[]>([]);
  const [loading, setLoading] = useState(true);
  const [isScanModalOpen, setIsScanModalOpen] = useState(false);
  const [generatingReportFor, setGeneratingReportFor] = useState<string | null>(null);

  const loadScans = async () => {
    try {
      setLoading(true);
      const data = await fetchApi<SecurityScan[]>('/scans');
      // Sort by started_at desc if backend doesn't
      data.sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());
      setScans(data);
    } catch (err) {
      console.error('Failed to load scans', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadScans();
  }, []);

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
        <span className="font-mono text-[13px] text-content font-bold">{item.id.substring(0, 8)}...</span>
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
      header: 'Resources Scanned',
      cell: (item: SecurityScan) => (
        <span className="text-[13px] text-content">{item.summary?.resources_scanned || 0}</span>
      ),
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
      cell: (item: SecurityScan) => (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider ${
          item.status === 'COMPLETED' ? 'bg-severity-secure/10 text-severity-secure-ink border border-severity-secure/20' :
          item.status === 'FAILED' ? 'bg-severity-critical/10 text-severity-critical-ink border border-severity-critical/20' :
          'bg-accent-subtle text-accent-9 border border-accent-border'
        }`}>
          {item.status}
        </span>
      ),
    },
    {
      header: 'Actions',
      cell: (item: SecurityScan) => (
        <div className="flex justify-end gap-2">
          <Button variant="ghost" size="sm" className="text-accent-9" onClick={() => window.location.href=`/app/findings?scan_id=${item.id}`}>
            View Findings
          </Button>
          {item.status === 'COMPLETED' && (
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => handleGenerateReport(item.id)}
              disabled={generatingReportFor === item.id}
            >
              {generatingReportFor === item.id ? (
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              ) : null}
              Generate Report
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

      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-content">Scan History</h1>
          <p className="text-[14px] text-content-secondary mt-1">Review previous security assessments and track posture changes over time.</p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="primary" className="flex items-center gap-2" onClick={() => setIsScanModalOpen(true)}>
            <Play className="w-4 h-4" />
            New Scan
          </Button>
        </div>
      </div>

      <Card className="flex-1 p-0 overflow-hidden flex flex-col bg-surface-1">
        {loading ? (
          <div className="flex flex-1 items-center justify-center p-12">
            <Loader2 className="w-8 h-8 text-accent-9 animate-spin" />
          </div>
        ) : (
          <DataTable data={scans} columns={columns} />
        )}
      </Card>
    </div>
  );
}
