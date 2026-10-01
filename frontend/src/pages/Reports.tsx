import React, { useState, useEffect } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { DataTable } from '../components/ui/DataTable';
import { FileText, Download, Loader2, Play } from 'lucide-react';
import { reportsApi } from '../api/reports';
import { SecurityReport } from '../types/api';

export function Reports() {
  const [reports, setReports] = useState<SecurityReport[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    try {
      setLoading(true);
      const data = await reportsApi.listReports();
      setReports(data.items);
    } catch (err) {
      console.error('Failed to load reports', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await reportsApi.downloadReport(id);
    } catch (err) {
      console.error('Download failed', err);
    }
  };

  const columns: any[] = [
    {
      header: 'Report Title',
      cell: (item: SecurityReport) => (
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-surface-2 flex items-center justify-center border border-line">
            <FileText className="w-4 h-4 text-accent-9" />
          </div>
          <div>
            <div className="font-bold text-[14px] text-content">{item.title}</div>
            <div className="text-[12px] text-content-muted font-mono">{item.id.substring(0, 8)}</div>
          </div>
        </div>
      ),
    },
    {
      header: 'Generated At',
      cell: (item: SecurityReport) => (
        <span className="text-[13px] text-content-secondary">{new Date(item.generated_at).toLocaleString()}</span>
      ),
    },
    {
      header: 'Score',
      cell: (item: SecurityReport) => (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[12px] font-bold bg-accent-subtle text-accent-10 border border-accent-border">
          {item.security_score !== null ? item.security_score : 'N/A'}
        </span>
      ),
    },
    {
      header: 'Findings',
      cell: (item: SecurityReport) => (
        <span className="text-[13px] text-content">{item.finding_count}</span>
      ),
    },
    {
      header: 'Actions',
      cell: (item: SecurityReport) => (
        <div className="flex justify-end gap-2">
          <Button variant="ghost" size="sm" className="text-accent-9" onClick={() => window.location.href=`/app/reports/${item.id}`}>
            View
          </Button>
          <Button variant="outline" size="sm" onClick={(e) => handleDownload(item.id, e)}>
            <Download className="w-3 h-3 mr-1" /> PDF
          </Button>
        </div>
      ),
      className: 'text-right',
    }
  ];

  return (
    <div className="h-full flex flex-col animate-in fade-in duration-300">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-content">Security Reports</h1>
          <p className="text-[14px] text-content-secondary mt-1">Professional security assessments and compliance reports.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="primary" onClick={() => window.location.href='/app/scans'} className="flex items-center gap-2">
            Generate Report
          </Button>
        </div>
      </div>

      <Card className="flex-1 p-0 overflow-hidden flex flex-col bg-surface-1">
        {loading ? (
          <div className="flex flex-1 items-center justify-center p-12">
            <Loader2 className="w-8 h-8 text-accent-9 animate-spin" />
          </div>
        ) : reports.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center p-12 text-center max-w-sm mx-auto">
            <FileText className="w-12 h-12 text-content-muted mb-4" />
            <div className="text-content font-bold mb-2">No reports generated</div>
            <div className="text-content-muted text-sm mb-6">Generate a security report from any completed scan in your scan history.</div>
            <Button variant="outline" onClick={() => window.location.href='/app/scans'}>
              Go to Scan History
            </Button>
          </div>
        ) : (
          <DataTable data={reports} columns={columns} />
        )}
      </Card>
    </div>
  );
}
