import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

# Portable JSON type
PortableJSON = JSON().with_variant(JSONB, 'postgresql')

class Finding(Base):
    __tablename__ = "findings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False, index=True)
    resource_id = Column(String, nullable=False)
    rule_id = Column(String, nullable=False, index=True)
    
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    severity = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    
    risk_score = Column(Integer, nullable=True, index=True)
    priority = Column(String, nullable=True)
    status = Column(String, nullable=False, default="OPEN", index=True)
    
    recommendation = Column(String, nullable=True)
    evidence = Column(PortableJSON, nullable=True)
    risk_factors = Column(PortableJSON, nullable=True)
    
    detected_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    scan = relationship("Scan", back_populates="findings")
