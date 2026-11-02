from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user_optional
from app.models.user import User
from app.models.scan import Scan
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.scan import scan_repo
from app.schemas.dashboard import DashboardSummary, TopRiskFinding, ScoreTrendPoint

router = APIRouter()

@router.get("", response_model=DashboardSummary)
@router.get("/", response_model=DashboardSummary)
@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard(
    workspace_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Returns the dashboard summary of the latest security posture.
    Consumes single source of truth persisted scan and risk data.
    Does NOT recalculate security scores independently.
    Supports workspace scoping with membership verification (anti-IDOR).
    Provides actual historical trend data without inventing data.
    """
    if workspace_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view workspace dashboard",
            )
        ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not ws:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

        is_member = ws.owner_id == current_user.id or db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
        ).first() is not None

        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have access to this workspace",
            )

        latest_scan = (
            db.query(Scan)
            .filter(Scan.workspace_id == workspace_id, Scan.status == "COMPLETED")
            .order_by(Scan.completed_at.desc(), Scan.created_at.desc())
            .first()
        )
    else:
        latest_scan = scan_repo.get_latest_completed(db)

    if not latest_scan:
        return DashboardSummary(
            rating="Not Scored",
            reason="No scans have been executed yet.",
            score_trend=[],
        )

    if latest_scan.security_score is None:
        return DashboardSummary(
            rating="Not Scored",
            reason="No scannable AWS resources were discovered or insufficient data to calculate a score.",
            latest_scan_id=latest_scan.id,
            latest_scan_status=latest_scan.status,
            last_scanned_at=latest_scan.completed_at.isoformat() if latest_scan.completed_at else None,
            score_trend=[],
        )

    # Active findings (unresolved)
    active_findings = [f for f in (latest_scan.findings or []) if f.status != "RESOLVED"]

    # Top Risk Findings (sorted by risk_score descending)
    sorted_risks = sorted(active_findings, key=lambda f: f.risk_score or 0, reverse=True)[:10]
    top_risks = [
        TopRiskFinding(
            finding_id=f.id,
            title=f.title,
            severity=f.severity,
            risk_score=f.risk_score or 0,
            priority=f.priority or "P4",
            resource_name=f.resource_id,
        )
        for f in sorted_risks
    ]

    findings_summary = {
        "critical": sum(1 for f in active_findings if (f.severity or "").upper() == "CRITICAL"),
        "high": sum(1 for f in active_findings if (f.severity or "").upper() == "HIGH"),
        "medium": sum(1 for f in active_findings if (f.severity or "").upper() == "MEDIUM"),
        "low": sum(1 for f in active_findings if (f.severity or "").upper() == "LOW"),
        "info": sum(1 for f in active_findings if (f.severity or "").upper() == "INFO"),
    }

    passed_count = (
        latest_scan.checks_passed
        if latest_scan.checks_passed is not None
        else ((latest_scan.checks_completed or 0) - (latest_scan.checks_failed or 0))
    )
    checks_summary = {
        "passed": max(0, passed_count),
        "failed": latest_scan.checks_failed or 0,
        "errors": latest_scan.checks_errored or 0,
        "skipped": 0,
    }

    category_scores = {}
    for cs in (latest_scan.category_scores or []):
        category_scores[cs.category] = {
            "score": cs.score,
            "status": cs.status,
            "findings": cs.finding_count,
            "critical": cs.critical_count,
            "high": cs.high_count,
        }

    # Query historical completed scans for trend and previous score
    history_query = db.query(Scan).filter(
        Scan.status.in_(["COMPLETED", "PARTIAL"]),
        Scan.security_score.isnot(None),
    )
    if workspace_id:
        history_query = history_query.filter(Scan.workspace_id == workspace_id)
    elif current_user:
        owned_ids = [w.id for w in (current_user.owned_workspaces or [])]
        member_records = db.query(WorkspaceMember.workspace_id).filter(WorkspaceMember.user_id == current_user.id).all()
        ws_ids = list(set(owned_ids + [m[0] for m in member_records]))
        if ws_ids:
            history_query = history_query.filter(Scan.workspace_id.in_(ws_ids))

    historical_scans = (
        history_query.order_by(Scan.started_at.desc().nullslast(), Scan.created_at.desc().nullslast())
        .limit(10)
        .all()
    )

    previous_score: Optional[int] = None
    score_delta: Optional[int] = None
    if len(historical_scans) > 1:
        previous_score = historical_scans[1].security_score
        if latest_scan.security_score is not None and previous_score is not None:
            score_delta = latest_scan.security_score - previous_score

    # Build chronological score trend (oldest to newest) from actual scans
    score_trend: List[ScoreTrendPoint] = []
    for s in reversed(historical_scans):
        if s.security_score is not None:
            dt = s.started_at or s.created_at or s.completed_at
            date_str = dt.strftime("%b %d, %H:%M") if dt else "Scan"
            timestamp_str = dt.isoformat() if dt else ""
            score_trend.append(
                ScoreTrendPoint(
                    scan_id=s.id,
                    date=date_str,
                    timestamp=timestamp_str,
                    score=s.security_score,
                    rating=s.security_rating,
                )
            )

    last_scanned_str = (
        latest_scan.completed_at.isoformat()
        if latest_scan.completed_at
        else (latest_scan.started_at.isoformat() if latest_scan.started_at else None)
    )

    is_sim = bool(
        (latest_scan.aws_connection_id and "demo" in latest_scan.aws_connection_id.lower())
        or (latest_scan.findings and any(
            ((f.evidence or {}).get("simulated")) or (f.resource_id and f.resource_id.startswith("demo-"))
            for f in latest_scan.findings
        ))
    )

    return DashboardSummary(
        security_score=latest_scan.security_score,
        rating=latest_scan.security_rating or "Not Scored",
        reason=None,
        total_resources=latest_scan.resources_scanned or 0,
        total_findings=len(active_findings),
        findings_summary=findings_summary,
        checks_summary=checks_summary,
        category_scores=category_scores,
        top_risks=top_risks,
        latest_scan_id=latest_scan.id,
        latest_scan_status=latest_scan.status,
        last_scanned_at=last_scanned_str,
        previous_score=previous_score,
        score_delta=score_delta,
        score_trend=score_trend,
        is_simulated=is_sim,
        scan_mode="simulated_demo" if is_sim else "live_aws",
    )
