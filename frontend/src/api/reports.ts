import { fetchApi } from './client';
import { SecurityReport, SecurityReportList, SecurityReportDetail } from '../types/api';

export const reportsApi = {
  listReports: (skip = 0, limit = 50, workspaceId?: string) => {
    const params = new URLSearchParams();
    params.append('skip', String(skip));
    params.append('limit', String(limit));
    if (workspaceId) params.append('workspace_id', workspaceId);
    return fetchApi<SecurityReportList>(`/reports?${params.toString()}`);
  },
    
  getReport: (reportId: string) => 
    fetchApi<SecurityReportDetail>(`/reports/${reportId}`),
    
  createReport: (scanId: string, workspaceId?: string, title?: string) => 
    fetchApi<SecurityReport>(`/reports`, {
      method: 'POST',
      body: JSON.stringify({ scan_id: scanId, workspace_id: workspaceId, title }),
    }),
    
  downloadReport: async (reportId: string) => {
    const token = localStorage.getItem('cloudguard_token');
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const API_URL = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
    
    const response = await fetch(`${API_URL}/reports/${reportId}/download`, {
      method: 'GET',
      headers,
    });
    
    if (!response.ok) {
      throw new Error(`Download failed: ${response.statusText}`);
    }
    
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cloudguard-security-report-${reportId}.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }
};
