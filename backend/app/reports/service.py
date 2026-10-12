import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.report import report_repo
from app.repositories.scan import scan_repo
from app.repositories.finding import finding_repo
from app.models.report import SecurityReport
from app.models.scan import Scan
from app.reports.pdf import sanitize_text

def generate_report_summary(
    db: Session,
    scan_id: str,
    title: Optional[str] = None,
    workspace_id: Optional[str] = None,
) -> SecurityReport:
    """
    Generate and persist a SecurityReport from an existing completed or partial scan.
    Guarantees that no new scan or security checks are run.
    """
    scan = scan_repo.get(db, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
        
    if scan.status not in ["COMPLETED", "PARTIAL"]:
        raise HTTPException(status_code=400, detail="Cannot generate report for incomplete scan")

    # If workspace_id passed, verify scan belongs to it
    if workspace_id and scan.workspace_id and scan.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Scan does not belong to specified workspace")

    # Idempotent retrieval: If a report already exists for this scan, return the persisted report
    existing_report = report_repo.get_by_scan(db, scan_id)
    if existing_report:
        return existing_report

    # Fetch persisted findings (no re-scan)
    findings = finding_repo.list_findings(db, scan_id=scan_id, limit=10000)
    
    # Calculate finding counts directly from persisted data
    critical = sum(1 for f in findings if (f.severity or "").upper() == "CRITICAL")
    high = sum(1 for f in findings if (f.severity or "").upper() == "HIGH")
    medium = sum(1 for f in findings if (f.severity or "").upper() == "MEDIUM")
    low = sum(1 for f in findings if (f.severity or "").upper() == "LOW")
    info = sum(1 for f in findings if (f.severity or "").upper() == "INFO")
    
    report_data = {
        "workspace_id": scan.workspace_id,
        "scan_id": scan_id,
        "aws_connection_id": scan.aws_connection_id,
        "title": title or f"Security Assessment - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "report_type": "SECURITY_ASSESSMENT",
        "status": "GENERATED",
        "security_score": scan.security_score,
        "security_rating": scan.security_rating,
        "finding_count": len(findings),
        "critical_count": critical,
        "high_count": high,
        "medium_count": medium,
        "low_count": low,
        "info_count": info,
        "resource_count": scan.resources_scanned or 0,
        "coverage_percentage": scan.coverage_percentage or 0.0,
        "generated_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
    }
    
    report = report_repo.create(db, report_data)
    return report


def get_report_raw(db: Session, report_id: str) -> SecurityReport:
    """Fetch raw SecurityReport entity, raising 404 if missing."""
    report = report_repo.get(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


def get_report_details(db: Session, report_id: str) -> Dict[str, Any]:
    """
    Construct rich report details for the frontend and API consumption,
    including executive narrative, category scores, and sanitized findings.
    """
    report = get_report_raw(db, report_id)
    scan = report.scan
    findings = finding_repo.list_findings(db, scan_id=report.scan_id, limit=1000)
    category_scores = scan.category_scores if scan else []

    # Sort findings by risk score descending
    sorted_findings = sorted(
        findings,
        key=lambda x: (x.risk_score or 0, x.detected_at or datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True
    )

    # Executive narrative synthesis
    if report.critical_count > 0:
        exec_text = (
            f"The assessment identified {report.critical_count} critical and {report.high_count} high-severity vulnerabilities. "
            "Immediate remediation of exposed endpoints and privileged roles is strongly advised."
        )
    elif report.high_count > 0:
        exec_text = (
            f"The assessment identified {report.high_count} high-priority security issues. "
            "Remediation is recommended to align with AWS security best practices and prevent privilege escalation."
        )
    elif report.finding_count == 0:
        exec_text = "All evaluated AWS resources conform to deterministic security baselines with no active findings identified."
    else:
        exec_text = (
            f"The assessment identified {report.finding_count} security configuration observations. "
            "Review findings to improve defense-in-depth posture."
        )

    formatted_findings = [
        {
            "finding_id": f.id,
            "rule_id": sanitize_text(f.rule_id),
            "title": sanitize_text(f.title),
            "severity": (f.severity or "INFO").upper(),
            "service": sanitize_text(f.service or f.category or "aws"),
            "resource_id": sanitize_text(f.resource_id),
            "category": sanitize_text(f.category or f.service or "general"),
            "description": sanitize_text(f.description),
            "recommendation": sanitize_text(f.recommendation),
            "status": f.status or "OPEN",
            "risk_score": f.risk_score or 0,
            "priority": f.priority or "P4",
            "detected_at": f.detected_at.isoformat() if f.detected_at else None,
        }
        for f in sorted_findings
    ]

    formatted_categories = [
        {
            "category": cs.category,
            "score": cs.score,
            "status": cs.status,
            "finding_count": cs.finding_count or 0,
            "critical_count": cs.critical_count or 0,
            "high_count": cs.high_count or 0,
        }
        for cs in category_scores
    ]

    account_id = None
    if scan:
        if getattr(scan, "aws_connection", None):
            account_id = getattr(scan.aws_connection, "account_id", None)
        if not account_id:
            account_id = scan.aws_connection_id

    distinct_services = list(set([f.get("service") for f in formatted_findings if f.get("service")]))
    if not distinct_services:
        distinct_services = ["s3", "ec2", "iam", "rds", "cloudtrail"]

    return {
        "report": report,
        "executive_summary": {
            "summary_text": exec_text,
            "security_score": report.security_score,
            "rating": report.security_rating,
            "key_highlights": [
                f"{report.resource_count} resources assessed across {len(distinct_services)} services",
                f"{report.finding_count} total findings recorded",
                f"{report.critical_count} critical risks requiring attention",
            ]
        },
        "security_posture": {
            "score": report.security_score,
            "rating": report.security_rating,
            "coverage": report.coverage_percentage,
            "status": scan.status if scan else "UNKNOWN",
        },
        "category_scores": formatted_categories,
        "finding_summary": {
            "critical": report.critical_count,
            "high": report.high_count,
            "medium": report.medium_count,
            "low": report.low_count,
            "info": report.info_count,
        },
        "top_findings": formatted_findings[:10],
        "detailed_findings": formatted_findings,
        "assessment_scope": {
            "account_id": account_id,
            "aws_connection_id": scan.aws_connection_id if scan else None,
            "region": "us-east-1",
            "resources_scanned": report.resource_count,
            "services": distinct_services,
            "methodology": "Deterministic Security Rule Assessment",
        }
    }
