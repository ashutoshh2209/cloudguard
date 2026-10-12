from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class WorkspaceRole(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"

class WorkspaceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Workspace name")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Workspace name cannot be empty or blank")
        return trimmed

class WorkspaceUpdateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Workspace name")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Workspace name cannot be empty or blank")
        return trimmed

class WorkspaceResponse(BaseModel):
    id: str
    name: str
    owner_id: str
    current_user_role: Optional[str] = None
    member_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WorkspaceMemberResponse(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    email: str
    full_name: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WorkspaceMemberAddRequest(BaseModel):
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.MEMBER

class WorkspaceMemberUpdateRequest(BaseModel):
    role: WorkspaceRole
