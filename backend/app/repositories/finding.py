from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.finding import Finding

class FindingRepository:
    def bulk_create(self, db: Session, scan_id: str, findings_data: List[Dict[str, Any]]):
        findings = []
        for f_data in findings_data:
            finding = Finding(
                id=f_data["id"],
                scan_id=scan_id,
                resource_id=f_data["resource_id"],
                rule_id=f_data["rule_id"],
                title=f_data["title"],
                description=f_data.get("description"),
                severity=f_data["severity"],
                category=f_data["category"],
                risk_score=f_data.get("risk_score"),
                priority=f_data.get("priority"),
                status=f_data.get("status", "OPEN"),
                recommendation=f_data.get("recommendation"),
                evidence=f_data.get("evidence"),
                risk_factors=f_data.get("risk_factors")
            )
            findings.append(finding)
        if findings:
            db.bulk_save_objects(findings)
            db.flush()

    def get(self, db: Session, finding_id: str) -> Optional[Finding]:
        return db.query(Finding).filter(Finding.id == finding_id).first()

    def list_findings(self, db: Session, scan_id: str = None, severity: str = None, 
                      service: str = None, status: str = None, 
                      sort: str = "risk_score", order: str = "desc", 
                      skip: int = 0, limit: int = 50) -> List[Finding]:
        query = db.query(Finding)
        if scan_id:
            query = query.filter(Finding.scan_id == scan_id)
        if severity:
            query = query.filter(Finding.severity == severity.upper())
        if status:
            query = query.filter(Finding.status == status.upper())
            
        # Sort logic
        if sort == "risk_score":
            if order.lower() == "desc":
                query = query.order_by(desc(Finding.risk_score))
            else:
                query = query.order_by(Finding.risk_score)
        else:
            query = query.order_by(desc(Finding.detected_at))
            
        return query.offset(skip).limit(limit).all()

    def update_status(self, db: Session, finding_id: str, status: str) -> Optional[Finding]:
        finding = self.get(db, finding_id)
        if finding:
            finding.status = status.upper()
            db.flush()
        return finding

finding_repo = FindingRepository()
