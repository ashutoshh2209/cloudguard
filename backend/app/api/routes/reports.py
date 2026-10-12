from typing import Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import get_current_user_optional, get_current_user
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.scan import Scan
from app.schemas.report import (
    SecurityReportCreate,
    SecurityReportResponse,
    SecurityReportList,
    SecurityReportDetail,
)
from app.reports.service import generate_report_summary, get_report_details, get_report_raw
from app.reports.pdf import generate_pdf
from app.repositories.report import report_repo
from app.repositories.finding import finding_repo
from app.repositories.scan import scan_repo

router = APIRouter()


def _check_workspace_access(db: Session, workspace_id: str, user: User) -> bool:
    """Verify if user is the workspace owner or an authorized member."""
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        return False
    if ws.owner_id == user.id:
        return True
    membership = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user.id)
        .first()
    )
    return membership is not None


@router.post("", response_model=SecurityReportResponse)
@router.post("/", response_model=SecurityReportResponse)
def create_report(
    payload: Optional[SecurityReportCreate] = None,
    scan_id: Optional[str] = Query(None, description="The ID of the completed scan to report on"),
    workspace_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> Any:
    """
    Generate a new security report from an existing completed or partial scan.
    Guarantees no new scans or rules are recalculated.
    """
    target_scan_id = payload.scan_id if payload and payload.scan_id else scan_id
    if not target_scan_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="scan_id is required",
        )

    scan = scan_repo.get(db, target_scan_id)
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    # Anti-IDOR authorization
    if current_user and scan.workspace_id:
        if not _check_workspace_access(db, scan.workspace_id, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to access this workspace scan",
            )

    report_title = payload.title if payload and payload.title else None
    report = generate_report_summary(db, target_scan_id, title=report_title)
    return report


@router.get("", response_model=SecurityReportList)
@router.get("/", response_model=SecurityReportList)
def list_reports(
    workspace_id: Optional[str] = Query(None, description="Filter by workspace ID"),
    skip: int = Query(0, description="Pagination skip"),
    limit: int = Query(50, description="Pagination limit"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> Any:
    """
    List generated security reports with pagination and anti-IDOR workspace scoping.
    """
    workspace_ids = None

    if current_user:
        if workspace_id:
            if not _check_workspace_access(db, workspace_id, current_user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You do not have permission for this workspace",
                )
            target_ws_id = workspace_id
        else:
            # Gather all accessible workspaces for current user
            owned = [w.id for w in db.query(Workspace).filter(Workspace.owner_id == current_user.id).all()]
            memberships = [
                m.workspace_id
                for m in db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).all()
            ]
            accessible = list(set(owned + memberships))
            workspace_ids = accessible
            target_ws_id = None
    else:
        target_ws_id = workspace_id

    reports = report_repo.list_reports(
        db,
        workspace_id=target_ws_id,
        workspace_ids=workspace_ids,
        skip=skip,
        limit=limit,
    )
    total = report_repo.count(
        db,
        workspace_id=target_ws_id,
        workspace_ids=workspace_ids,
    )
    return {"items": reports, "total": total}


@router.get("/{report_id}", response_model=SecurityReportDetail)
def get_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> Any:
    """
    Get comprehensive report view including posture, category scores, and sanitized findings.
    """
    report = get_report_raw(db, report_id)
    if current_user and report.workspace_id:
        if not _check_workspace_access(db, report.workspace_id, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to view this report",
            )

    details = get_report_details(db, report_id)
    return details


@router.get("/{report_id}/download")
def download_report_pdf(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Download a professional PDF export of the security assessment report.
    """
    report = get_report_raw(db, report_id)
    if current_user and report.workspace_id:
        if not _check_workspace_access(db, report.workspace_id, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to download this report",
            )

    scan = report.scan
    findings = finding_repo.list_findings(db, scan_id=report.scan_id, limit=500)
    category_scores = scan.category_scores if scan else []
    
    account_id = None
    if scan and scan.aws_connection:
        account_id = scan.aws_connection.account_id
    elif scan:
        account_id = scan.aws_connection_id

    pdf_buffer = generate_pdf(report, scan, findings, category_scores, account_id=account_id)
    
    filename = f"cloudguard-security-report-{report_id}.pdf"
    
    return StreamingResponse(
        pdf_buffer, 
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        }
    )
