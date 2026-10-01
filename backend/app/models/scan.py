import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Scan(Base):
    __tablename__ = "scans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    aws_connection_id = Column(String, ForeignKey("aws_connections.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="PENDING", index=True)
    
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    resources_scanned = Column(Integer, default=0)
    checks_attempted = Column(Integer, default=0)
    checks_completed = Column(Integer, default=0)
    checks_failed = Column(Integer, default=0)
    coverage_percentage = Column(Integer, default=0)
    
    security_score = Column(Integer, nullable=True)
    security_rating = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    aws_connection = relationship("AWSConnection")
    resources = relationship("CloudResource", back_populates="scan", cascade="all, delete")
    findings = relationship("Finding", back_populates="scan", cascade="all, delete")
    check_results = relationship("CheckResult", back_populates="scan", cascade="all, delete")
    category_scores = relationship("CategoryScore", back_populates="scan", cascade="all, delete")
