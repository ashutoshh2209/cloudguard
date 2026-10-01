from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.repositories.scan import scan_repo
from app.schemas.dashboard import DashboardSummary, TopRiskFinding

router = APIRouter()

@router.get("", response_model=DashboardSummary)
async def get_dashboard(db: Session = Depends(get_db)):
    """
    Returns the frontend-friendly dashboard summary of the latest security posture.
    """
    latest_scan = scan_repo.get_latest_completed(db)
        
    if not latest_scan:
        return DashboardSummary(
            rating="Not Scored",
            reason="No scans have been executed yet."
        )
        
    if latest_scan.security_score is None:
        return DashboardSummary(
            rating="Not Scored",
            reason="No scannable AWS resources were discovered or insufficient data to calculate a score."
        )

    # Convert Top Findings
    top_risks = []
    # Get top findings from DB by sorting
    findings = sorted(latest_scan.findings, key=lambda f: f.risk_score or 0, reverse=True)[:10]
    for f in findings:
        top_risks.append(
            TopRiskFinding(
                finding_id=f.id,
                title=f.title,
                severity=f.severity,
                risk_score=f.risk_score or 0,
                priority=f.priority or "P4",
                resource_name="unknown" # For now
            )
        )
        
    # Reconstruct summaries
    findings_summary = {
        "critical": sum(1 for f in latest_scan.findings if f.severity == "CRITICAL"),
        "high": sum(1 for f in latest_scan.findings if f.severity == "HIGH"),
        "medium": sum(1 for f in latest_scan.findings if f.severity == "MEDIUM"),
        "low": sum(1 for f in latest_scan.findings if f.severity == "LOW"),
        "info": sum(1 for f in latest_scan.findings if f.severity == "INFO")
    }
    
    checks_summary = {
        "passed": latest_scan.checks_completed - latest_scan.checks_failed,
        "failed": latest_scan.checks_failed,
        "errors": 0,
        "skipped": 0
    }
    
    category_scores = {}
    for cs in latest_scan.category_scores:
        category_scores[cs.category] = {
            "score": cs.score,
            "status": cs.status,
            "findings": cs.finding_count,
            "critical": cs.critical_count,
            "high": cs.high_count
        }

    return DashboardSummary(
        security_score=latest_scan.security_score,
        rating=latest_scan.security_rating,
        findings_summary=findings_summary,
        checks_summary=checks_summary,
        category_scores=category_scores,
        top_risks=top_risks
    )
