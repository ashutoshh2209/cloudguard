import { fetchApi } from './client';
import { Finding } from '../types/api';

export interface FindingFilterParams {
  workspace_id?: string;
  scan_id?: string;
  severity?: string;
  priority?: string;
  service?: string;
  status?: string;
  skip?: number;
  limit?: number;
}

export const findingsApi = {
  list: async (params?: FindingFilterParams): Promise<Finding[]> => {
    const query = new URLSearchParams();
    if (params?.workspace_id) query.append('workspace_id', params.workspace_id);
    if (params?.scan_id) query.append('scan_id', params.scan_id);
    if (params?.severity) query.append('severity', params.severity);
    if (params?.priority) query.append('priority', params.priority);
    if (params?.service) query.append('service', params.service);
    if (params?.status) query.append('status', params.status);
    if (params?.skip !== undefined) query.append('skip', params.skip.toString());
    if (params?.limit !== undefined) query.append('limit', params.limit.toString());

    const qs = query.toString();
    return fetchApi<Finding[]>(`/findings${qs ? `?${qs}` : ''}`);
  },

  get: async (findingId: string): Promise<Finding> => {
    return fetchApi<Finding>(`/findings/${findingId}`);
  },

  updateStatus: async (findingId: string, status: 'OPEN' | 'RESOLVED' | 'IGNORED'): Promise<Finding> => {
    return fetchApi<Finding>(`/findings/${findingId}?status=${status}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  },
};
