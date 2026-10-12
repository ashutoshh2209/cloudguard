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
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True)
    aws_connection_id = Column(String, ForeignKey("aws_connections.id", ondelete="CASCADE"), nullable=True, index=True)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=True, index=True)
    
    service = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=False, index=True)
    resource_id = Column(String, nullable=False, index=True)
    resource_name = Column(String, nullable=True)
    name = Column(String, nullable=True)
    region = Column(String, nullable=False, index=True)
    arn = Column(String, nullable=True, index=True)
    
    status = Column(String, nullable=False, default="active")
    
    metadata_json = Column(PortableJSON, nullable=True)
    
    discovered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="resources")
    aws_connection = relationship("AWSConnection", backref="resources")
    scan = relationship("Scan", back_populates="resources")
