from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.report import SecurityReport
from typing import List, Optional

class ReportRepository:
    def get(self, db: Session, report_id: str) -> Optional[SecurityReport]:
        return db.query(SecurityReport).filter(SecurityReport.id == report_id).first()

    def get_by_scan(self, db: Session, scan_id: str) -> Optional[SecurityReport]:
        return db.query(SecurityReport).filter(SecurityReport.scan_id == scan_id).first()

    def list_reports(
        self,
        db: Session,
        workspace_id: Optional[str] = None,
        workspace_ids: Optional[List[str]] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[SecurityReport]:
        query = db.query(SecurityReport)
        if workspace_id:
            query = query.filter(SecurityReport.workspace_id == workspace_id)
        elif workspace_ids is not None:
            query = query.filter(SecurityReport.workspace_id.in_(workspace_ids))
        return query.order_by(SecurityReport.generated_at.desc(), SecurityReport.created_at.desc()).offset(skip).limit(limit).all()

    def count(
        self,
        db: Session,
        workspace_id: Optional[str] = None,
        workspace_ids: Optional[List[str]] = None,
    ) -> int:
        query = db.query(SecurityReport)
        if workspace_id:
            query = query.filter(SecurityReport.workspace_id == workspace_id)
        elif workspace_ids is not None:
            query = query.filter(SecurityReport.workspace_id.in_(workspace_ids))
        return query.count()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[SecurityReport]:
        return db.query(SecurityReport).order_by(SecurityReport.generated_at.desc()).offset(skip).limit(limit).all()

    def create(self, db: Session, report_data: dict) -> SecurityReport:
        report = SecurityReport(**report_data)
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

report_repo = ReportRepository()
