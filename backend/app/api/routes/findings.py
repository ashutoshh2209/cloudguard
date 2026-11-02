from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.core.database import get_db
from app.api.deps import get_current_user_optional, get_current_user
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.finding import Finding
from app.models.scan import Scan


router = APIRouter()


class UpdateFindingStatusRequest(BaseModel):
    status: str


def _format_finding(f: Finding) -> Dict[str, Any]:
    created_iso = f.created_at.isoformat() if f.created_at else (f.detected_at.isoformat() if f.detected_at else None)
    detected_iso = f.detected_at.isoformat() if f.detected_at else created_iso
    updated_iso = f.updated_at.isoformat() if f.updated_at else None

    evidence = f.evidence or {}
    is_simulated = bool(
        evidence.get("simulated")
        or evidence.get("is_demo")
        or (f.resource_id and f.resource_id.startswith("demo-"))
        or (f.title and "[SIMULATED]" in f.title)
    )

    return {
        "id": f.id,
        "finding_id": f.id,
        "workspace_id": f.workspace_id,
        "scan_id": f.scan_id,
        "rule_id": f.rule_id,
        "title": f.title,
        "description": f.description,
        "severity": f.severity,
        "category": f.category,
        "service": f.service or "aws",
        "region": f.region or "global",
        "resource_id": f.resource_id,
        "resource_name": f.resource_id,
        "risk_score": f.risk_score,
        "priority": f.priority or "P4",
        "status": f.status,
        "recommendation": f.recommendation,
        "evidence": evidence,
        "risk_factors": f.risk_factors or [],
        "is_simulated": is_simulated,
        "source_label": "Simulated Finding (Demo Mode)" if is_simulated else "Live AWS Account",
        "created_at": created_iso,
        "detected_at": detected_iso,
        "updated_at": updated_iso,
    }


def _verify_workspace_access(
    db: Session,
    user: Optional[User],
    workspace_id: str,
    require_write: bool = False,
) -> None:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access workspace findings",
        )

    # Check workspace exists
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    # Owner has full access
    if workspace.owner_id == user.id:
        return

    # Check membership
    membership = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user.id)
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to this workspace",
        )

    if require_write and membership.role.upper() == "VIEWER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewer role cannot modify finding status",
        )


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
async def list_findings(
    workspace_id: Optional[str] = Query(None),
    scan_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    service: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    List security findings with filtering and workspace authorization.
    Supports filtering by severity, priority, service, status, scan_id, and workspace_id.
    """
    query = db.query(Finding)

    if workspace_id:
        _verify_workspace_access(db, current_user, workspace_id, require_write=False)
        query = query.filter(Finding.workspace_id == workspace_id)
    elif current_user:
        # Scope to all accessible workspaces for the authenticated user
        owned_ids = [w.id for w in (current_user.owned_workspaces or [])]
        member_records = db.query(WorkspaceMember.workspace_id).filter(WorkspaceMember.user_id == current_user.id).all()
        member_ids = [m[0] for m in member_records]
        accessible_ids = list(set(owned_ids + member_ids))
        if not accessible_ids:
            return []
        query = query.filter(Finding.workspace_id.in_(accessible_ids))

    if scan_id:
        query = query.filter(Finding.scan_id == scan_id)

    if severity:
        query = query.filter(func.upper(Finding.severity) == severity.upper())

    if priority:
        query = query.filter(func.upper(Finding.priority) == priority.upper())

    if service:
        query = query.filter(func.lower(Finding.service) == service.lower())

    if status_filter:
        query = query.filter(func.upper(Finding.status) == status_filter.upper())

    findings = (
        query.order_by(Finding.risk_score.desc().nullslast(), Finding.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [_format_finding(f) for f in findings]


@router.get("/{finding_id}")
async def get_finding(
    finding_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Retrieve a single finding by ID with anti-IDOR workspace authorization.
    """
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    if finding.workspace_id:
        _verify_workspace_access(db, current_user, finding.workspace_id, require_write=False)

    return _format_finding(finding)


@router.patch("/{finding_id}")
async def update_finding_status(
    finding_id: str,
    payload: Optional[UpdateFindingStatusRequest] = None,
    status_query: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Update finding status (OPEN, RESOLVED, IGNORED).
    Enforces workspace membership and role authorization (VIEWER cannot update status).
    """
    target_status = (payload.status if payload else None) or status_query
    if not target_status or target_status.upper() not in ["OPEN", "RESOLVED", "IGNORED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Allowed values: OPEN, RESOLVED, IGNORED.",
        )

    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    if finding.workspace_id:
        _verify_workspace_access(db, current_user, finding.workspace_id, require_write=True)

    finding.status = target_status.upper()
    finding.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(finding)

    return _format_finding(finding)
