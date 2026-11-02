import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import logger
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.models.revoked_token import RevokedToken
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    TokenResponse,
    LogoutResponse,
)
from app.api.deps import get_current_user, get_current_token_payload

router = APIRouter()


def _ensure_user_has_workspace(db: Session, user: User) -> None:
    """
    Ensures the user has at least one real workspace with OWNER membership.
    Also repairs any owned workspace missing a WorkspaceMember row.
    """
    now = datetime.now(timezone.utc)

    owned_workspaces = db.query(Workspace).filter(Workspace.owner_id == user.id).all()
    for ws in owned_workspaces:
        existing_member = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == ws.id,
                WorkspaceMember.user_id == user.id,
            )
            .first()
        )
        if not existing_member:
            db.add(
                WorkspaceMember(
                    id=str(uuid.uuid4()),
                    workspace_id=ws.id,
                    user_id=user.id,
                    role="OWNER",
                    created_at=now,
                )
            )
            db.commit()

    has_membership = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.user_id == user.id)
        .first()
    )
    if not has_membership:
        ws_id = str(uuid.uuid4())
        default_ws = Workspace(
            id=ws_id,
            name="Personal Workspace",
            owner_id=user.id,
            created_at=now,
            updated_at=now,
        )
        db.add(default_ws)
        db.add(
            WorkspaceMember(
                id=str(uuid.uuid4()),
                workspace_id=ws_id,
                user_id=user.id,
                role="OWNER",
                created_at=now,
            )
        )
        db.commit()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new user account with unique email and secure password hashing.",
)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    # Normalize email to lower case
    normalized_email = request.email.lower().strip()

    # Check for existing user with duplicate email
    existing_user = (
        db.query(User)
        .filter(func.lower(func.trim(User.email)) == normalized_email)
        .first()
    )
    if existing_user:
        logger.warning(f"Registration attempted with existing email: {normalized_email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Hash the password securely using bcrypt
    hashed = hash_password(request.password)

    # Create new user instance
    new_user = User(
        id=str(uuid.uuid4()),
        email=normalized_email,
        password_hash=hashed,
        full_name=request.full_name.strip(),
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    _ensure_user_has_workspace(db, new_user)

    logger.info(f"User registered successfully with ID: {new_user.id}")
    return new_user

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login and obtain access token",
    description="Authenticates credentials and returns a JWT access token.",
)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    normalized_email = request.email.lower().strip()

    user = (
        db.query(User)
        .filter(func.lower(func.trim(User.email)) == normalized_email)
        .first()
    )

    # Constant-time comparison / generic error message to prevent enumeration
    if not user or not verify_password(request.password, user.password_hash):
        logger.warning(f"Failed authentication attempt for email: {normalized_email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        logger.warning(f"Login attempt for inactive user ID: {user.id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account",
        )

    _ensure_user_has_workspace(db, user)

    # Create JWT access token with unique JTI for revocation support
    access_token = create_access_token(subject=user.id)
    expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    logger.info(f"User authenticated successfully with ID: {user.id}")
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in_seconds,
        user=UserResponse.model_validate(user),
    )

@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Returns profile information for the authenticated user.",
)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    _ensure_user_has_workspace(db, current_user)
    return UserResponse.model_validate(current_user)

@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout user and revoke token",
    description="Revokes the active JWT access token server-side via token revocation blocklist.",
)
def logout(
    current_user: User = Depends(get_current_user),
    token_payload: Dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db),
) -> LogoutResponse:
    jti = token_payload.get("jti")
    exp_timestamp = token_payload.get("exp")

    if not jti or not exp_timestamp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token payload for revocation",
        )

    # Convert expiration timestamp to datetime
    expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)

    # Check if already revoked
    existing_revocation = db.query(RevokedToken).filter(RevokedToken.jti == jti).first()
    if not existing_revocation:
        revoked_token = RevokedToken(
            id=str(uuid.uuid4()),
            jti=jti,
            user_id=current_user.id,
            expires_at=expires_at,
        )
        db.add(revoked_token)
        db.commit()

    logger.info(f"Token revoked and user logged out with ID: {current_user.id}")
    return LogoutResponse(message="Successfully logged out")
