import uuid
from datetime import datetime, timezone
from typing import List, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import logger
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.schemas.workspace import (
    WorkspaceRole,
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
    WorkspaceResponse,
    WorkspaceMemberResponse,
    WorkspaceMemberAddRequest,
    WorkspaceMemberUpdateRequest,
)
from app.api.deps import (
    get_current_user,
    require_workspace_viewer_or_above,
    require_workspace_admin_or_owner,
    require_workspace_owner,
    get_workspace_and_membership,
)

router = APIRouter()

# -----------------------------------------------------------------------------
# Workspaces CRUD
# -----------------------------------------------------------------------------

@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace",
    description="Creates a new workspace and automatically designates the creator as OWNER.",
)
def create_workspace(
    request: WorkspaceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    workspace_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # 1. Create Workspace
    workspace = Workspace(
        id=workspace_id,
        name=request.name.strip(),
        owner_id=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(workspace)

    # 2. Add creator as OWNER member
    membership = WorkspaceMember(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        user_id=current_user.id,
        role=WorkspaceRole.OWNER.value,
        created_at=now,
    )
    db.add(membership)
    db.commit()
    db.refresh(workspace)

    logger.info(f"Workspace '{workspace.name}' ({workspace.id}) created by User {current_user.id}")

    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        owner_id=workspace.owner_id,
        current_user_role=WorkspaceRole.OWNER.value,
        member_count=1,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )

@router.get(
    "",
    response_model=List[WorkspaceResponse],
    status_code=status.HTTP_200_OK,
    summary="List user's workspaces",
    description="Returns all workspaces where the authenticated user is a member.",
)
def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[WorkspaceResponse]:
    memberships = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.user_id == current_user.id)
        .all()
    )

    results: List[WorkspaceResponse] = []
    for m in memberships:
        ws = db.query(Workspace).filter(Workspace.id == m.workspace_id).first()
        if not ws:
            continue
        member_count = (
            db.query(func.count(WorkspaceMember.id))
            .filter(WorkspaceMember.workspace_id == ws.id)
            .scalar()
            or 1
        )
        results.append(
            WorkspaceResponse(
                id=ws.id,
                name=ws.name,
                owner_id=ws.owner_id,
                current_user_role=m.role,
                member_count=member_count,
                created_at=ws.created_at,
                updated_at=ws.updated_at,
            )
        )

    return results

@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get workspace details",
    description="Returns details for a specific workspace. Requires membership (VIEWER or above).",
)
def get_workspace(
    data: Tuple[Workspace, WorkspaceMember] = Depends(require_workspace_viewer_or_above),
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    workspace, membership = data
    member_count = (
        db.query(func.count(WorkspaceMember.id))
        .filter(WorkspaceMember.workspace_id == workspace.id)
        .scalar()
        or 1
    )

    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        owner_id=workspace.owner_id,
        current_user_role=membership.role,
        member_count=member_count,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )

@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update workspace",
    description="Updates workspace name. Requires ADMIN or OWNER role.",
)
def update_workspace(
    request: WorkspaceUpdateRequest,
    data: Tuple[Workspace, WorkspaceMember] = Depends(require_workspace_admin_or_owner),
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    workspace, membership = data
    workspace.name = request.name.strip()
    workspace.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(workspace)

    member_count = (
        db.query(func.count(WorkspaceMember.id))
        .filter(WorkspaceMember.workspace_id == workspace.id)
        .scalar()
        or 1
    )

    logger.info(f"Workspace {workspace.id} updated by User {membership.user_id}")

    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        owner_id=workspace.owner_id,
        current_user_role=membership.role,
        member_count=member_count,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )

@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete workspace",
    description="Deletes workspace and all associated memberships. Requires OWNER role.",
)
def delete_workspace(
    data: Tuple[Workspace, WorkspaceMember] = Depends(require_workspace_owner),
    db: Session = Depends(get_db),
):
    workspace, membership = data
    workspace_id = workspace.id

    db.delete(workspace)
    db.commit()

    logger.info(f"Workspace {workspace_id} deleted by OWNER {membership.user_id}")
    return {"message": "Workspace deleted successfully"}

# -----------------------------------------------------------------------------
# Workspace Members Management
# -----------------------------------------------------------------------------

@router.get(
    "/{workspace_id}/members",
    response_model=List[WorkspaceMemberResponse],
    status_code=status.HTTP_200_OK,
    summary="List workspace members",
    description="Lists all members of the workspace. Requires membership (VIEWER or above).",
)
def list_workspace_members(
    data: Tuple[Workspace, WorkspaceMember] = Depends(require_workspace_viewer_or_above),
    db: Session = Depends(get_db),
) -> List[WorkspaceMemberResponse]:
    workspace, _ = data

    members = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.workspace_id == workspace.id)
        .all()
    )

    results: List[WorkspaceMemberResponse] = []
    for m in members:
        user = db.query(User).filter(User.id == m.user_id).first()
        if user:
            results.append(
                WorkspaceMemberResponse(
                    id=m.id,
                    workspace_id=m.workspace_id,
                    user_id=m.user_id,
                    email=user.email,
                    full_name=user.full_name,
                    role=m.role,
                    created_at=m.created_at,
                )
            )

    return results

