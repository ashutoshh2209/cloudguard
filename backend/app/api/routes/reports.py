from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Any

from app.core.database import get_db
from app.schemas.report import SecurityReportCreate, SecurityReportResponse, SecurityReportList
from app.reports.service import generate_report_summary, get_report_details
from app.reports.pdf import generate_pdf
from app.repositories.report import report_repo

router = APIRouter()

@router.post("/", response_model=SecurityReportResponse)
def create_report(
    scan_id: str = Query(..., description="The ID of the completed scan to report on"),
    db: Session = Depends(get_db)
) -> Any:
    """
    Generate a new security report from a completed scan.
    """
    report = generate_report_summary(db, scan_id)
    return report

@router.get("/", response_model=SecurityReportList)
def list_reports(
    skip: int = Query(0, description="Pagination skip"),
    limit: int = Query(50, description="Pagination limit"),
    db: Session = Depends(get_db)
) -> Any:
    """
    List all generated security reports.
    """
    reports = report_repo.get_all(db, skip=skip, limit=limit)
    total = report_repo.count(db)
    return {"items": reports, "total": total}

@router.get("/{report_id}")
def get_report(report_id: str, db: Session = Depends(get_db)) -> Any:
    """
    Get detailed web view of a security report.
    """
    details = get_report_details(db, report_id)
    return details

@router.get("/{report_id}/download")
def download_report_pdf(report_id: str, db: Session = Depends(get_db)):
    """
    Download a PDF version of the report.
    """
    details = get_report_details(db, report_id)
    report = details["report"]
    scan = report.scan
    top_findings = details["top_findings"]
    category_scores = details["category_scores"]
    
    pdf_buffer = generate_pdf(report, scan, top_findings, category_scores)
    
    filename = f"cloudguard-security-report-{report_id}.pdf"
    
    return StreamingResponse(
        pdf_buffer, 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
