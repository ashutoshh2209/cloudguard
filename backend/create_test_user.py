"""
Script to create or verify a test user in CloudGuard.
Usage:
    python create_test_user.py [email] [password] [full_name]
Defaults:
    email: demo@cloudguard.io
    password: Password123!
    full_name: Security Lead
"""
import sys
import uuid
from app.core.database import SessionLocal
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.core.security import hash_password

def ensure_test_user(
    email: str = "demo@cloudguard.io",
    password: str = "Password123!",
    full_name: str = "Security Lead"
):
    db = SessionLocal()
    try:
        normalized_email = email.lower().strip()
        user = db.query(User).filter(User.email == normalized_email).first()
        
        if not user:
            user = User(
                id=str(uuid.uuid4()),
                email=normalized_email,
                password_hash=hash_password(password),
                full_name=full_name,
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Created new user: {normalized_email} (ID: {user.id})")
        else:
            user.password_hash = hash_password(password)
            user.is_active = True
            db.commit()
            print(f"Updated password for existing user: {normalized_email} (ID: {user.id})")

        # Ensure default workspace exists
        membership = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user.id).first()
        if not membership:
            ws_id = str(uuid.uuid4())
            workspace = Workspace(
                id=ws_id,
                name="Personal Workspace",
                owner_id=user.id,
            )
            db.add(workspace)
            membership = WorkspaceMember(
                id=str(uuid.uuid4()),
                workspace_id=ws_id,
                user_id=user.id,
                role="OWNER",
            )
            db.add(membership)
            db.commit()
            print(f"Created default workspace for {normalized_email}")
        else:
            print(f"User {normalized_email} already has a workspace.")

        return user
    finally:
        db.close()

if __name__ == "__main__":
    email_arg = sys.argv[1] if len(sys.argv) > 1 else "demo@cloudguard.io"
    pass_arg = sys.argv[2] if len(sys.argv) > 2 else "Password123!"
    name_arg = sys.argv[3] if len(sys.argv) > 3 else "Security Lead"
    ensure_test_user(email_arg, pass_arg, name_arg)
