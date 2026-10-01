import { fetchApi } from './client';
import { FindingExplanation, ScanAISummary, CopilotRequest, CopilotResponse } from '../types/api';

export const aiApi = {
  explainFinding: (findingId: string) => 
    fetchApi<FindingExplanation>(`/ai/findings/${findingId}/explain`, { method: 'POST' }),
    
  summarizeScan: (scanId: string) => 
    fetchApi<ScanAISummary>(`/ai/scans/${scanId}/summary`, { method: 'POST' }),
    
  askCopilot: (request: CopilotRequest) => 
    fetchApi<CopilotResponse>('/ai/chat', { 
      method: 'POST',
      body: JSON.stringify(request)
    })
};
