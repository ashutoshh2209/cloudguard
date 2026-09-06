import React, { useState, useEffect } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { DataTable } from '../components/ui/DataTable';
import { SeverityIndicator } from '../components/ui/SeverityIndicator';
import { Search, Filter, Download, Loader2, Cloud } from 'lucide-react';
import { fetchApi } from '../api/client';
import { SecurityScan } from '../types/api';

interface CloudResource {
  id: str;
  scan_id: str;
  resource_type: str;
  resource_id: str;
  resource_name: str;
  region: str;
  details: any;
}

export function Resources() {
  const [searchTerm, setSearchTerm] = useState('');
  const [resources, setResources] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadResources();
  }, []);

  const loadResources = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // First fetch the latest scan
      const scans = await fetchApi<SecurityScan[]>('/scans');
      if (!scans || scans.length === 0) {
        setResources([]);
        return;
      }
      
      // Sort to get latest
      scans.sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());
      const latestScan = scans[0];
      
      // Fetch resources for latest scan
      const data = await fetchApi<any[]>(`/resources?scan_id=${latestScan.id}`);
      setResources(data);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to load resources');
    } finally {
      setLoading(false);
    }
  };

  const columns: any[] = [
    {
      header: 'Status',
      cell: (item: any) => <SeverityIndicator severity={item.status || 'secure'} showLabel={false} />,
      className: 'w-16',
    },
    {
      header: 'Resource Name',
      cell: (item: any) => (
        <div>
          <div className="font-bold text-content">{item.resource_name || item.resource_id}</div>
          <div className="text-[12px] text-content-muted font-mono truncate max-w-[200px]">{item.resource_id}</div>
        </div>
      ),
    },
    {
      header: 'Service',
      cell: (item: any) => (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-surface-2 text-content-secondary border border-line">
          {item.resource_type}
        </span>
      ),
    },
    { header: 'Region', accessorKey: 'region', className: 'text-content-secondary' },
    { 
      header: 'Details', 
      cell: (item: any) => (
        <span className="text-content-muted text-[12px]">
          {item.details ? Object.keys(item.details).length + ' attributes' : 'N/A'}
        </span>
      ),
      className: 'text-content-secondary' 
    }
  ];

  const filteredData = resources.filter(r => 
    (r.resource_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (r.resource_id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (r.resource_type || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="h-full flex flex-col animate-in fade-in duration-300">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-content">Cloud Resources</h1>
          <p className="text-[14px] text-content-secondary mt-1">Inventory of all discovered assets in your cloud environment.</p>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 text-content-muted absolute left-3 top-1/2 -translate-y-1/2" />
            <input 
              type="text" 
              placeholder="Search resources..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full sm:w-64 bg-surface-1 border border-line rounded py-1.5 pl-9 pr-4 text-[13px] text-content placeholder:text-content-muted focus:outline-none focus:border-accent-9/50 shadow-sm transition-colors"
            />
          </div>
        </div>
      </div>

      <Card className="flex-1 p-0 overflow-hidden flex flex-col bg-surface-1">
        {loading ? (
          <div className="flex flex-1 items-center justify-center p-12">
            <Loader2 className="w-8 h-8 text-accent-9 animate-spin" />
          </div>
        ) : error ? (
          <div className="flex flex-1 flex-col items-center justify-center p-12 text-center">
            <div className="text-severity-critical-ink mb-2">Error loading resources</div>
            <div className="text-content-muted text-sm">{error}</div>
          </div>
        ) : resources.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center p-12 text-center max-w-sm mx-auto">
            <Cloud className="w-12 h-12 text-content-muted mb-4" />
            <div className="text-content font-bold mb-2">No resources found</div>
            <div className="text-content-muted text-sm">Run a security scan to discover resources in your connected AWS accounts.</div>
          </div>
        ) : (
          <DataTable data={filteredData} columns={columns} />
        )}
      </Card>
    </div>
  );
}
