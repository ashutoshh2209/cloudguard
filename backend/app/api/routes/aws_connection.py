from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.aws_connection import AWSConnection
from app.schemas.aws_connection import (
    AWSConnectionCreateRequest,
    AWSConnectionResponse,
    AWSConnectionDeleteResponse,
)
from app.aws.schemas import ConnectRequest, ConnectResponse, StatusResponse, DisconnectResponse
from app.services.aws_connection_service import aws_connection_service

router = APIRouter()

# -----------------------------------------------------------------------------
# Part 4: Workspace-Scoped AWS Connection Endpoints
# -----------------------------------------------------------------------------

@router.post("/connections", response_model=AWSConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_aws_connection(
    request: AWSConnectionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Connect an AWS account to a workspace using an IAM Role.
    Performs STS AssumeRole + GetCallerIdentity to verify identity before saving.
    Requires OWNER or ADMIN role in the target workspace.
    Credentials are NEVER stored in the database or returned in the response.
    """
    # 1. Verify workspace existence
    workspace = db.query(Workspace).filter(Workspace.id == request.workspace_id).first()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    # 2. Verify user membership and permission (anti-IDOR)
    membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == request.workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of this workspace",
        )

    if membership.role not in ("OWNER", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions: operation requires role in ['OWNER', 'ADMIN'] (current: {membership.role})",
        )

    # 3. Create connection & verify via STS
    connection = aws_connection_service.create_connection(
        db=db,
        workspace_id=request.workspace_id,
        role_arn=request.role_arn,
        region=request.region,
        external_id=request.external_id,
    )

    return connection


@router.get("/connections", response_model=List[AWSConnectionResponse])
async def list_aws_connections(
    workspace_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List AWS connections.
    If workspace_id is provided, checks workspace membership and lists connections for it.
    If workspace_id is omitted, lists connections across all workspaces the user belongs to.
    """
    if workspace_id:
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

        return db.query(AWSConnection).filter(AWSConnection.workspace_id == workspace_id).all()

    # If no workspace_id specified, find all workspaces user belongs to
    memberships = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).all()
    user_workspace_ids = [m.workspace_id for m in memberships]

    return db.query(AWSConnection).filter(AWSConnection.workspace_id.in_(user_workspace_ids)).all()


@router.get("/connections/{connection_id}", response_model=AWSConnectionResponse)
async def get_aws_connection(
    connection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve details for a single AWS connection.
    Protects against IDOR by checking the user's workspace membership.
    """
    connection = db.query(AWSConnection).filter(AWSConnection.id == connection_id).first()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AWS connection not found",
        )

    # Check authorization against workspace
    if connection.workspace_id:
        membership = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == connection.workspace_id,
                WorkspaceMember.user_id == current_user.id,
            )
            .first()
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not a member of the workspace for this connection",
            )

    return connection


@router.delete("/connections/{connection_id}", response_model=AWSConnectionDeleteResponse)
async def delete_aws_connection(
    connection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Disconnects and deletes an AWS connection.
    Purges in-memory credentials and deletes database record.
    Requires OWNER or ADMIN role in the owning workspace.
    """
    connection = db.query(AWSConnection).filter(AWSConnection.id == connection_id).first()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AWS connection not found",
        )

    if connection.workspace_id:
        membership = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == connection.workspace_id,
                WorkspaceMember.user_id == current_user.id,
            )
            .first()
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not a member of the workspace for this connection",
            )
        if membership.role not in ("OWNER", "ADMIN"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: operation requires role in ['OWNER', 'ADMIN'] (current: {membership.role})",
            )

    aws_connection_service.delete_connection(db, connection)

    return AWSConnectionDeleteResponse(
        id=connection_id,
        message="AWS connection deleted successfully",
    )


@router.post("/connections/{connection_id}/verify", response_model=AWSConnectionResponse)
async def verify_aws_connection(
    connection_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Re-verifies an AWS connection using STS AssumeRole + GetCallerIdentity.
    Updates connection status and timestamp.
    Requires OWNER or ADMIN role in the owning workspace.
    """
    connection = db.query(AWSConnection).filter(AWSConnection.id == connection_id).first()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AWS connection not found",
        )

    if connection.workspace_id:
        membership = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == connection.workspace_id,
                WorkspaceMember.user_id == current_user.id,
            )
            .first()
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not a member of the workspace for this connection",
            )
        if membership.role not in ("OWNER", "ADMIN"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: operation requires role in ['OWNER', 'ADMIN'] (current: {membership.role})",
            )

    updated_connection = aws_connection_service.verify_connection(db, connection)
    return updated_connection


# -----------------------------------------------------------------------------
# Backward-Compatible Legacy Endpoints (Parts 1 & 2)
# -----------------------------------------------------------------------------

@router.post("/connect", response_model=ConnectResponse)
async def connect_aws(request: ConnectRequest):
    """
    Legacy connection endpoint for single-session testing.
    """
    return aws_connection_service.connect(request)


@router.get("/status", response_model=StatusResponse)
async def get_connection_status(
    workspace_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Status endpoint for current connection state.
    Checks active in-memory session first; if not active, resolves
    connected AWS account from the persisted database records.
    """
    mem_status = aws_connection_service.get_status()
    if mem_status.connected:
        return mem_status

    if workspace_id:
        conn = (
            db.query(AWSConnection)
            .filter(
                AWSConnection.workspace_id == workspace_id,
                AWSConnection.status == "CONNECTED",
            )
            .order_by(AWSConnection.updated_at.desc())
            .first()
        )
        if conn:
            return StatusResponse(
                connected=True,
                account_id=conn.account_id,
                region=conn.region,
                identity_arn=conn.role_arn,
                message="AWS account is connected",
            )
    elif current_user:
        owned_ids = [w.id for w in (current_user.owned_workspaces or [])]
        member_records = db.query(WorkspaceMember.workspace_id).filter(WorkspaceMember.user_id == current_user.id).all()
        accessible_ids = list(set(owned_ids + [m[0] for m in member_records]))
        if accessible_ids:
            conn = (
                db.query(AWSConnection)
                .filter(
                    AWSConnection.workspace_id.in_(accessible_ids),
                    AWSConnection.status == "CONNECTED",
                )
                .order_by(AWSConnection.updated_at.desc())
                .first()
            )
            if conn:
                return StatusResponse(
                    connected=True,
                    account_id=conn.account_id,
                    region=conn.region,
                    identity_arn=conn.role_arn,
                    message="AWS account is connected",
                )

    return mem_status


@router.post("/disconnect", response_model=DisconnectResponse)
async def disconnect_aws():
    """
    Legacy disconnect endpoint to clear active in-memory session.
    """
    return aws_connection_service.disconnect()
