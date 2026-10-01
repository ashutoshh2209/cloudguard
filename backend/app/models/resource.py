import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

PortableJSON = JSON().with_variant(JSONB, 'postgresql')

class CloudResource(Base):
    __tablename__ = "resources"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False, index=True)
    aws_connection_id = Column(String, ForeignKey("aws_connections.id"), nullable=False)
    
    resource_id = Column(String, nullable=False)
    resource_type = Column(String, nullable=False, index=True)
    service = Column(String, nullable=False, index=True)
    name = Column(String, nullable=True)
    region = Column(String, nullable=False, index=True)
    
    status = Column(String, nullable=False, default="active")
    
    metadata_json = Column(PortableJSON, nullable=True) # Using PortableJSON for flexible AWS metadata
    
    discovered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    scan = relationship("Scan", back_populates="resources")
