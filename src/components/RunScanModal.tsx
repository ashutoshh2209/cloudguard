import React, { useState, useEffect } from 'react';
import { Shield, X, CheckCircle2, CircleDashed, AlertTriangle } from 'lucide-react';
import { Button } from './ui/Button';
import { fetchApi } from '../api/client';
import { AWSConnectionStatus, SecurityScan } from '../types/api';

interface RunScanModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function RunScanModal({ isOpen, onClose }: RunScanModalProps) {
  const [step, setStep] = useState<'configure' | 'scanning' | 'results'>('configure');
  const [awsStatus, setAwsStatus] = useState<AWSConnectionStatus | null>(null);
  const [scanResult, setScanResult] = useState<SecurityScan | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setStep('configure');
      setScanResult(null);
      setError(null);
      loadAwsStatus();
    }
  }, [isOpen]);

  const loadAwsStatus = async () => {
    try {
      const data = await fetchApi<AWSConnectionStatus>('/aws/status');
      setAwsStatus(data);
    } catch (err) {
      console.error(err);
    }
  };

  const startScan = async () => {
    if (!awsStatus?.account_id) return;
    setStep('scanning');
    setError(null);
    try {
      const result = await fetchApi<SecurityScan>(`/scans?account_id=${awsStatus.account_id}`, {
        method: 'POST'
      });
      setScanResult(result);
      setStep('results');
    } catch (err: any) {
      setError(err.message || 'Failed to run scan');
      setStep('configure');
    }
  };

  if (!isOpen) return null;

  return (
    <>
      <div 
        className="fixed inset-0 bg-black/60 z-50 transition-opacity backdrop-blur-sm"
        onClick={step === 'scanning' ? undefined : onClose}
      />
      
      <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[calc(100%-2rem)] max-w-[520px] bg-surface-1 border border-line rounded-xl z-50 shadow-elev-4 flex flex-col animate-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-line">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center">
              <Shield className="w-4 h-4 text-blue-600" />
            </div>
            <h2 className="text-[16px] font-bold text-content">Run security assessment</h2>
          </div>
          {step !== 'scanning' && (
            <button 
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded hover:bg-surface-2 text-content-muted hover:text-content-secondary transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Content */}
        <div className="p-4 md:p-6">
          
          {step === 'configure' && (
            <div className="space-y-6">
              {error && (
                <div className="p-3 bg-severity-critical/10 border border-severity-critical/30 rounded-lg text-sm text-severity-critical-ink">
                  {error}
                </div>
              )}
              <div>
                <label className="block text-[12px] font-bold text-content-muted uppercase tracking-wider mb-2">AWS Account</label>
                <div className="px-4 py-3 rounded-lg border border-line bg-surface-2 text-[14px] text-content font-medium flex items-center justify-between">
                  <span>{awsStatus?.account_id ? `Account: ${awsStatus.account_id}` : 'No AWS Account connected'}</span>
                </div>
              </div>

              <div>
                <label className="block text-[12px] font-bold text-content-muted uppercase tracking-wider mb-2">Services to scan</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {['S3', 'IAM', 'EC2', 'Security Groups', 'RDS', 'CloudTrail'].map(service => (
                    <label key={service} className="flex items-center gap-3 p-3 rounded-lg border border-line bg-surface-1 cursor-pointer hover:bg-surface-3">
                      <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-line-strong bg-surface-1 text-blue-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50 focus:ring-offset-0" />
                      <span className="text-[13px] text-content-secondary font-medium">{service}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-[12px] font-bold text-content-muted uppercase tracking-wider mb-2">Scan type</label>
                <div className="space-y-2">
                  <label className="flex items-center gap-3 p-3 rounded-lg border border-line bg-surface-3 cursor-pointer">
                    <input type="radio" name="scanType" defaultChecked className="w-4 h-4 bg-transparent border-line-strong text-blue-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50 focus:ring-offset-0" />
                    <div>
                      <div className="text-[13px] text-content font-bold">Quick assessment</div>
                      <div className="text-[12px] text-content-muted">Checks high-risk misconfigurations only (est. 30s)</div>
                    </div>
                  </label>
                  <label className="flex items-center gap-3 p-3 rounded-lg border border-transparent hover:border-line cursor-pointer transition-colors">
                    <input type="radio" name="scanType" className="w-4 h-4 bg-transparent border-line-strong text-blue-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50 focus:ring-offset-0" />
                    <div>
                      <div className="text-[13px] text-content-secondary font-bold">Full assessment</div>
                      <div className="text-[12px] text-content-muted">Complete CIS compliance check (est. 4m)</div>
                    </div>
                  </label>
                </div>
              </div>
            </div>
          )}

          {step === 'scanning' && (
            <div className="py-8 space-y-8">
              <div className="flex flex-col items-center justify-center text-center">
                <div className="relative w-16 h-16 mb-6">
                  <svg className="absolute inset-0 w-full h-full -rotate-90 animate-spin" viewBox="0 0 100 100" style={{ animationDuration: '3s' }}>
                    <circle cx="50" cy="50" r="46" fill="none" stroke="currentColor" strokeWidth="4" className="text-white/5" />
                    <circle 
                      cx="50" cy="50" r="46" fill="none" stroke="currentColor" strokeWidth="4" 
                      strokeDasharray="289 289"
                      strokeDashoffset={289 - (289 * 0.25)}
                      className="text-blue-500"
                    />
                  </svg>
                </div>
                <h3 className="text-lg font-bold text-content">Running backend scan...</h3>
                <p className="text-[13px] text-content-muted mt-1">Please keep this window open while the backend analyzes your resources.</p>
              </div>

              <div className="max-w-xs mx-auto space-y-4">
                <div className="flex items-center gap-3">
                  <CircleDashed className="w-4 h-4 text-blue-600 animate-spin flex-shrink-0" />
                  <span className="text-[13px] text-content font-bold">Discovering resources & analyzing rules</span>
                </div>
              </div>
            </div>
          )}

          {step === 'results' && scanResult && (
            <div className="py-8 flex flex-col items-center text-center">
              <div className="w-16 h-16 rounded-full bg-green-50 border border-green-200 flex items-center justify-center mb-6 shadow-sm">
                <CheckCircle2 className="w-8 h-8 text-green-600" />
              </div>
              <h3 className="text-2xl font-bold text-content mb-2">Scan completed</h3>
              <p className="text-[14px] text-content-muted mb-8 font-medium">Checks run: {scanResult.summary.checks_completed}</p>
              
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full mb-8">
                <div className="p-4 rounded-xl bg-surface-1 border border-line shadow-sm hover-lift relative overflow-hidden group">
                  <div className="absolute inset-0 bg-surface-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                  <div className="text-[28px] font-bold text-content">{scanResult.summary.resources_scanned}</div>
                  <div className="text-[11px] font-bold text-content-muted uppercase tracking-wider mt-1">Resources</div>
                </div>
                <div className="p-4 rounded-xl bg-surface-1 border border-line shadow-sm hover-lift relative overflow-hidden group">
                  <div className="absolute inset-0 bg-orange-50 opacity-0 group-hover:opacity-100 transition-opacity" />
                  <div className="text-[28px] font-bold text-orange-600">{scanResult.summary.checks_failed}</div>
                  <div className="text-[11px] font-bold text-orange-500 uppercase tracking-wider mt-1">Failed Checks</div>
                </div>
                <div className="p-4 rounded-xl bg-blue-50 border border-blue-200 shadow-sm hover-lift relative overflow-hidden group">
                  <div className="absolute inset-0 bg-blue-100/50 opacity-0 group-hover:opacity-100 transition-opacity" />
                  <div className="text-[28px] font-bold text-blue-700">{scanResult.security_score || 'N/A'}</div>
                  <div className="text-[11px] font-bold text-blue-600 uppercase tracking-wider mt-1">Score</div>
                </div>
              </div>
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-surface-2 border-t border-line rounded-b-xl flex flex-col-reverse sm:flex-row justify-end gap-3">
          {step === 'configure' && (
            <>
              <Button variant="ghost" onClick={onClose}>Cancel</Button>
              <Button variant="primary" onClick={startScan} disabled={!awsStatus?.account_id}>Start Scan</Button>
            </>
          )}
          {step === 'results' && (
            <Button variant="primary" onClick={onClose} className="w-full">View Findings</Button>
          )}
        </div>

      </div>
    </>
  );
}
