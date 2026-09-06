from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.database.dependencies import get_db
from app.scanner.manager import scan_manager
from app.findings.schemas import Finding, ScanResult, ScanStatusInfo
from app.repositories.scan import scan_repo
from app.repositories.finding import finding_repo
from app.models.scan import Scan

router = APIRouter()

@router.post("/", response_model=ScanResult)
async def run_scan(account_id: str, db: Session = Depends(get_db)):
    """
    Triggers a new synchronous scan for the given AWS account.
    """
    # In a real async flow, we would return a job ID.
    return scan_manager.start_scan(account_id, db)

@router.get("/", response_model=list) # Need proper schema for Scan list
async def list_scans(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    scans = scan_repo.get_all(db, skip=skip, limit=limit)
    return scans

@router.get("/{scan_id}")
async def get_scan_status(scan_id: str, db: Session = Depends(get_db)):
    """
    Returns the scan details.
    """
    scan = scan_repo.get(db, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan

@router.get("/findings/", response_model=List[Finding])
async def list_findings(
    scan_id: Optional[str] = Query(None, description="Filter by scan ID"),
    severity: Optional[str] = Query(None, description="Filter by severity (e.g., CRITICAL, HIGH)"),
    status: Optional[str] = Query(None, description="Filter by status (e.g., OPEN, RESOLVED)"),
    sort: Optional[str] = Query("risk_score", description="Sort field"),
    order: Optional[str] = Query("desc", description="Sort order (asc, desc)"),
    skip: int = Query(0, description="Pagination skip"),
    limit: int = Query(50, description="Pagination limit"),
    db: Session = Depends(get_db)
):
    """
    Returns a list of all findings.
    """
    findings = finding_repo.list_findings(
        db, scan_id=scan_id, severity=severity, status=status,
        sort=sort, order=order, skip=skip, limit=limit
    )
    # The Pydantic model finding_id maps to id in DB
    result = []
    for f in findings:
        f_dict = {
            "finding_id": f.id,
            "rule_id": f.rule_id,
            "title": f.title,
            "severity": f.severity,
            "service": "aws", # Need to fix or remove if not on model
            "resource_id": f.resource_id,
            "resource_name": "unknown", 
            "region": "global",
            "category": f.category,
            "description": f.description,
            "evidence": f.evidence,
            "recommendation": f.recommendation,
            "status": f.status,
            "risk_score": f.risk_score,
            "priority": f.priority,
            "risk_factors": f.risk_factors
        }
        result.append(Finding(**f_dict))
    return result

@router.get("/findings/{finding_id}", response_model=Finding)
async def get_finding(finding_id: str, db: Session = Depends(get_db)):
    """
    Returns details of a specific finding.
    """
    f = finding_repo.get(db, finding_id)
    if not f:
        raise HTTPException(status_code=404, detail="Finding not found")
        
    f_dict = {
        "finding_id": f.id,
        "rule_id": f.rule_id,
        "title": f.title,
        "severity": f.severity,
        "service": "aws", 
        "resource_id": f.resource_id,
        "resource_name": "unknown", 
        "region": "global",
        "category": f.category,
        "description": f.description,
        "evidence": f.evidence,
        "recommendation": f.recommendation,
        "status": f.status,
        "risk_score": f.risk_score,
        "priority": f.priority,
        "risk_factors": f.risk_factors
    }
    return Finding(**f_dict)

@router.patch("/findings/{finding_id}")
async def update_finding_status(finding_id: str, status: str, db: Session = Depends(get_db)):
    if status.upper() not in ["OPEN", "RESOLVED", "IGNORED"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    f = finding_repo.update_status(db, finding_id, status)
    if not f:
        raise HTTPException(status_code=404, detail="Finding not found")
    db.commit()
    return {"status": f.status}
