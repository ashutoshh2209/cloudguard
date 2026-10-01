import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Download, Loader2, ArrowLeft, Shield, CheckCircle, AlertTriangle } from 'lucide-react';
import { reportsApi } from '../api/reports';
import { SecurityReportDetail } from '../types/api';

export function ReportDetail() {
  const { id } = useParams<{ id: string }>();
  const [details, setDetails] = useState<SecurityReportDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      loadReport(id);
    }
  }, [id]);

  const loadReport = async (reportId: string) => {
    try {
      setLoading(true);
      const data = await reportsApi.getReport(reportId);
      setDetails(data);
    } catch (err) {
      console.error('Failed to load report', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!id) return;
    try {
      await reportsApi.downloadReport(id);
    } catch (err) {
      console.error('Download failed', err);
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-accent-9 animate-spin" />
      </div>
    );
  }

  if (!details) {
    return (
      <div className="h-full flex flex-col items-center justify-center">
        <div className="text-content font-bold text-lg mb-2">Report not found</div>
        <Button variant="outline" onClick={() => window.location.href='/app/reports'}>Go Back</Button>
      </div>
    );
  }

  const { report, executive_summary, security_posture, finding_summary, category_scores, top_findings } = details;

  return (
    <div className="h-full flex flex-col animate-in fade-in duration-300 pb-12 overflow-y-auto">
      <div className="flex items-center gap-4 mb-6">
        <Button variant="ghost" className="p-2" onClick={() => window.location.href='/app/reports'}>
          <ArrowLeft className="w-4 h-4 text-content-secondary" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-content">{report.title}</h1>
          <p className="text-[14px] text-content-secondary mt-1">Generated: {new Date(report.generated_at).toLocaleString()}</p>
        </div>
        <div className="ml-auto">
          <Button variant="primary" onClick={handleDownload}>
            <Download className="w-4 h-4 mr-2" />
            Download PDF
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <Card className="p-6 flex flex-col justify-center items-center text-center">
          <Shield className="w-12 h-12 text-accent-9 mb-4" />
          <div className="text-sm font-bold text-content-secondary uppercase tracking-wider mb-1">Security Score</div>
          <div className="text-5xl font-black text-content">{security_posture.score ?? 'N/A'}</div>
          <div className="text-sm text-content-muted mt-2">Rating: {security_posture.rating ?? 'N/A'}</div>
        </Card>

        <Card className="p-6 col-span-2">
          <h3 className="text-lg font-bold text-content mb-4">Executive Summary</h3>
          <p className="text-content-secondary leading-relaxed">
            {executive_summary.summary_text}
          </p>
          <div className="grid grid-cols-3 gap-4 mt-6">
            <div className="bg-surface-2 p-3 rounded border border-line">
              <div className="text-xs text-content-muted uppercase">Resources Assessed</div>
              <div className="text-xl font-bold text-content mt-1">{report.resource_count}</div>
            </div>
            <div className="bg-surface-2 p-3 rounded border border-line">
              <div className="text-xs text-content-muted uppercase">Coverage</div>
              <div className="text-xl font-bold text-content mt-1">{security_posture.coverage}%</div>
            </div>
            <div className="bg-surface-2 p-3 rounded border border-line">
              <div className="text-xs text-content-muted uppercase">Total Findings</div>
              <div className="text-xl font-bold text-content mt-1">{report.finding_count}</div>
            </div>
          </div>
        </Card>
      </div>

      <h2 className="text-xl font-bold text-content mb-4">Finding Distribution</h2>
      <div className="grid grid-cols-5 gap-4 mb-8">
        {[
          { label: 'Critical', count: finding_summary.critical, color: 'text-severity-critical-ink', bg: 'bg-severity-critical/10', border: 'border-severity-critical/20' },
          { label: 'High', count: finding_summary.high, color: 'text-severity-high-ink', bg: 'bg-severity-high/10', border: 'border-severity-high/20' },
          { label: 'Medium', count: finding_summary.medium, color: 'text-severity-medium-ink', bg: 'bg-severity-medium/10', border: 'border-severity-medium/20' },
          { label: 'Low', count: finding_summary.low, color: 'text-severity-low-ink', bg: 'bg-severity-low/10', border: 'border-severity-low/20' },
          { label: 'Info', count: finding_summary.info, color: 'text-severity-secure-ink', bg: 'bg-severity-secure/10', border: 'border-severity-secure/20' },
        ].map(s => (
          <div key={s.label} className={`p-4 rounded border flex flex-col items-center justify-center ${s.bg} ${s.border}`}>
            <div className={`text-3xl font-black ${s.color}`}>{s.count}</div>
            <div className={`text-xs font-bold uppercase mt-1 ${s.color}`}>{s.label}</div>
          </div>
        ))}
      </div>

      {top_findings.length > 0 && (
        <>
          <h2 className="text-xl font-bold text-content mb-4">Top Findings</h2>
          <div className="space-y-4">
            {top_findings.map((f, i) => (
              <Card key={f.finding_id} className="p-4 flex gap-4">
                <div className="mt-1">
                  {f.severity === 'CRITICAL' || f.severity === 'HIGH' ? (
                    <AlertTriangle className="w-5 h-5 text-severity-critical-ink" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-severity-medium-ink" />
                  )}
                </div>
                <div className="flex-1">
                  <div className="font-bold text-content">{i + 1}. {f.title}</div>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-surface-2 border border-line">{f.severity}</span>
                    <span className="text-xs font-mono text-content-muted">{f.resource_id}</span>
                  </div>
                  <p className="text-sm text-content-secondary mt-3">{f.description}</p>
                  {f.recommendation && (
                    <div className="mt-3 p-3 rounded bg-surface-2 border border-line">
                      <div className="text-xs font-bold text-content mb-1">Recommendation</div>
                      <div className="text-sm text-content-secondary">{f.recommendation}</div>
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
