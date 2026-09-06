from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.repositories.report import report_repo
from app.repositories.scan import scan_repo
from app.repositories.finding import finding_repo
from datetime import datetime, timezone

def generate_report_summary(db: Session, scan_id: str):
    scan = scan_repo.get(db, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
        
    if scan.status not in ["COMPLETED", "PARTIAL"]:
        raise HTTPException(status_code=400, detail="Cannot generate report for incomplete scan")

    # Check if report already exists for this scan
    existing_report = report_repo.get_by_scan(db, scan_id)
    if existing_report:
        return existing_report

    # Fetch findings
    findings = finding_repo.list_findings(db, scan_id=scan_id, limit=10000)
    
    # Calculate finding counts
    critical = sum(1 for f in findings if f.severity == "CRITICAL")
    high = sum(1 for f in findings if f.severity == "HIGH")
    medium = sum(1 for f in findings if f.severity == "MEDIUM")
    low = sum(1 for f in findings if f.severity == "LOW")
    info = sum(1 for f in findings if f.severity == "INFO")
    
    # Create the report record
    report_data = {
        "scan_id": scan_id,
        "title": f"Security Assessment - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "status": "GENERATED",
        "security_score": scan.security_score,
        "security_rating": scan.security_rating,
        "finding_count": len(findings),
        "critical_count": critical,
        "high_count": high,
        "medium_count": medium,
        "low_count": low,
        "info_count": info,
        "resource_count": scan.resources_scanned,
        "coverage_percentage": scan.coverage_percentage,
    }
    
    report = report_repo.create(db, report_data)
    return report

def get_report_details(db: Session, report_id: str):
    report = report_repo.get(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    scan = report.scan
    findings = finding_repo.list_findings(db, scan_id=report.scan_id, limit=50) # top 50
    category_scores = scan.category_scores if scan else []
    
    # Generate executive summary text
    if report.critical_count > 0:
        exec_text = "The assessment identified critical security issues requiring immediate attention."
    elif report.high_count > 0:
        exec_text = "The assessment found several high-priority security issues that should be addressed."
    elif report.finding_count == 0:
        exec_text = "No security findings were identified by the currently enabled CloudGuard rules."
    else:
        exec_text = "The assessment identified security configuration issues that should be reviewed to improve security posture."
        
    return {
        "report": report,
        "executive_summary": {
            "summary_text": exec_text
        },
        "security_posture": {
            "score": report.security_score,
            "rating": report.security_rating,
            "coverage": report.coverage_percentage,
            "status": scan.status if scan else "UNKNOWN"
        },
        "category_scores": category_scores,
        "finding_summary": {
            "critical": report.critical_count,
            "high": report.high_count,
            "medium": report.medium_count,
            "low": report.low_count,
            "info": report.info_count
        },
        "top_findings": findings[:10]  # Return top 10 for detailed view
    }
