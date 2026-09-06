from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from app.findings.schemas import Finding, CheckSummary

class TopRiskFinding(BaseModel):
    finding_id: str
    title: str
    severity: str
    risk_score: int
    priority: str
    resource_name: str

class DashboardSummary(BaseModel):
    security_score: Optional[int] = None
    rating: str
    reason: Optional[str] = None
    findings_summary: Dict[str, int] = {}
    checks_summary: Optional[CheckSummary] = None
    category_scores: Dict[str, Any] = {}
    top_risks: List[TopRiskFinding] = []
