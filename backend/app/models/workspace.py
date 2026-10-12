import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    owner_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_workspaces")
    members = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")
    aws_connections = relationship("AWSConnection", back_populates="workspace", cascade="all, delete-orphan")
    resources = relationship("CloudResource", back_populates="workspace", cascade="all, delete-orphan")
    scans = relationship("Scan", back_populates="workspace", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="workspace", cascade="all, delete-orphan")
    reports = relationship("SecurityReport", back_populates="workspace", cascade="all, delete-orphan")
