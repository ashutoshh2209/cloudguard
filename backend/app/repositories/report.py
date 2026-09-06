from sqlalchemy.orm import Session
from app.models.report import SecurityReport
from app.schemas.report import SecurityReportCreate
from typing import List, Optional

class ReportRepository:
    def get(self, db: Session, report_id: str) -> Optional[SecurityReport]:
        return db.query(SecurityReport).filter(SecurityReport.id == report_id).first()

    def get_by_scan(self, db: Session, scan_id: str) -> Optional[SecurityReport]:
        return db.query(SecurityReport).filter(SecurityReport.scan_id == scan_id).first()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[SecurityReport]:
        return db.query(SecurityReport).order_by(SecurityReport.created_at.desc()).offset(skip).limit(limit).all()

    def count(self, db: Session) -> int:
        return db.query(SecurityReport).count()

    def create(self, db: Session, report_data: dict) -> SecurityReport:
        report = SecurityReport(**report_data)
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

report_repo = ReportRepository()
