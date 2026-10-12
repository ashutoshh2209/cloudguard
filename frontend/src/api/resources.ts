import { fetchApi } from './client';

export interface CloudResourceItem {
  id: string;
  workspace_id?: string;
  aws_connection_id?: string;
  scan_id?: string;
  service: string;
  resource_type: string;
  resource_id: string;
  resource_name: string;
  name?: string;
  region: string;
  arn?: string;
  status: string;
  metadata?: Record<string, any>;
  details?: Record<string, any>;
  discovered_at: string;
  updated_at?: string;
}

export interface ResourceFilterParams {
  workspace_id?: string;
  scan_id?: string;
  service?: string;
  resource_type?: string;
  search?: string;
  skip?: number;
  limit?: number;
}

export interface DiscoveryResultItem {
  workspace_id?: string;
  aws_connection_id?: string;
  account_id?: string;
  resources_count: number;
  service_summary: Record<string, number>;
  service_errors: Record<string, string>;
  discovered_at: string;
}

export const resourcesApi = {
  listResources: (params: ResourceFilterParams = {}) => {
    const query = new URLSearchParams();
    if (params.workspace_id) query.append('workspace_id', params.workspace_id);
    if (params.scan_id) query.append('scan_id', params.scan_id);
    if (params.service && params.service !== 'all') query.append('service', params.service);
    if (params.resource_type) query.append('resource_type', params.resource_type);
    if (params.search) query.append('search', params.search);
    if (params.skip !== undefined) query.append('skip', params.skip.toString());
    if (params.limit !== undefined) query.append('limit', params.limit.toString());

    const queryString = query.toString() ? `?${query.toString()}` : '';
    return fetchApi<CloudResourceItem[]>(`/resources${queryString}`);
  },

  getResource: (id: string) => fetchApi<CloudResourceItem>(`/resources/${id}`),

  runDiscovery: (workspaceId: string) =>
    fetchApi<DiscoveryResultItem>('/discovery/run', {
      method: 'POST',
      body: JSON.stringify({ workspace_id: workspaceId }),
    }),
};
