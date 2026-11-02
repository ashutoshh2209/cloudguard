export interface ScanSummary {
  resources_scanned: number;
  checks_attempted: number;
  checks_completed: number;
  checks_failed: number;
  checks_passed?: number;
  checks_errored?: number;
  findings?: number;
  critical?: number;
  high?: number;
  medium?: number;
  low?: number;
  info?: number;
}

export interface SecurityScan {
  id: string;
  scan_id?: string;
  workspace_id?: string;
  status: 'PENDING' | 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'PARTIAL';
  started_at: string;
  completed_at?: string;
  created_at?: string;
  aws_connection_id?: string;
  account_id?: string;
  summary: ScanSummary;
  coverage_percentage: number;
  security_score?: number;
  security_rating?: string;
  category_scores?: Record<string, CategoryScore>;
  is_simulated?: boolean;
  scan_type?: string;
}

export interface ScoreTrendPoint {
  scan_id: string;
  date: string;
  timestamp: string;
  score: number;
  rating?: string;
}

export interface Finding {
  finding_id: string;
  id?: string;
  workspace_id?: string;
  scan_id?: string;
  rule_id: string;
  title: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  category: string;
  service?: string;
  region?: string;
  resource_id: string;
  status: 'OPEN' | 'RESOLVED' | 'IGNORED';
  risk_score: number;
  priority?: string;
  description?: string;
  recommendation?: string;
  evidence?: Record<string, any>;
  risk_factors?: string[];
  is_simulated?: boolean;
  source_label?: string;
  created_at?: string;
  detected_at?: string;
  updated_at?: string;
}

export interface CloudResource {
  id: string;
  resource_id: string;
  resource_type: string;
  service: string;
  region: string;
  status: string;
  discovered_at: string;
}

export interface TopRiskFinding {
  finding_id: string;
  title: string;
  severity: string;
  risk_score: number;
  priority: string;
  resource_name: string;
}

export interface CategoryScore {
  score: number;
  status: string;
  findings: number;
  critical: number;
  high: number;
}

export interface CheckSummary {
  passed: number;
  failed: number;
  errors: number;
  skipped: number;
}

export interface DashboardSummary {
  security_score?: number;
  rating: string;
  reason?: string;
  total_resources?: number;
  total_findings?: number;
  findings_summary: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    info: number;
  };
  checks_summary?: CheckSummary;
  category_scores: Record<string, CategoryScore>;
  top_risks: TopRiskFinding[];
  latest_scan_id?: string;
  latest_scan_status?: string;
  last_scanned_at?: string;
  previous_score?: number;
  score_delta?: number;
  score_trend?: ScoreTrendPoint[];
  is_simulated?: boolean;
  scan_mode?: string;
}

export interface AWSConnectionStatus {
  connected: boolean;
  account_id?: string;
  region?: string;
  identity_arn?: string;
  message?: string;
}

export interface SecurityReport {
  id: string;
  scan_id: string;
  report_type: string;
  status: string;
  title: string;
  security_score: number | null;
  security_rating: string | null;
  finding_count: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  info_count: number;
  resource_count: number;
  coverage_percentage: number;
  generated_at: string;
  created_at: string;
}

export interface SecurityReportList {
  items: SecurityReport[];
  total: number;
}

export interface SecurityReportDetail {
  report: SecurityReport;
  executive_summary: {
    summary_text: string;
  };
  security_posture: {
    score: number | null;
    rating: string | null;
    coverage: number;
    status: string;
  };
  category_scores: any[];
  finding_summary: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    info: number;
  };
  top_findings: Finding[];
}

export interface FindingExplanation {
  summary: string;
  why_it_matters: string;
  potential_impact?: string | null;
  attack_scenario: string | null;
  recommended_actions: string[];
  caveats: string[];
}

export interface ScanAISummary {
  summary: string;
  key_risks: string[];
  recommended_actions: string[];
  observations: string[];
  caveats: string[];
}

export interface CopilotMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface CopilotRequest {
  message: string;
  scan_id?: string | null;
  workspace_id?: string | null;
  history: CopilotMessage[];
}

export interface CopilotResponse {
  answer: string;
  provider?: string;
  scan_id?: string | null;
  status?: string;
}
