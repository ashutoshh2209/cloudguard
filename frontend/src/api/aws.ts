import { fetchApi } from './client';

export interface AWSConnectionItem {
  id: string;
  workspace_id?: string;
  account_id: string;
  role_arn: string;
  external_id?: string | null;
  region: string;
  status: string;
  created_at: string;
  updated_at: string;
  last_verified_at: string;
}

export interface AWSConnectionCreateInput {
  workspace_id: string;
  role_arn: string;
  region: string;
  external_id?: string | null;
}

export interface AWSConnectionDeleteResponse {
  id: string;
  message: string;
}

export const awsApi = {
  listConnections: (workspaceId?: string) => {
    const query = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : '';
    return fetchApi<AWSConnectionItem[]>(`/aws/connections${query}`);
  },

  getConnection: (connectionId: string) =>
    fetchApi<AWSConnectionItem>(`/aws/connections/${connectionId}`),

  createConnection: (input: AWSConnectionCreateInput) =>
    fetchApi<AWSConnectionItem>('/aws/connections', {
      method: 'POST',
      body: JSON.stringify(input),
    }),

  verifyConnection: (connectionId: string) =>
    fetchApi<AWSConnectionItem>(`/aws/connections/${connectionId}/verify`, {
      method: 'POST',
    }),

  deleteConnection: (connectionId: string) =>
    fetchApi<AWSConnectionDeleteResponse>(`/aws/connections/${connectionId}`, {
      method: 'DELETE',
    }),

  // Legacy fallback support
  getLegacyStatus: () => fetchApi<{ connected: boolean; account_id?: string; region?: string; identity_arn?: string; message?: string }>('/aws/status'),
  legacyConnect: (role_arn: string, region: string) =>
    fetchApi('/aws/connect', {
      method: 'POST',
      body: JSON.stringify({ role_arn, region }),
    }),
  legacyDisconnect: () =>
    fetchApi('/aws/disconnect', { method: 'POST' }),
};
