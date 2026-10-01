import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class CheckResult(Base):
    __tablename__ = "check_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False, index=True)
    resource_id = Column(String, nullable=False)
    rule_id = Column(String, nullable=False)
    
    status = Column(String, nullable=False) # PASSED, FAILED, ERROR, SKIPPED
    error_message = Column(String, nullable=True)
    
    checked_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    scan = relationship("Scan", back_populates="check_results")