@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add member to workspace",
    description="Adds an existing user to the workspace. Requires ADMIN or OWNER role.",
)
def add_workspace_member(
    request: WorkspaceMemberAddRequest,
    data: Tuple[Workspace, WorkspaceMember] = Depends(require_workspace_admin_or_owner),
    db: Session = Depends(get_db),
) -> WorkspaceMemberResponse:
    workspace, current_membership = data
    target_email = request.email.lower().strip()

    # 1. Look up user by email
    target_user = (
        db.query(User)
        .filter(func.lower(User.email) == target_email)
        .first()
    )
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with specified email not found",
        )

    # 2. Check if user is already a member
    existing_membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == target_user.id,
        )
        .first()
    )
    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this workspace",
        )

    # 3. Only OWNER can assign OWNER role
    if request.role == WorkspaceRole.OWNER and current_membership.role != WorkspaceRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the workspace owner can assign the OWNER role",
        )

    new_member = WorkspaceMember(
        id=str(uuid.uuid4()),
        workspace_id=workspace.id,
        user_id=target_user.id,
        role=request.role.value,
        created_at=datetime.now(timezone.utc),
    )
    db.add(new_member)
    db.commit()
    db.refresh(new_member)

    logger.info(f"User {target_user.id} added to Workspace {workspace.id} as {new_member.role} by {current_membership.user_id}")

    return WorkspaceMemberResponse(
        id=new_member.id,
        workspace_id=new_member.workspace_id,
        user_id=new_member.user_id,
        email=target_user.email,
        full_name=target_user.full_name,
        role=new_member.role,
        created_at=new_member.created_at,
    )

@router.patch(
    "/{workspace_id}/members/{user_id}",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Update member role",
    description="Updates role of an existing workspace member. Requires ADMIN or OWNER role.",
)
def update_workspace_member_role(
    user_id: str,
    request: WorkspaceMemberUpdateRequest,
    data: Tuple[Workspace, WorkspaceMember] = Depends(require_workspace_admin_or_owner),
    db: Session = Depends(get_db),
) -> WorkspaceMemberResponse:
    workspace, current_membership = data

    # 1. Users cannot change their own role
    if current_membership.user_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Users cannot change their own workspace role",
        )

    # 2. Find target member
    target_membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == user_id,
        )
        .first()
    )
    if not target_membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace member not found",
        )

    # 3. Cannot modify workspace owner role
    if target_membership.role == WorkspaceRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify the role of the workspace owner",
        )

    # 4. ADMIN cannot promote anyone to OWNER
    if request.role == WorkspaceRole.OWNER and current_membership.role != WorkspaceRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the workspace owner can promote members to OWNER",
        )

    # 5. ADMIN cannot modify another ADMIN's role
    if current_membership.role == WorkspaceRole.ADMIN.value and target_membership.role == WorkspaceRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins cannot modify another Admin's role. Contact the workspace Owner.",
        )

    target_membership.role = request.role.value
    db.commit()
    db.refresh(target_membership)

    user = db.query(User).filter(User.id == target_membership.user_id).first()
    email = user.email if user else ""
    full_name = user.full_name if user else ""

    logger.info(f"Role for User {user_id} in Workspace {workspace.id} updated to {target_membership.role}")

    return WorkspaceMemberResponse(
        id=target_membership.id,
        workspace_id=target_membership.workspace_id,
        user_id=target_membership.user_id,
        email=email,
        full_name=full_name,
        role=target_membership.role,
        created_at=target_membership.created_at,
    )

@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove workspace member",
    description="Removes a member from the workspace or allows a member to leave.",
)
def remove_workspace_member(
    user_id: str,
    data: Tuple[Workspace, WorkspaceMember] = Depends(require_workspace_viewer_or_above),
    db: Session = Depends(get_db),
):
    workspace, current_membership = data

    # Find target membership
    target_membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == user_id,
        )
        .first()
    )
    if not target_membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace member not found",
        )

    # Cannot remove workspace owner under any circumstance
    if target_membership.role == WorkspaceRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The workspace owner cannot be removed. Transfer ownership or delete the workspace.",
        )

    # Case A: Self-removal (leaving the workspace)
    if current_membership.user_id == user_id:
        db.delete(target_membership)
        db.commit()
        logger.info(f"User {user_id} left Workspace {workspace.id}")
        return {"message": "Successfully left the workspace"}

    # Case B: Removing another member requires ADMIN or OWNER
    if current_membership.role not in [WorkspaceRole.OWNER.value, WorkspaceRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions: requires ADMIN or OWNER role to remove members",
        )

    # ADMIN cannot remove another ADMIN
    if current_membership.role == WorkspaceRole.ADMIN.value and target_membership.role == WorkspaceRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins cannot remove another Admin. Contact the workspace Owner.",
        )

    db.delete(target_membership)
    db.commit()

    logger.info(f"User {user_id} removed from Workspace {workspace.id} by {current_membership.user_id}")
    return {"message": "Member removed successfully"}
