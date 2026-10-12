from typing import Optional, Tuple, Dict, Any, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token, TokenExpiredError, TokenInvalidError
from app.models.user import User
from app.models.revoked_token import RevokedToken
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember

bearer_scheme = HTTPBearer(auto_error=False)

async def get_current_user_and_token(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Tuple[User, Dict[str, Any]]:
    """
    Validate incoming Bearer token, check revocation blocklist,
    and resolve active user.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except TokenInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check server-side revocation list
    jti = payload.get("jti")
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing jti claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    revoked = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
    if revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Load user
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account",
        )

    return user, payload

async def get_current_user(
    auth_data: Tuple[User, Dict[str, Any]] = Depends(get_current_user_and_token)
) -> User:
    """Dependency that returns the authenticated active User object."""
    return auth_data[0]

async def get_current_user_optional(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[User]:
    """Dependency that returns the User if valid Bearer token provided, or None if unauthenticated."""
    if not credentials or not credentials.credentials:
        return None
    try:
        user, _ = await get_current_user_and_token(db=db, credentials=credentials)
        return user
    except HTTPException:
        return None

async def get_current_token_payload(
    auth_data: Tuple[User, Dict[str, Any]] = Depends(get_current_user_and_token)
) -> Dict[str, Any]:
    """Dependency that returns the validated token payload."""
    return auth_data[1]

# -----------------------------------------------------------------------------
# Workspace Authorization Dependencies & IDOR Protection
# -----------------------------------------------------------------------------

async def get_workspace_and_membership(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Tuple[Workspace, WorkspaceMember]:
    """
    Verify workspace existence and current user's membership.
    Protects against IDOR (cross-workspace unauthorized access).
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

    return workspace, membership

def require_workspace_role(*allowed_roles: str):
    """
    Reusable authorization factory that verifies the authenticated user
    possesses one of the specified workspace roles.
    """
    async def role_checker(
        data: Tuple[Workspace, WorkspaceMember] = Depends(get_workspace_and_membership),
    ) -> Tuple[Workspace, WorkspaceMember]:
        workspace, membership = data
        if membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: operation requires role in {list(allowed_roles)} (current: {membership.role})",
            )
        return workspace, membership

    return role_checker

# Standard role guards
require_workspace_viewer_or_above = require_workspace_role("OWNER", "ADMIN", "MEMBER", "VIEWER")
require_workspace_member_or_above = require_workspace_role("OWNER", "ADMIN", "MEMBER")
require_workspace_admin_or_owner = require_workspace_role("OWNER", "ADMIN")
require_workspace_owner = require_workspace_role("OWNER")
