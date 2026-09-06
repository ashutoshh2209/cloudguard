import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from app.database.base import Base

class AWSConnection(Base):
    __tablename__ = "aws_connections"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String, nullable=False, unique=True, index=True)
    role_arn = Column(String, nullable=False)
    region = Column(String, nullable=False)
    status = Column(String, nullable=False, default="verified")
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_verified_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
