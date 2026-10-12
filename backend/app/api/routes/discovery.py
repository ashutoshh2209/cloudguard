from typing import Optional, Union, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user_optional, get_current_user
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.schemas.inventory import ResourceInventory
from app.schemas.resource import (
    DiscoveryRunRequest,
    DiscoveryResultResponse,
)
from app.services.discovery_service import discovery_service

router = APIRouter()

@router.post("/run", response_model=Union[DiscoveryResultResponse, ResourceInventory])
async def run_discovery(
    request: Optional[DiscoveryRunRequest] = None,
    workspace_id: Optional[str] = Query(None, description="Optional workspace ID query parameter"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Triggers AWS resource discovery.
    - When workspace_id is provided, requires authentication and workspace membership (OWNER, ADMIN, MEMBER).
      Discovers resources across EC2, S3, IAM, Security Groups, RDS, and CloudTrail, persisting them to the database.
    - When workspace_id is omitted (legacy), uses in-memory AWS connection.
    """
    target_workspace_id = (request.workspace_id if request and request.workspace_id else None) or workspace_id

    if target_workspace_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to run discovery for a workspace",
            )

        workspace = db.query(Workspace).filter(Workspace.id == target_workspace_id).first()
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        # Anti-IDOR: Check membership
        membership = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == target_workspace_id,
                WorkspaceMember.user_id == current_user.id,
            )
            .first()
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not a member of this workspace",
            )

        if membership.role == "VIEWER":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions: Viewers cannot trigger resource discovery",
            )

        connection_id = request.connection_id if request else None
        return discovery_service.discover_workspace_resources(
            db=db,
            workspace_id=target_workspace_id,
            connection_id=connection_id,
        )

    # Legacy invocation (Part 1 compatibility)
    return discovery_service.run_discovery()


@router.post("/workspaces/{workspace_id}", response_model=DiscoveryResultResponse)
async def run_workspace_discovery(
    workspace_id: str,
    connection_id: Optional[str] = Query(None, description="Optional specific connection ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Explicit endpoint to trigger resource discovery for a specific workspace.
    Requires workspace membership with OWNER, ADMIN, or MEMBER role.
    """
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of this workspace",
        )

    if membership.role == "VIEWER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions: Viewers cannot trigger resource discovery",
        )

    return discovery_service.discover_workspace_resources(
        db=db,
        workspace_id=workspace_id,
        connection_id=connection_id,
    )
