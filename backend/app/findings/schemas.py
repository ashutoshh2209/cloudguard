from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

class FindingStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"

class Finding(BaseModel):
    finding_id: str
    rule_id: str
    title: str
    severity: Severity
    service: str
    resource_id: str
    resource_name: str
    region: str
    category: str
    description: str
    evidence: Dict[str, Any]
    recommendation: str
    status: FindingStatus = FindingStatus.OPEN
    risk_score: Optional[int] = None
    priority: Optional[str] = None
    risk_factors: Optional[List[str]] = None

class ScanSummary(BaseModel):
    resources_scanned: int = 0
    findings: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0
    checks_attempted: int = 0
    checks_completed: int = 0
    checks_failed: int = 0
    checks_passed: int = 0
    checks_errored: int = 0

class CheckSummary(BaseModel):
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0

class ScanResult(BaseModel):
    scan_id: str
    id: Optional[str] = None
    status: str
    account_id: str
    security_score: Optional[int] = None
    rating: Optional[str] = None
    summary: ScanSummary
    checks_summary: Optional[CheckSummary] = None
    category_scores: Optional[Dict[str, Any]] = None
    findings: List[Finding]

    def __init__(self, **data):
        if "scan_id" in data and "id" not in data:
            data["id"] = data["scan_id"]
        elif "id" in data and "scan_id" not in data:
            data["scan_id"] = data["id"]
        super().__init__(**data)

class CheckResultItem(BaseModel):
    id: str
    scan_id: str
    resource_id: str
    rule_id: str
    status: str
    message: Optional[str] = None
    error_message: Optional[str] = None
    recommendation: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    checked_at: Optional[str] = None

class ScanResponseItem(BaseModel):
    id: str
    scan_id: str
    workspace_id: Optional[str] = None
    status: str
    started_at: str
    completed_at: Optional[str] = None
    aws_connection_id: Optional[str] = None
    summary: ScanSummary
    coverage_percentage: int = 0
    security_score: Optional[int] = None
    security_rating: Optional[str] = None

class ScanDetailResponse(ScanResponseItem):
    check_results: Optional[List[CheckResultItem]] = None
    findings: Optional[List[Finding]] = None

class ScanStatusInfo(BaseModel):
    scan_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    security_score: Optional[int] = None
    rating: Optional[str] = None
    resources_scanned: int = 0
    finding_count: int = 0

