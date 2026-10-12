from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.api.deps import get_current_user_optional, get_current_user
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.resource import CloudResource
from app.repositories.resource import resource_repo

router = APIRouter()

@router.get("")
@router.get("/")
async def list_resources(
    workspace_id: Optional[str] = Query(None, description="Filter by workspace ID"),
    scan_id: Optional[str] = Query(None, description="Filter by scan ID"),
    service: Optional[str] = Query(None, description="Filter by service name (e.g. s3, ec2, iam, rds, cloudtrail)"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    search: Optional[str] = Query(None, description="Search term for resource name, ID, or ARN"),
    skip: int = Query(0, ge=0, description="Pagination skip"),
    limit: int = Query(100, ge=1, le=500, description="Pagination limit"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Returns a list of resources.
    - If workspace_id is provided, checks workspace membership (anti-IDOR) and returns resources for that workspace.
    - If scan_id is provided, returns resources associated with that scan.
    - Supports service, resource_type, search, and pagination filters.
    """
    query = db.query(CloudResource)

    # 1. Workspace-scoped authorization
    if workspace_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to view workspace resources",
            )

        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        # Anti-IDOR check
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

        query = query.filter(CloudResource.workspace_id == workspace_id)
    elif scan_id:
        # Legacy scan-filtered query
        query = query.filter(CloudResource.scan_id == scan_id)
    elif current_user:
        # User is authenticated but didn't pass workspace_id: show resources across their workspaces
        memberships = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).all()
        user_ws_ids = [m.workspace_id for m in memberships]
        query = query.filter(CloudResource.workspace_id.in_(user_ws_ids))

    # 2. Additional filters
    if service:
        query = query.filter(CloudResource.service == service.lower().strip())

    if resource_type:
        query = query.filter(CloudResource.resource_type == resource_type.strip())

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                CloudResource.resource_name.ilike(search_pattern),
                CloudResource.name.ilike(search_pattern),
                CloudResource.resource_id.ilike(search_pattern),
                CloudResource.arn.ilike(search_pattern),
            )
        )

    resources = query.order_by(CloudResource.discovered_at.desc()).offset(skip).limit(limit).all()

    return [
        {
            "id": r.id,
            "workspace_id": r.workspace_id,
            "aws_connection_id": r.aws_connection_id,
            "scan_id": r.scan_id,
            "resource_id": r.resource_id,
            "resource_type": r.resource_type,
            "resource_name": r.resource_name or r.name or r.resource_id,
            "name": r.resource_name or r.name or r.resource_id,
            "service": r.service,
            "region": r.region,
            "arn": r.arn,
            "status": r.status,
            "metadata": r.metadata_json or {},
            "details": r.metadata_json or {},
            "discovered_at": r.discovered_at.isoformat() if r.discovered_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in resources
    ]


@router.get("/{resource_id}")
async def get_resource(
    resource_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Retrieves a single resource by ID with workspace authorization check.
    """
    resource = db.query(CloudResource).filter(CloudResource.id == resource_id).first()
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )

    # Anti-IDOR check
    if resource.workspace_id and current_user:
        membership = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == resource.workspace_id,
                WorkspaceMember.user_id == current_user.id,
            )
            .first()
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not a member of the workspace for this resource",
            )

    return {
        "id": resource.id,
        "workspace_id": resource.workspace_id,
        "aws_connection_id": resource.aws_connection_id,
        "scan_id": resource.scan_id,
        "resource_id": resource.resource_id,
        "resource_type": resource.resource_type,
        "resource_name": resource.resource_name or resource.name or resource.resource_id,
        "name": resource.resource_name or resource.name or resource.resource_id,
        "service": resource.service,
        "region": resource.region,
        "arn": resource.arn,
        "status": resource.status,
        "metadata": resource.metadata_json or {},
        "details": resource.metadata_json or {},
        "discovered_at": resource.discovered_at.isoformat() if resource.discovered_at else None,
        "updated_at": resource.updated_at.isoformat() if resource.updated_at else None,
    }
