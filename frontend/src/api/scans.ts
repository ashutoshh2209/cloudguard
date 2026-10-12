import { fetchApi } from './client';
import { SecurityScan } from '../types/api';

export interface CheckResultItem {
  id: string;
  scan_id: string;
  resource_id: string;
  rule_id: string;
  status: 'PASS' | 'FAIL' | 'ERROR' | 'NOT_APPLICABLE';
  message?: string;
  error_message?: string;
  recommendation?: string;
  evidence?: Record<string, any>;
  checked_at?: string;
}

export interface ScanDetailResponse extends SecurityScan {
  check_results?: CheckResultItem[];
  findings?: any[];
}

export const scansApi = {
  listScans: async (params?: { workspace_id?: string; status?: string; skip?: number; limit?: number }): Promise<SecurityScan[]> => {
    const searchParams = new URLSearchParams();
    if (params?.workspace_id) searchParams.append('workspace_id', params.workspace_id);
    if (params?.status) searchParams.append('status', params.status);
    if (params?.skip !== undefined) searchParams.append('skip', String(params.skip));
    if (params?.limit !== undefined) searchParams.append('limit', String(params.limit));
    const qs = searchParams.toString();
    return fetchApi<SecurityScan[]>(`/scans${qs ? `?${qs}` : ''}`);
  },

  getScan: async (scanId: string): Promise<ScanDetailResponse> => {
    return fetchApi<ScanDetailResponse>(`/scans/${scanId}`);
  },

  runScan: async (params: { workspace_id?: string; account_id?: string; aws_connection_id?: string }): Promise<ScanDetailResponse> => {
    return fetchApi<ScanDetailResponse>('/scans/', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  getScanChecks: async (scanId: string, status?: string): Promise<CheckResultItem[]> => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : '';
    return fetchApi<CheckResultItem[]>(`/scans/${scanId}/checks${qs}`);
  },
};
