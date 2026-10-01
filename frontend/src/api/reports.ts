import { fetchApi } from './client';
import { SecurityReport, SecurityReportList, SecurityReportDetail } from '../types/api';

export const reportsApi = {
  listReports: (skip = 0, limit = 50) => 
    fetchApi<SecurityReportList>(`/reports?skip=${skip}&limit=${limit}`),
    
  getReport: (reportId: string) => 
    fetchApi<SecurityReportDetail>(`/reports/${reportId}`),
    
  createReport: (scanId: string) => 
    fetchApi<SecurityReport>(`/reports?scan_id=${scanId}`, { method: 'POST' }),
    
  downloadReport: async (reportId: string) => {
    // We cannot use the standard fetchApi because it expects JSON, but this is a binary PDF.
    const token = localStorage.getItem('cloudguard_token');
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    // Assumes API_URL is accessible like in client.ts
    const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';
    
    const response = await fetch(`${API_URL}/reports/${reportId}/download`, {
      method: 'GET',
      headers
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
