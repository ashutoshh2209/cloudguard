import React, { useState, useEffect } from 'react';
import { Card } from './ui/Card';
import { Button } from './ui/Button';
import { Cloud, CheckCircle, AlertTriangle, XCircle, Loader2 } from 'lucide-react';
import { fetchApi } from '../api/client';
import { AWSConnectionStatus } from '../types/api';

export function AWSConnectionManager() {
  const [status, setStatus] = useState<AWSConnectionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [roleArn, setRoleArn] = useState('');
  const [region, setRegion] = useState('us-east-1');

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      setLoading(true);
      const data = await fetchApi<AWSConnectionStatus>('/aws/status');
      setStatus(data);
    } catch (err: any) {
      // If we get an error, assume not connected (unless 500)
      setStatus({ connected: false });
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsConnecting(true);
    setError(null);
    try {
      await fetchApi('/aws/connect', {
        method: 'POST',
        body: JSON.stringify({ role_arn: roleArn, region })
      });
      await loadStatus();
    } catch (err: any) {
      setError(err.message || 'Failed to connect to AWS');
    } finally {
      setIsConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    setIsConnecting(true);
    setError(null);
    try {
      await fetchApi('/aws/disconnect', { method: 'POST' });
      await loadStatus();
    } catch (err: any) {
      setError(err.message || 'Failed to disconnect');
    } finally {
      setIsConnecting(false);
    }
  };

  if (loading) {
    return (
      <Card className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 text-accent-9 animate-spin" />
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-bold text-content">AWS Accounts</h3>
          <p className="text-[14px] text-content-secondary">Connect and manage your AWS environments.</p>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-severity-critical/10 border border-severity-critical/30 rounded-lg flex items-start gap-3 text-severity-critical-ink">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <div className="text-sm">{error}</div>
        </div>
      )}

      {status?.connected ? (
        <div className="border border-line rounded-lg divide-y divide-line bg-surface-1">
          <div className="p-4 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-surface-2 border border-line flex items-center justify-center">
                <Cloud className="w-5 h-5 text-accent-9" />
              </div>
              <div>
                <div className="font-bold text-content flex items-center gap-2">
                  Connected AWS Account
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-severity-secure/10 text-severity-secure-ink border border-severity-secure/20">
                    Connected
                  </span>
                </div>
                <div className="text-[13px] text-content-muted font-mono mt-0.5">
                  Account ID: {status.account_id} | Region: {status.region}
                </div>
              </div>
            </div>
            <Button 
              variant="outline" 
              size="sm"
              onClick={handleDisconnect}
              disabled={isConnecting}
              className="text-severity-critical-ink border-severity-critical hover:bg-severity-critical hover:text-content-inverse"
            >
              {isConnecting ? 'Disconnecting...' : 'Disconnect'}
            </Button>
          </div>
          <div className="p-4 bg-surface-2 text-xs text-content-secondary font-mono break-all">
            Verified Identity: {status.identity_arn}
          </div>
        </div>
      ) : (
        <div className="border border-line rounded-lg p-6 bg-surface-1">
          <h4 className="text-md font-bold text-content mb-4 flex items-center gap-2">
            <XCircle className="w-4 h-4 text-content-muted" /> Not Connected
          </h4>
          <form onSubmit={handleConnect} className="space-y-4 max-w-md">
            <div>
              <label className="block text-[13px] font-bold text-content-secondary mb-1.5">
                IAM Role ARN
              </label>
              <input 
                type="text" 
                required
                value={roleArn}
                onChange={e => setRoleArn(e.target.value)}
                placeholder="arn:aws:iam::123456789012:role/CloudGuardAudit" 
                className="w-full bg-surface-2 border border-line rounded-lg px-3 py-2 text-[14px] text-content font-mono focus:outline-none focus:border-accent-9/50" 
              />
              <p className="text-xs text-content-muted mt-1">
                Role must have a trust policy allowing CloudGuard to assume it.
              </p>
            </div>
            <div>
              <label className="block text-[13px] font-bold text-content-secondary mb-1.5">
                Default Region
              </label>
              <input 
                type="text" 
                required
                value={region}
                onChange={e => setRegion(e.target.value)}
                placeholder="us-east-1" 
                className="w-full bg-surface-2 border border-line rounded-lg px-3 py-2 text-[14px] text-content focus:outline-none focus:border-accent-9/50" 
              />
            </div>
            <Button 
              type="submit" 
              variant="primary" 
              className="mt-2"
              disabled={isConnecting}
            >
              {isConnecting ? 'Connecting...' : 'Connect AWS Account'}
            </Button>
          </form>
        </div>
      )}
    </Card>
  );
}
