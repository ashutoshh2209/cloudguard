import React, { useState, useEffect, useCallback } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { DataTable } from '../components/ui/DataTable';
import { SeverityIndicator } from '../components/ui/SeverityIndicator';
import { Search, Loader2, Cloud, RefreshCw, AlertTriangle, CheckCircle, Database, Server, Key, Shield, Layers } from 'lucide-react';
import { resourcesApi, CloudResourceItem } from '../api/resources';
import { fetchApi } from '../api/client';
import { SecurityScan } from '../types/api';
import { useAuth } from '../context/AuthContext';

const SERVICE_TABS = [
  { id: 'all', label: 'All Services' },
  { id: 'ec2', label: 'EC2' },
  { id: 's3', label: 'S3' },
  { id: 'iam', label: 'IAM' },
  { id: 'rds', label: 'RDS' },
  { id: 'cloudtrail', label: 'CloudTrail' },
];

export function Resources() {
  const { activeWorkspace } = useAuth();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedService, setSelectedService] = useState('all');
  const [resources, setResources] = useState<CloudResourceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const isViewer = activeWorkspace?.role === 'VIEWER';

  const loadResources = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      let data: CloudResourceItem[] = [];

      // 1. If active workspace is present, query real workspace resources
      if (activeWorkspace) {
        data = await resourcesApi.listResources({
          workspace_id: activeWorkspace.id,
          service: selectedService !== 'all' ? selectedService : undefined,
        });
      }

      // 2. If no workspace resources found, check latest scan as fallback
      if ((!data || data.length === 0) && !activeWorkspace) {
        try {
          const scans = await fetchApi<SecurityScan[]>('/scans');
          if (scans && scans.length > 0) {
            scans.sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());
            const latestScan = scans[0];
            data = await resourcesApi.listResources({ scan_id: latestScan.id });
          }
        } catch {
          // ignore scan fallback error
        }
      }

      setResources(data || []);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to load resources');
      setResources([]);
    } finally {
      setLoading(false);
    }
  }, [activeWorkspace, selectedService]);

  useEffect(() => {
    loadResources();
  }, [loadResources]);

  const handleRunDiscovery = async () => {
    if (!activeWorkspace) {
      setError('Please select an active workspace first');
      return;
    }

    try {
      setIsDiscovering(true);
      setError(null);
      setSuccessMessage(null);

      const result = await resourcesApi.runDiscovery(activeWorkspace.id);
      
      let msg = `Discovered ${result.resources_count} AWS assets across EC2, S3, IAM, Security Groups, RDS, and CloudTrail!`;
      if (result.service_errors && Object.keys(result.service_errors).length > 0) {
        msg += ` (Note: ${Object.keys(result.service_errors).join(', ')} reported access limits)`;
      }
      setSuccessMessage(msg);
      await loadResources();
    } catch (err: any) {
      setError(err.message || 'Resource discovery failed. Ensure an AWS account is connected to this workspace.');
    } finally {
      setIsDiscovering(false);
    }
  };

  const getServiceIcon = (service: string) => {
    switch (service.toLowerCase()) {
      case 'ec2':
        return <Server className="w-3.5 h-3.5" />;
      case 's3':
        return <Database className="w-3.5 h-3.5" />;
      case 'iam':
        return <Key className="w-3.5 h-3.5" />;
      case 'rds':
        return <Database className="w-3.5 h-3.5 text-accent-9" />;
      case 'cloudtrail':
        return <Shield className="w-3.5 h-3.5" />;
      default:
        return <Layers className="w-3.5 h-3.5" />;
    }
  };

  const columns: any[] = [
    {
      header: 'Status',
      cell: (item: CloudResourceItem) => (
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
            item.status === 'running' || item.status === 'active' || item.status === 'available'
              ? 'bg-severity-secure/10 text-severity-secure-ink border border-severity-secure/20'
              : 'bg-surface-2 text-content-muted border border-line'
          }`}
        >
          {item.status || 'active'}
        </span>
      ),
      className: 'w-24',
    },
    {
      header: 'Resource Name',
      cell: (item: CloudResourceItem) => (
        <div>
          <div className="font-bold text-content">{item.resource_name || item.name || item.resource_id}</div>
          <div className="text-[12px] text-content-muted font-mono truncate max-w-[260px]">{item.resource_id}</div>
        </div>
      ),
    },
    {
      header: 'Service / Type',
      cell: (item: CloudResourceItem) => (
        <div className="flex items-center gap-1.5">
          {getServiceIcon(item.service)}
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-surface-2 text-content-secondary border border-line">
            {item.resource_type}
          </span>
        </div>
      ),
    },
    {
      header: 'Region',
      cell: (item: CloudResourceItem) => (
        <span className="text-[13px] text-content-secondary font-mono">{item.region}</span>
      ),
      className: 'w-28',
    },
    {
      header: 'Attributes',
      cell: (item: CloudResourceItem) => {
        const meta = item.metadata || item.details || {};
        const count = Object.keys(meta).length;
        return (
          <span className="text-content-muted text-[12px]">
            {count > 0 ? `${count} attributes` : 'Standard'}
          </span>
        );
      },
      className: 'text-content-secondary w-28',
    },
    {
      header: 'Discovered',
      cell: (item: CloudResourceItem) => (
        <span className="text-content-muted text-[12px]">
          {item.discovered_at ? new Date(item.discovered_at).toLocaleDateString() : 'N/A'}
        </span>
      ),
      className: 'text-content-secondary w-28',
    },
  ];

  const filteredData = resources.filter((r) => {
    const matchesSearch =
      (r.resource_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (r.name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (r.resource_id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (r.resource_type || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (r.arn || '').toLowerCase().includes(searchTerm.toLowerCase());

    const matchesService =
      selectedService === 'all' ||
      r.service.toLowerCase() === selectedService.toLowerCase();

    return matchesSearch && matchesService;
  });

  return (
    <div className="h-full flex flex-col animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-content">Cloud Resources</h1>
          <p className="text-[14px] text-content-secondary mt-1">
            Live inventory of assets discovered across EC2, S3, IAM, Security Groups, RDS, and CloudTrail for{' '}
            <span className="font-semibold text-content">{activeWorkspace?.name || 'Default Workspace'}</span>.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="primary"
            onClick={handleRunDiscovery}
            disabled={isDiscovering || isViewer}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${isDiscovering ? 'animate-spin' : ''}`} />
            {isDiscovering ? 'Discovering...' : 'Discover Assets'}
          </Button>
        </div>
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

      {/* Filter Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div className="flex flex-wrap items-center gap-1.5 bg-surface-1 border border-line p-1 rounded-lg">
          {SERVICE_TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSelectedService(tab.id)}
              className={`px-3 py-1.5 rounded text-xs font-semibold transition-colors ${
                selectedService === tab.id
                  ? 'bg-accent-9 text-content-inverse'
                  : 'text-content-secondary hover:text-content hover:bg-surface-2'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="relative">
          <Search className="w-4 h-4 text-content-muted absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search name, ID, or ARN..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full sm:w-64 bg-surface-1 border border-line rounded py-1.5 pl-9 pr-4 text-[13px] text-content placeholder:text-content-muted focus:outline-none focus:border-accent-9/50 shadow-sm transition-colors"
          />
        </div>
      </div>

      <Card className="flex-1 p-0 overflow-hidden flex flex-col bg-surface-1">
        {loading ? (
          <div className="flex flex-1 flex-col items-center justify-center p-12">
            <Loader2 className="w-8 h-8 text-accent-9 animate-spin mb-3" />
            <div className="text-sm text-content-secondary">Loading cloud inventory...</div>
          </div>
        ) : error && resources.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center p-12 text-center">
            <AlertTriangle className="w-10 h-10 text-severity-critical-ink mb-3" />
            <div className="text-severity-critical-ink font-bold mb-1">Error Loading Resources</div>
            <div className="text-content-muted text-sm mb-4">{error}</div>
            <Button variant="outline" size="sm" onClick={loadResources}>
              Retry
            </Button>
          </div>
        ) : filteredData.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center p-12 text-center max-w-sm mx-auto">
            <Cloud className="w-12 h-12 text-content-muted mb-4" />
            <div className="text-content font-bold mb-1">No resources found</div>
            <p className="text-content-muted text-sm mb-4">
              {resources.length === 0
                ? 'No resources discovered in this workspace yet. Connect an AWS account in Settings and click "Discover Assets".'
                : 'No resources match the selected filters or search query.'}
            </p>
            {resources.length === 0 && !isViewer && (
              <Button variant="outline" size="sm" onClick={handleRunDiscovery} disabled={isDiscovering}>
                Discover Assets Now
              </Button>
            )}
          </div>
        ) : (
          <DataTable data={filteredData} columns={columns} />
        )}
      </Card>
    </div>
  );
}
