from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.core.database import get_db
from app.api.deps import get_current_user_optional
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.aws_connection import AWSConnection
from app.models.scan import Scan
from app.models.check_result import CheckResult
from app.models.finding import Finding as FindingModel
from app.scanner.manager import scan_manager
from app.scanner.deterministic_scanner import deterministic_scanner
from app.findings.schemas import (
    Finding,
    ScanResult,
    ScanResponseItem,
    ScanSummary,
    CheckResultItem,
    ScanDetailResponse,
)
from app.repositories.scan import scan_repo
from app.repositories.finding import finding_repo

router = APIRouter()

class RunScanRequest(BaseModel):
    workspace_id: Optional[str] = None
    account_id: Optional[str] = None
    aws_connection_id: Optional[str] = None


def _format_scan_item(scan: Scan) -> Dict[str, Any]:
    created_iso = scan.created_at.isoformat() if scan.created_at else (scan.started_at.isoformat() if scan.started_at else None)
    return {
        "id": scan.id,
        "scan_id": scan.id,
        "workspace_id": scan.workspace_id,
        "status": scan.status,
        "started_at": scan.started_at.isoformat() if scan.started_at else "",
        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        "created_at": created_iso,
        "aws_connection_id": scan.aws_connection_id,
        "summary": {
            "resources_scanned": scan.resources_scanned or 0,
            "findings": len(scan.findings) if scan.findings else 0,
            "critical": sum(1 for f in (scan.findings or []) if (f.severity or "").upper() == "CRITICAL"),
            "high": sum(1 for f in (scan.findings or []) if (f.severity or "").upper() == "HIGH"),
            "medium": sum(1 for f in (scan.findings or []) if (f.severity or "").upper() == "MEDIUM"),
            "low": sum(1 for f in (scan.findings or []) if (f.severity or "").upper() == "LOW"),
            "info": sum(1 for f in (scan.findings or []) if (f.severity or "").upper() == "INFO"),
            "checks_attempted": scan.checks_attempted or 0,
            "checks_completed": scan.checks_completed or 0,
            "checks_failed": scan.checks_failed or 0,
            "checks_passed": scan.checks_passed or 0,
            "checks_errored": scan.checks_errored or 0,
        },
        "coverage_percentage": scan.coverage_percentage or 0,
        "security_score": scan.security_score,
        "security_rating": scan.security_rating,
    }


def _format_scan_detail(scan: Scan, db: Session) -> Dict[str, Any]:
    base = _format_scan_item(scan)
    
    # Get account_id from connection if available
    account_id = ""
    if scan.aws_connection_id:
        conn = db.query(AWSConnection).filter(AWSConnection.id == scan.aws_connection_id).first()
        if conn:
            account_id = conn.account_id
    base["account_id"] = account_id

    # Category scores
    cat_scores = {}
    for cs in (scan.category_scores or []):
        cat_scores[cs.category] = {
            "score": cs.score,
            "status": cs.status,
            "findings": cs.finding_count,
            "critical": cs.critical_count,
            "high": cs.high_count,
        }
    base["category_scores"] = cat_scores

    # Format check results
    check_results = (
        db.query(CheckResult)
        .filter(CheckResult.scan_id == scan.id)
        .order_by(CheckResult.checked_at.desc())
        .all()
    )
    base["check_results"] = [
        {
            "id": cr.id,
            "scan_id": cr.scan_id,
            "resource_id": cr.resource_id,
            "rule_id": cr.rule_id,
            "status": cr.status,
            "message": cr.message,
            "error_message": cr.error_message,
            "recommendation": cr.recommendation,
            "evidence": cr.evidence or {},
            "checked_at": cr.checked_at.isoformat() if cr.checked_at else None,
        }
        for cr in check_results
    ]

    # Format findings
    findings = (
        db.query(FindingModel)
        .filter(FindingModel.scan_id == scan.id)
        .order_by(FindingModel.risk_score.desc().nullslast(), FindingModel.detected_at.desc())
        .all()
    )
    base["findings"] = [
        {
            "finding_id": f.id,
            "id": f.id,
            "workspace_id": f.workspace_id,
            "scan_id": f.scan_id,
            "rule_id": f.rule_id,
            "title": f.title,
            "severity": f.severity,
            "service": f.service or "aws",
            "resource_id": f.resource_id,
            "resource_name": f.resource_id,
            "region": f.region or "global",
            "category": f.category,
            "description": f.description,
            "evidence": f.evidence or {},
            "recommendation": f.recommendation,
            "status": f.status,
            "risk_score": f.risk_score,
            "priority": f.priority or "P4",
            "risk_factors": f.risk_factors or [],
            "created_at": f.created_at.isoformat() if f.created_at else (f.detected_at.isoformat() if f.detected_at else None),
            "detected_at": f.detected_at.isoformat() if f.detected_at else None,
            "updated_at": f.updated_at.isoformat() if f.updated_at else None,
        }
        for f in findings
    ]

    return base


