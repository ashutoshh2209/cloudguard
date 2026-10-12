import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

PortableJSON = JSON().with_variant(JSONB, 'postgresql')

class CheckResult(Base):
    __tablename__ = "check_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_id = Column(String, nullable=False, index=True)
    rule_id = Column(String, nullable=False, index=True)
    
    status = Column(String, nullable=False, index=True) # PASS, FAIL, ERROR, NOT_APPLICABLE
    message = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    recommendation = Column(String, nullable=True)
    evidence = Column(PortableJSON, nullable=True)
    
    checked_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    scan = relationship("Scan", back_populates="check_results")
