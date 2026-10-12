"""
Pydantic schemas package.
"""
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    TokenResponse,
    LogoutResponse,
)
from app.schemas.workspace import (
    WorkspaceRole,
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
    WorkspaceResponse,
    WorkspaceMemberResponse,
    WorkspaceMemberAddRequest,
    WorkspaceMemberUpdateRequest,
)
from app.schemas.aws_connection import (
    AWSConnectionCreateRequest,
    AWSConnectionResponse,
    AWSConnectionVerifyResponse,
    AWSConnectionDeleteResponse,
)
from app.schemas.resource import (
    DiscoveredResourceData,
    ResourceResponse,
    ResourceListResponse,
    DiscoveryRunRequest,
    DiscoveryResultResponse,
)

__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "UserResponse",
    "TokenResponse",
    "LogoutResponse",
    "WorkspaceRole",
    "WorkspaceCreateRequest",
    "WorkspaceUpdateRequest",
    "WorkspaceResponse",
    "WorkspaceMemberResponse",
    "WorkspaceMemberAddRequest",
    "WorkspaceMemberUpdateRequest",
    "AWSConnectionCreateRequest",
    "AWSConnectionResponse",
    "AWSConnectionVerifyResponse",
    "AWSConnectionDeleteResponse",
    "DiscoveredResourceData",
    "ResourceResponse",
    "ResourceListResponse",
    "DiscoveryRunRequest",
    "DiscoveryResultResponse",
]