@router.post("")
@router.post("/")
async def run_scan(
    payload: Optional[RunScanRequest] = None,
    account_id: Optional[str] = Query(None),
    workspace_id: Optional[str] = Query(None),
    aws_connection_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Triggers a security scan.
    - If workspace_id is provided, verifies user membership and permissions (OWNER, ADMIN, MEMBER).
      VIEWER role is restricted from triggering scans.
      Executes deterministic security rules against discovered resources.
    - If account_id is provided without workspace_id, runs legacy scan flow for backwards compatibility.
    """
    target_workspace_id = (payload.workspace_id if payload else None) or workspace_id
    target_account_id = (payload.account_id if payload else None) or account_id
    target_conn_id = (payload.aws_connection_id if payload else None) or aws_connection_id

    # 1. Workspace-Authorized Scan Flow
    if target_workspace_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to run a workspace scan",
            )

        workspace = db.query(Workspace).filter(Workspace.id == target_workspace_id).first()
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        # Anti-IDOR check
        membership = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == target_workspace_id,
                WorkspaceMember.user_id == current_user.id,
            )
            .first()
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not a member of this workspace",
            )

        # Viewer restriction
        if membership.role not in ("OWNER", "ADMIN", "MEMBER"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: role '{membership.role}' cannot trigger scans (must be MEMBER, ADMIN, or OWNER)",
            )

        scan = deterministic_scanner.run_workspace_scan(
            db=db,
            workspace_id=target_workspace_id,
            aws_connection_id=target_conn_id,
        )
        return _format_scan_detail(scan, db)

    # 2. Legacy Account Scan Flow (Part 1 backwards compatibility)
    if target_account_id:
        return scan_manager.start_scan(target_account_id, db)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Missing required workspace_id or account_id",
    )


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
async def list_scans(
    workspace_id: Optional[str] = Query(None, description="Filter by workspace ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by scan status (e.g. COMPLETED, RUNNING, FAILED, PARTIAL)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Returns a list of scans with pagination, workspace filtering, and status filtering.
    Always sorted newest first.
    Enforces workspace authorization (anti-IDOR).
    """
    query = db.query(Scan)

    if workspace_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view workspace scans",
            )

        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        # Anti-IDOR check: user must be owner or member
        is_member = workspace.owner_id == current_user.id or db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
        ).first() is not None

        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not a member of this workspace",
            )

        query = query.filter(Scan.workspace_id == workspace_id)
    elif current_user:
        # Show scans from all workspaces user has access to
        owned_ids = [w.id for w in (current_user.owned_workspaces or [])]
        member_records = db.query(WorkspaceMember.workspace_id).filter(WorkspaceMember.user_id == current_user.id).all()
        ws_ids = list(set(owned_ids + [m[0] for m in member_records]))
        if not ws_ids:
            return []
        query = query.filter(Scan.workspace_id.in_(ws_ids))

    if status_filter:
        query = query.filter(func.upper(Scan.status) == status_filter.strip().upper())

    scans = (
        query.order_by(Scan.started_at.desc().nullslast(), Scan.created_at.desc().nullslast())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_format_scan_item(s) for s in scans]


@router.get("/{scan_id}")
async def get_scan_status(
    scan_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Returns scan details, summary metrics, check results, category scores, and findings.
    Enforces workspace authorization if the scan is scoped to a workspace.
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    # Anti-IDOR check for workspace-scoped scans
    if scan.workspace_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view this scan",
            )

        ws = db.query(Workspace).filter(Workspace.id == scan.workspace_id).first()
        is_member = (ws and ws.owner_id == current_user.id) or db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == scan.workspace_id,
            WorkspaceMember.user_id == current_user.id,
        ).first() is not None

        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not a member of the workspace for this scan",
            )

    return _format_scan_detail(scan, db)


@router.get("/{scan_id}/checks")
async def get_scan_checks(
    scan_id: str,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: PASS, FAIL, ERROR, NOT_APPLICABLE"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Returns the individual deterministic check results for a scan.
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    if scan.workspace_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        membership = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == scan.workspace_id,
                WorkspaceMember.user_id == current_user.id,
            )
            .first()
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not a member of the workspace for this scan",
            )

    query = db.query(CheckResult).filter(CheckResult.scan_id == scan_id)
    if status_filter:
        query = query.filter(CheckResult.status == status_filter.upper().strip())

    checks = query.order_by(CheckResult.checked_at.desc()).offset(skip).limit(limit).all()
    return [
        {
            "id": cr.id,
            "scan_id": cr.scan_id,
            "resource_id": cr.resource_id,
            "rule_id": cr.rule_id,
            "status": cr.status,
            "message": cr.message,
            "error_message": cr.error_message,
            "recommendation": cr.recommendation,
            "evidence": cr.evidence or {},
            "checked_at": cr.checked_at.isoformat() if cr.checked_at else None,
        }
        for cr in checks
    ]


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
    result = []
    for f in findings:
        f_dict = {
            "finding_id": f.id,
            "rule_id": f.rule_id,
            "title": f.title,
            "severity": f.severity,
            "service": "aws",
            "resource_id": f.resource_id,
            "resource_name": f.resource_id, 
            "region": "global",
            "category": f.category,
            "description": f.description,
            "evidence": f.evidence or {},
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
        "resource_name": f.resource_id, 
        "region": "global",
        "category": f.category,
        "description": f.description,
        "evidence": f.evidence or {},
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
