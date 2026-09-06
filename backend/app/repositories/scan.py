from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.scan import Scan

class ScanRepository:
    def create(self, db: Session, aws_connection_id: str) -> Scan:
        scan = Scan(
            aws_connection_id=aws_connection_id,
            status="RUNNING"
        )
        db.add(scan)
        db.flush()
        return scan

    def get(self, db: Session, scan_id: str) -> Optional[Scan]:
        return db.query(Scan).filter(Scan.id == scan_id).first()
        
    def get_latest_completed(self, db: Session) -> Optional[Scan]:
        return db.query(Scan).filter(Scan.status == "COMPLETED").order_by(Scan.created_at.desc()).first()

    def get_all(self, db: Session, skip: int = 0, limit: int = 20) -> List[Scan]:
        return db.query(Scan).order_by(Scan.created_at.desc()).offset(skip).limit(limit).all()

    def update_scan_metrics(self, db: Session, scan_id: str, 
                          resources_scanned: int, 
                          checks_attempted: int,
                          checks_completed: int,
                          checks_failed: int,
                          security_score: int = None,
                          security_rating: str = None):
        scan = self.get(db, scan_id)
        if scan:
            scan.resources_scanned = resources_scanned
            scan.checks_attempted = checks_attempted
            scan.checks_completed = checks_completed
            scan.checks_failed = checks_failed
            scan.security_score = security_score
            scan.security_rating = security_rating
            if checks_attempted > 0:
                scan.coverage_percentage = int((checks_completed / checks_attempted) * 100)
            db.flush()

    def complete_scan(self, db: Session, scan_id: str, status: str = "COMPLETED"):
        from datetime import datetime, timezone
        scan = self.get(db, scan_id)
        if scan:
            scan.status = status
            scan.completed_at = datetime.now(timezone.utc)
            db.flush()

scan_repo = ScanRepository()
