import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class SecurityReport(Base):
    __tablename__ = "security_reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # In a full multi-tenant system, this would be workspace_id. We'll use aws_connection_id as proxy or just rely on the scan.
    scan_id = Column(String, ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    
    report_type = Column(String, nullable=False, default="SECURITY_ASSESSMENT")
    status = Column(String, nullable=False, default="GENERATED")
    title = Column(String, nullable=False)
    
    security_score = Column(Integer, nullable=True)
    security_rating = Column(String, nullable=True)
    
    finding_count = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    info_count = Column(Integer, default=0)
    
    resource_count = Column(Integer, default=0)
    coverage_percentage = Column(Integer, default=0)
    
    generated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    scan = relationship("Scan")
