import React, { useState, useEffect, useCallback } from 'react';
import { Card } from './ui/Card';
import { Button } from './ui/Button';
import { Cloud, CheckCircle, AlertTriangle, XCircle, Loader2, RefreshCw, ShieldCheck } from 'lucide-react';
import { awsApi, AWSConnectionItem } from '../api/aws';
import { useAuth } from '../context/AuthContext';

export function AWSConnectionManager() {
  const { activeWorkspace } = useAuth();
  const [connections, setConnections] = useState<AWSConnectionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [isActionPending, setIsActionPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Form State
  const [roleArn, setRoleArn] = useState('');
  const [region, setRegion] = useState('us-east-1');
  const [externalId, setExternalId] = useState('');

  const isViewer = activeWorkspace?.role === 'VIEWER';

  const loadConnections = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      if (activeWorkspace) {
        const list = await awsApi.listConnections(activeWorkspace.id);
        setConnections(list || []);
      } else {
        // Fallback to general list if no active workspace selected
        const list = await awsApi.listConnections();
        setConnections(list || []);
      }
    } catch (err: any) {
      // If endpoint returns error or empty, check legacy fallback
      try {
        const legacy = await awsApi.getLegacyStatus();
        if (legacy && legacy.connected) {
          setConnections([
            {
              id: 'legacy-active',
              account_id: legacy.account_id || 'Unknown',
              role_arn: legacy.identity_arn || 'Configured via STS',
              region: legacy.region || 'us-east-1',
              status: 'CONNECTED',
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              last_verified_at: new Date().toISOString(),
            },
          ]);
        } else {
          setConnections([]);
        }
      } catch {
        setConnections([]);
      }
    } finally {
      setLoading(false);
    }
  }, [activeWorkspace]);

  useEffect(() => {
    loadConnections();
  }, [loadConnections]);

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace) {
      setError('Please select or create an active workspace first');
      return;
    }

    setIsActionPending(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await awsApi.createConnection({
        workspace_id: activeWorkspace.id,
        role_arn: roleArn.trim(),
        region: region.trim(),
        external_id: externalId.trim() ? externalId.trim() : null,
      });
      setSuccessMessage('AWS account connected and verified successfully via AWS STS AssumeRole!');
      setRoleArn('');
      setExternalId('');
      await loadConnections();
    } catch (err: any) {
      setError(err.message || 'Failed to connect AWS account. Please check the IAM role ARN, trust policy, and region.');
    } finally {
      setIsActionPending(false);
    }
  };

  const handleVerify = async (connectionId: string) => {
    setIsActionPending(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await awsApi.verifyConnection(connectionId);
      setSuccessMessage('AWS IAM Role assumption re-verified successfully via STS.');
      await loadConnections();
    } catch (err: any) {
      setError(err.message || 'Failed to re-verify AWS STS AssumeRole. Check trust policy permissions.');
      await loadConnections();
    } finally {
      setIsActionPending(false);
    }
  };

  const handleDisconnect = async (connectionId: string) => {
    if (!confirm('Are you sure you want to disconnect this AWS account? Active scans will not be able to assume this role.')) {
      return;
    }

    setIsActionPending(true);
    setError(null);
    setSuccessMessage(null);

    try {
      if (connectionId === 'legacy-active') {
        await awsApi.legacyDisconnect();
      } else {
        await awsApi.deleteConnection(connectionId);
      }
      setSuccessMessage('AWS connection removed and temporary credentials purged.');
      await loadConnections();
    } catch (err: any) {
      setError(err.message || 'Failed to disconnect AWS account');
    } finally {
      setIsActionPending(false);
    }
  };

  if (loading) {
    return (
      <Card className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 text-accent-9 animate-spin" />
      </Card>
    );
  }

  const activeConnection = connections.length > 0 ? connections[0] : null;

  return (
    <Card>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-bold text-content">AWS Accounts</h3>
          <p className="text-[14px] text-content-secondary">
            Connect and manage AWS environments for workspace{' '}
            <span className="font-semibold text-content">{activeWorkspace?.name || 'Default'}</span> using secure IAM Role STS AssumeRole.
          </p>
        </div>
        {isViewer && (
          <span className="inline-flex items-center px-2.5 py-1 rounded text-xs font-medium bg-surface-2 text-content-muted border border-line">
            Read-only (Viewer)
          </span>
        )}
      </div>

      {error && (
        <div className="mb-6 p-4 bg-severity-critical/10 border border-severity-critical/30 rounded-lg flex items-start gap-3 text-severity-critical-ink">
          <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="text-sm">{error}</div>
        </div>
      )}

      {successMessage && (
        <div className="mb-6 p-4 bg-severity-secure/10 border border-severity-secure/30 rounded-lg flex items-start gap-3 text-severity-secure-ink">
          <CheckCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="text-sm">{successMessage}</div>
        </div>
      )}

      {activeConnection ? (
        <div className="border border-line rounded-lg divide-y divide-line bg-surface-1">
          <div className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-surface-2 border border-line flex items-center justify-center shrink-0">
                <Cloud className="w-5 h-5 text-accent-9" />
              </div>
              <div>
                <div className="font-bold text-content flex items-center gap-2">
                  Connected AWS Account
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                      activeConnection.status === 'CONNECTED'
                        ? 'bg-severity-secure/10 text-severity-secure-ink border border-severity-secure/20'
                        : 'bg-severity-critical/10 text-severity-critical-ink border border-severity-critical/20'
                    }`}
                  >
                    {activeConnection.status}
                  </span>
                </div>
                <div className="text-[13px] text-content-muted font-mono mt-0.5">
                  Account ID: <span className="text-content font-bold">{activeConnection.account_id}</span> | Region: {activeConnection.region}
                </div>
                <div className="text-xs text-content-muted mt-1">
                  Last verified: {activeConnection.last_verified_at ? new Date(activeConnection.last_verified_at).toLocaleString() : 'Just now'}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleVerify(activeConnection.id)}
                disabled={isActionPending || isViewer}
                className="flex items-center gap-1.5"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isActionPending ? 'animate-spin' : ''}`} />
                Verify
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleDisconnect(activeConnection.id)}
                disabled={isActionPending || isViewer}
                className="text-severity-critical-ink border-severity-critical hover:bg-severity-critical hover:text-content-inverse"
              >
                Disconnect
              </Button>
            </div>
          </div>

          <div className="p-4 bg-surface-2 text-xs text-content-secondary font-mono break-all flex flex-col gap-1">
            <div>
              <span className="text-content-muted">Role ARN:</span> {activeConnection.role_arn}
            </div>
            {activeConnection.external_id && (
              <div>
                <span className="text-content-muted">External ID:</span> {activeConnection.external_id}
              </div>
            )}
            <div className="text-[11px] text-severity-secure-ink flex items-center gap-1 mt-1">
              <ShieldCheck className="w-3.5 h-3.5" />
              Credentials assumed securely in-memory via AWS STS; no static access keys stored.
            </div>
          </div>
        </div>
      ) : (
        <div className="border border-line rounded-lg p-6 bg-surface-1">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-md font-bold text-content flex items-center gap-2">
              <XCircle className="w-4 h-4 text-content-muted" /> Not Connected
            </h4>
          </div>

          {isViewer ? (
            <p className="text-sm text-content-muted">
              No AWS account connected to this workspace. Contact a workspace Admin or Owner to configure AWS integration.
            </p>
          ) : (
            <form onSubmit={handleConnect} className="space-y-4 max-w-lg">
              <div>
                <label className="block text-[13px] font-bold text-content-secondary mb-1.5">
                  IAM Role ARN
                </label>
                <input
                  type="text"
                  required
                  value={roleArn}
                  onChange={(e) => setRoleArn(e.target.value)}
                  placeholder="arn:aws:iam::123456789012:role/CloudGuardAuditRole"
                  className="w-full bg-surface-2 border border-line rounded-lg px-3 py-2 text-[14px] text-content font-mono focus:outline-none focus:border-accent-9/50"
                />
                <p className="text-xs text-content-muted mt-1">
                  Format: <code className="text-accent-9">arn:aws:iam::12-digit-account-id:role/RoleName</code>. CloudGuard will assume this role using AWS STS.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[13px] font-bold text-content-secondary mb-1.5">
                    Default Region
                  </label>
                  <select
                    value={region}
                    onChange={(e) => setRegion(e.target.value)}
                    className="w-full bg-surface-2 border border-line rounded-lg px-3 py-2 text-[14px] text-content focus:outline-none focus:border-accent-9/50"
                  >
                    <option value="us-east-1">us-east-1 (N. Virginia)</option>
                    <option value="us-east-2">us-east-2 (Ohio)</option>
                    <option value="us-west-1">us-west-1 (N. California)</option>
                    <option value="us-west-2">us-west-2 (Oregon)</option>
                    <option value="ap-south-1">ap-south-1 (Mumbai)</option>
                    <option value="ap-southeast-1">ap-southeast-1 (Singapore)</option>
                    <option value="ap-northeast-1">ap-northeast-1 (Tokyo)</option>
                    <option value="eu-west-1">eu-west-1 (Ireland)</option>
                    <option value="eu-central-1">eu-central-1 (Frankfurt)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[13px] font-bold text-content-secondary mb-1.5">
                    External ID (Optional)
                  </label>
                  <input
                    type="text"
                    value={externalId}
                    onChange={(e) => setExternalId(e.target.value)}
                    placeholder="Optional external ID"
                    className="w-full bg-surface-2 border border-line rounded-lg px-3 py-2 text-[14px] text-content focus:outline-none focus:border-accent-9/50"
                  />
                </div>
              </div>

              <div className="p-3 bg-surface-2/60 border border-line/60 rounded-md text-xs text-content-secondary space-y-1">
                <div className="font-semibold text-content flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-accent-9" /> Zero Static Secrets
                </div>
                <p>
                  CloudGuard never asks for access keys or secrets. Role assumption uses AWS STS temporary credentials kept only in backend volatile memory.
                </p>
              </div>

              <Button
                type="submit"
                variant="primary"
                className="mt-2"
                disabled={isActionPending || !roleArn}
              >
                {isActionPending ? 'Connecting & Verifying via STS...' : 'Connect AWS Account'}
              </Button>
            </form>
          )}
        </div>
      )}
    </Card>
  );
}
