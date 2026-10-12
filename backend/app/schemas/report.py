from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

class SecurityReportBase(BaseModel):
    title: str
    scan_id: str

class SecurityReportCreate(BaseModel):
    scan_id: str
    workspace_id: Optional[str] = None
    title: Optional[str] = None

class SecurityReportResponse(SecurityReportBase):
    id: str
    workspace_id: Optional[str] = None
    aws_connection_id: Optional[str] = None
    report_type: str
    status: str
    
    security_score: Optional[int] = None
    security_rating: Optional[str] = None
    
    finding_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    
    resource_count: int
    coverage_percentage: Union[float, int] = 0
    
    generated_at: datetime
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class SecurityReportList(BaseModel):
    items: List[SecurityReportResponse]
    total: int

class ExecutiveSummary(BaseModel):
    summary_text: str
    security_score: Optional[int] = None
    rating: Optional[str] = None
    key_highlights: List[str] = []

class SecurityPosture(BaseModel):
    score: Optional[int] = None
    rating: Optional[str] = None
    coverage: Union[float, int] = 0
    status: str

class FindingSummary(BaseModel):
    critical: int
    high: int
    medium: int
    low: int
    info: int

class ReportFindingItem(BaseModel):
    finding_id: str
    rule_id: str
    title: str
    severity: str
    service: str = "aws"
    resource_id: str
    category: str
    description: Optional[str] = None
    recommendation: Optional[str] = None
    status: str = "OPEN"
    risk_score: int = 0
    priority: str = "P4"
    detected_at: Optional[str] = None

class ReportCategoryScoreItem(BaseModel):
    category: str
    score: int
    status: str
    finding_count: int = 0
    critical_count: int = 0
    high_count: int = 0

class AssessmentScope(BaseModel):
    account_id: Optional[str] = None
    aws_connection_id: Optional[str] = None
    region: Optional[str] = None
    resources_scanned: int = 0
    services: List[str] = []
    methodology: str = "Deterministic Security Rule Assessment"

class SecurityReportDetail(BaseModel):
    report: SecurityReportResponse
    executive_summary: ExecutiveSummary
    security_posture: SecurityPosture
    category_scores: List[ReportCategoryScoreItem]
    finding_summary: FindingSummary
    top_findings: List[ReportFindingItem]
    detailed_findings: List[ReportFindingItem] = []
    assessment_scope: AssessmentScope
