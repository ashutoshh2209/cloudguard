from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from app.findings.schemas import CheckSummary

class TopRiskFinding(BaseModel):
    finding_id: str
    title: str
    severity: str
    risk_score: int
    priority: str
    resource_name: str

class ScoreTrendPoint(BaseModel):
    scan_id: str
    date: str
    timestamp: str
    score: int
    rating: Optional[str] = None

class DashboardSummary(BaseModel):
    security_score: Optional[int] = None
    rating: str
    reason: Optional[str] = None
    total_resources: int = 0
    total_findings: int = 0
    findings_summary: Dict[str, int] = {}
    checks_summary: Optional[CheckSummary] = None
    category_scores: Dict[str, Any] = {}
    top_risks: List[TopRiskFinding] = []
    latest_scan_id: Optional[str] = None
    latest_scan_status: Optional[str] = None
    last_scanned_at: Optional[str] = None
    previous_score: Optional[int] = None
    score_delta: Optional[int] = None
    score_trend: List[ScoreTrendPoint] = []
