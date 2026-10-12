import React, { useState, useEffect, useCallback } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { DataTable } from '../components/ui/DataTable';
import { FileText, Download, Loader2, Play, RefreshCw, Shield, Calendar } from 'lucide-react';
import { reportsApi } from '../api/reports';
import { SecurityReport } from '../types/api';
import { useAuth } from '../context/AuthContext';

export function Reports() {
  const { activeWorkspace } = useAuth();
  const [reports, setReports] = useState<SecurityReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const loadReports = useCallback(async () => {
    try {
      setLoading(true);
      const data = await reportsApi.listReports(0, 50, activeWorkspace?.id);
      setReports(data.items || []);
    } catch (err) {
      console.error('Failed to load reports', err);
    } finally {
      setLoading(false);
    }
  }, [activeWorkspace?.id]);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  const handleDownload = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      setDownloadingId(id);
      await reportsApi.downloadReport(id);
    } catch (err) {
      console.error('Download failed', err);
      alert('Failed to download report PDF');
    } finally {
      setDownloadingId(null);
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
            <div 
              className="font-bold text-[14px] text-content hover:text-accent-10 cursor-pointer"
              onClick={() => window.location.href=`/app/reports/${item.id}`}
            >
              {item.title}
            </div>
            <div className="text-[12px] text-content-muted font-mono">{item.id.substring(0, 8)}...</div>
          </div>
        </div>
      ),
    },
    {
      header: 'Generated At',
      cell: (item: SecurityReport) => (
        <div className="flex items-center gap-2 text-content-secondary">
          <Calendar className="w-3.5 h-3.5" />
          <span className="text-[13px]">{new Date(item.generated_at).toLocaleString()}</span>
        </div>
      ),
    },
    {
      header: 'Score',
      cell: (item: SecurityReport) => (
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[12px] font-bold bg-accent-subtle text-accent-10 border border-accent-border">
            {item.security_score !== null && item.security_score !== undefined ? `${item.security_score} / 100` : 'N/A'}
          </span>
          {item.security_rating && (
            <span className="text-[12px] font-medium text-content-secondary">
              ({item.security_rating})
            </span>
          )}
        </div>
      ),
    },
    {
      header: 'Findings (C / H / M / L)',
      cell: (item: SecurityReport) => (
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className={item.critical_count > 0 ? 'text-red-500 font-bold' : 'text-content-muted'}>{item.critical_count}C</span>
          <span className="text-line">/</span>
          <span className={item.high_count > 0 ? 'text-orange-500 font-bold' : 'text-content-muted'}>{item.high_count}H</span>
          <span className="text-line">/</span>
          <span className="text-amber-500">{item.medium_count}M</span>
          <span className="text-line">/</span>
          <span className="text-blue-500">{item.low_count}L</span>
        </div>
      ),
    },
    {
      header: 'Resources',
      cell: (item: SecurityReport) => (
        <span className="text-[13px] text-content font-medium">{item.resource_count}</span>
      ),
    },
    {
      header: 'Actions',
      cell: (item: SecurityReport) => (
        <div className="flex justify-end gap-2">
          <Button variant="ghost" size="sm" className="text-accent-9" onClick={() => window.location.href=`/app/reports/${item.id}`}>
            View
          </Button>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={(e) => handleDownload(item.id, e)} 
            disabled={downloadingId === item.id}
          >
            {downloadingId === item.id ? (
              <Loader2 className="w-3 h-3 mr-1 animate-spin" />
            ) : (
              <Download className="w-3 h-3 mr-1" />
            )}
            PDF
          </Button>
        </div>
      ),
      className: 'text-right',
    }
  ];

  return (
    <div className="h-full flex flex-col animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-content">Security Reports</h1>
            {activeWorkspace && (
              <span className="text-[12px] font-medium text-content-secondary bg-surface-2 px-2.5 py-0.5 rounded-full border border-line">
                {activeWorkspace.name}
              </span>
            )}
          </div>
          <p className="text-[14px] text-content-secondary mt-1">Professional executive assessments and deterministic compliance reports.</p>
        </div>

        <div className="flex items-center gap-2">
          <Button 
            variant="outline" 
            size="sm" 
            className="flex items-center gap-2" 
            onClick={loadReports}
            disabled={loading}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button 
            variant="primary" 
            onClick={() => window.location.href='/app/scans'} 
            className="flex items-center gap-2"
          >
            <Play className="w-4 h-4" />
            Generate From Scan
          </Button>
        </div>
      </div>

      <Card className="flex-1 p-0 overflow-hidden flex flex-col bg-surface-1">
        {loading && reports.length === 0 ? (
          <div className="flex flex-1 items-center justify-center p-12">
            <Loader2 className="w-8 h-8 text-accent-9 animate-spin" />
          </div>
        ) : reports.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center p-12 text-center max-w-sm mx-auto">
            <FileText className="w-12 h-12 text-content-muted mb-4 opacity-50" />
            <div className="text-content font-bold mb-2">No security reports yet</div>
            <div className="text-content-muted text-sm mb-6">
              Generate an executive security assessment from any completed scan in your scan history.
            </div>
            <Button variant="outline" onClick={() => window.location.href='/app/scans'}>
              View Scan History
            </Button>
          </div>
        ) : (
          <DataTable data={reports} columns={columns} />
        )}
      </Card>
    </div>
  );
}
