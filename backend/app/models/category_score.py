import uuid
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class CategoryScore(Base):
    __tablename__ = "category_scores"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False, index=True)
    category = Column(String, nullable=False)
    
    score = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    
    finding_count = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)

    # Relationships
    scan = relationship("Scan", back_populates="category_scores")
