import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models import Base, User, Workspace, WorkspaceMember
from app.core.database import get_db
from app.core.security import hash_password, create_access_token

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def create_test_user(email: str, full_name: str) -> tuple[User, str]:
    db = TestingSessionLocal()
    user = User(
        email=email,
        password_hash=hash_password("Password123!"),
        full_name=full_name,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(subject=user.id)
    db.close()
    return user, token

def test_unauthenticated_requests():
    # Workspace operations must reject unauthenticated requests with 401
    assert client.post("/api/v1/workspaces", json={"name": "WS"}).status_code == 401
    assert client.get("/api/v1/workspaces").status_code == 401
    assert client.get("/api/v1/workspaces/ws-123").status_code == 401
    assert client.patch("/api/v1/workspaces/ws-123", json={"name": "WS2"}).status_code == 401
    assert client.delete("/api/v1/workspaces/ws-123").status_code == 401
    assert client.get("/api/v1/workspaces/ws-123/members").status_code == 401
    assert client.post("/api/v1/workspaces/ws-123/members", json={"email": "a@b.com"}).status_code == 401

def test_workspace_creation():
    user, token = create_test_user("alice@cloudguard.io", "Alice Smith")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/workspaces",
        json={"name": "Production Environment"},
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Production Environment"
    assert data["owner_id"] == user.id
    assert data["current_user_role"] == "OWNER"
    assert data["member_count"] == 1
    assert "id" in data

def test_workspace_listing():
    user1, token1 = create_test_user("user1@cloudguard.io", "User One")
    user2, token2 = create_test_user("user2@cloudguard.io", "User Two")

    h1 = {"Authorization": f"Bearer {token1}"}
    h2 = {"Authorization": f"Bearer {token2}"}

    client.post("/api/v1/workspaces", json={"name": "U1 WS A"}, headers=h1)
    client.post("/api/v1/workspaces", json={"name": "U1 WS B"}, headers=h1)
    client.post("/api/v1/workspaces", json={"name": "U2 WS C"}, headers=h2)

    res1 = client.get("/api/v1/workspaces", headers=h1)
    assert res1.status_code == 200
    workspaces1 = res1.json()
    assert len(workspaces1) == 2
    names1 = [w["name"] for w in workspaces1]
    assert "U1 WS A" in names1 and "U1 WS B" in names1
    assert "U2 WS C" not in names1

    res2 = client.get("/api/v1/workspaces", headers=h2)
    assert res2.status_code == 200
    workspaces2 = res2.json()
    assert len(workspaces2) == 1
    assert workspaces2[0]["name"] == "U2 WS C"

def test_workspace_access():
    user, token = create_test_user("carol@cloudguard.io", "Carol")
    h = {"Authorization": f"Bearer {token}"}

    ws = client.post("/api/v1/workspaces", json={"name": "Carol's Team"}, headers=h).json()
    ws_id = ws["id"]

    res = client.get(f"/api/v1/workspaces/{ws_id}", headers=h)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == ws_id
    assert data["name"] == "Carol's Team"
    assert data["current_user_role"] == "OWNER"

def test_workspace_update():
    user, token = create_test_user("dan@cloudguard.io", "Dan")
    h = {"Authorization": f"Bearer {token}"}

    ws = client.post("/api/v1/workspaces", json={"name": "Original Name"}, headers=h).json()
    ws_id = ws["id"]

    update_res = client.patch(
        f"/api/v1/workspaces/{ws_id}",
        json={"name": "Renamed Workspace"},
        headers=h,
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Renamed Workspace"

    get_res = client.get(f"/api/v1/workspaces/{ws_id}", headers=h)
    assert get_res.json()["name"] == "Renamed Workspace"

def test_workspace_deletion():
    user, token = create_test_user("eva@cloudguard.io", "Eva")
    h = {"Authorization": f"Bearer {token}"}

    ws = client.post("/api/v1/workspaces", json={"name": "Temporary WS"}, headers=h).json()
    ws_id = ws["id"]

    del_res = client.delete(f"/api/v1/workspaces/{ws_id}", headers=h)
    assert del_res.status_code == 200
    assert "deleted" in del_res.json()["message"].lower()

    # Workspace should no longer exist
    get_res = client.get(f"/api/v1/workspaces/{ws_id}", headers=h)
    assert get_res.status_code == 404

def test_adding_members():
    owner, owner_token = create_test_user("owner@cloudguard.io", "Owner User")
    member, _ = create_test_user("colleague@cloudguard.io", "Colleague User")

    owner_h = {"Authorization": f"Bearer {owner_token}"}
    ws = client.post("/api/v1/workspaces", json={"name": "Collab WS"}, headers=owner_h).json()
    ws_id = ws["id"]

    # 1. Successfully add member
    add_res = client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": "colleague@cloudguard.io", "role": "MEMBER"},
        headers=owner_h,
    )
    assert add_res.status_code == 201
    member_data = add_res.json()
    assert member_data["email"] == "colleague@cloudguard.io"
    assert member_data["role"] == "MEMBER"

    # 2. Duplicate addition rejected
    dup_res = client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": "colleague@cloudguard.io", "role": "MEMBER"},
        headers=owner_h,
    )
    assert dup_res.status_code == 400
    assert "already a member" in dup_res.json()["detail"].lower()

    # 3. Adding non-existent user rejected
    non_existent_res = client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": "ghost@nowhere.com", "role": "MEMBER"},
        headers=owner_h,
    )
    assert non_existent_res.status_code == 404

def test_changing_roles():
    owner, owner_token = create_test_user("boss@cloudguard.io", "Boss")
    user, user_token = create_test_user("worker@cloudguard.io", "Worker")

    owner_h = {"Authorization": f"Bearer {owner_token}"}
    user_h = {"Authorization": f"Bearer {user_token}"}

    ws = client.post("/api/v1/workspaces", json={"name": "Role Test WS"}, headers=owner_h).json()
    ws_id = ws["id"]

    client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": "worker@cloudguard.io", "role": "MEMBER"},
        headers=owner_h,
    )

    # 1. Owner promotes worker to ADMIN
    promote_res = client.patch(
        f"/api/v1/workspaces/{ws_id}/members/{user.id}",
        json={"role": "ADMIN"},
        headers=owner_h,
    )
    assert promote_res.status_code == 200
    assert promote_res.json()["role"] == "ADMIN"

    # 2. Worker cannot change own role
    self_change_res = client.patch(
        f"/api/v1/workspaces/{ws_id}/members/{user.id}",
        json={"role": "MEMBER"},
        headers=user_h,
    )
    assert self_change_res.status_code == 400
    assert "cannot change their own" in self_change_res.json()["detail"].lower()

    # 3. ADMIN cannot demote the OWNER
    demote_owner_res = client.patch(
        f"/api/v1/workspaces/{ws_id}/members/{owner.id}",
        json={"role": "VIEWER"},
        headers=user_h,
    )
    assert demote_owner_res.status_code == 403
    assert "owner" in demote_owner_res.json()["detail"].lower()

def test_removing_members():
    owner, owner_token = create_test_user("chief@cloudguard.io", "Chief")
    user, user_token = create_test_user("temp@cloudguard.io", "Temp User")

    owner_h = {"Authorization": f"Bearer {owner_token}"}
    user_h = {"Authorization": f"Bearer {user_token}"}

    ws = client.post("/api/v1/workspaces", json={"name": "Removal WS"}, headers=owner_h).json()
    ws_id = ws["id"]

    client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": "temp@cloudguard.io", "role": "MEMBER"},
        headers=owner_h,
    )

    # 1. Owner cannot be removed
    rem_owner_res = client.delete(f"/api/v1/workspaces/{ws_id}/members/{owner.id}", headers=owner_h)
    assert rem_owner_res.status_code == 400
    assert "owner cannot be removed" in rem_owner_res.json()["detail"].lower()

    # 2. User can leave workspace
    leave_res = client.delete(f"/api/v1/workspaces/{ws_id}/members/{user.id}", headers=user_h)
    assert leave_res.status_code == 200
    assert "left the workspace" in leave_res.json()["message"].lower()

    # 3. User is no longer a member
    get_res = client.get(f"/api/v1/workspaces/{ws_id}", headers=user_h)
    assert get_res.status_code == 403

def test_cross_workspace_access_denial_idor():
    user_a, token_a = create_test_user("alice_idor@cloudguard.io", "Alice IDOR")
    user_b, token_b = create_test_user("bob_idor@cloudguard.io", "Bob IDOR")

    ha = {"Authorization": f"Bearer {token_a}"}
    hb = {"Authorization": f"Bearer {token_b}"}

    # Bob creates workspace B
    ws_b = client.post("/api/v1/workspaces", json={"name": "Bob's Secret Workspace"}, headers=hb).json()
    ws_b_id = ws_b["id"]

    # Critical Security Test: Alice attempts IDOR access to Bob's workspace
    # 1. Alice attempts to read Bob's workspace
    read_res = client.get(f"/api/v1/workspaces/{ws_b_id}", headers=ha)
    assert read_res.status_code == 403
    assert "not a member" in read_res.json()["detail"].lower()

    # 2. Alice attempts to update Bob's workspace
    update_res = client.patch(f"/api/v1/workspaces/{ws_b_id}", json={"name": "Hacked Name"}, headers=ha)
    assert update_res.status_code == 403

    # 3. Alice attempts to delete Bob's workspace
    delete_res = client.delete(f"/api/v1/workspaces/{ws_b_id}", headers=ha)
    assert delete_res.status_code == 403

    # 4. Alice attempts to list Bob's workspace members
    members_res = client.get(f"/api/v1/workspaces/{ws_b_id}/members", headers=ha)
    assert members_res.status_code == 403

    # 5. Alice attempts to inject a member into Bob's workspace
    inject_res = client.post(
        f"/api/v1/workspaces/{ws_b_id}/members",
        json={"email": "alice_idor@cloudguard.io", "role": "OWNER"},
        headers=ha,
    )
    assert inject_res.status_code == 403

def test_viewer_restrictions():
    owner, owner_token = create_test_user("v_owner@cloudguard.io", "Viewer Owner")
    viewer, viewer_token = create_test_user("v_viewer@cloudguard.io", "Readonly Viewer")
    other, _ = create_test_user("v_other@cloudguard.io", "Other User")

    owner_h = {"Authorization": f"Bearer {owner_token}"}
    viewer_h = {"Authorization": f"Bearer {viewer_token}"}

    ws = client.post("/api/v1/workspaces", json={"name": "Viewer Test WS"}, headers=owner_h).json()
    ws_id = ws["id"]

    # Add as VIEWER
    client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": "v_viewer@cloudguard.io", "role": "VIEWER"},
        headers=owner_h,
    )

    # 1. VIEWER CAN read workspace details
    assert client.get(f"/api/v1/workspaces/{ws_id}", headers=viewer_h).status_code == 200

    # 2. VIEWER CAN read members list
    assert client.get(f"/api/v1/workspaces/{ws_id}/members", headers=viewer_h).status_code == 200

    # 3. VIEWER CANNOT update workspace (requires ADMIN/OWNER)
    assert client.patch(f"/api/v1/workspaces/{ws_id}", json={"name": "New"}, headers=viewer_h).status_code == 403

    # 4. VIEWER CANNOT delete workspace (requires OWNER)
    assert client.delete(f"/api/v1/workspaces/{ws_id}", headers=viewer_h).status_code == 403

    # 5. VIEWER CANNOT add members (requires ADMIN/OWNER)
    assert client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": "v_other@cloudguard.io", "role": "MEMBER"},
        headers=viewer_h,
    ).status_code == 403

    # 6. VIEWER CANNOT update roles (requires ADMIN/OWNER)
    assert client.patch(
        f"/api/v1/workspaces/{ws_id}/members/{owner.id}",
        json={"role": "MEMBER"},
        headers=viewer_h,
    ).status_code == 403


def test_register_and_login_auto_provision_default_workspace_with_owner_role():
    # Register a brand-new user through the auth endpoint
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@cloudguard.io",
            "password": "StrongPassword123!",
            "full_name": "New CloudGuard User",
        },
    )
    assert reg_res.status_code == 201

    # Login and verify a real default workspace with OWNER membership exists immediately
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "newuser@cloudguard.io",
            "password": "StrongPassword123!",
        },
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Simulate page reload: /auth/me + /workspaces
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200

    ws_res = client.get("/api/v1/workspaces", headers=headers)
    assert ws_res.status_code == 200
    workspaces = ws_res.json()
    assert len(workspaces) == 1
    default_ws = workspaces[0]
    assert default_ws["name"] == "Personal Workspace"
    assert default_ws["current_user_role"] == "OWNER"
    assert default_ws["member_count"] == 1

    # Verify Settings -> Workspace & Members endpoint returns the OWNER member
    members_res = client.get(f"/api/v1/workspaces/{default_ws['id']}/members", headers=headers)
    assert members_res.status_code == 200
    members = members_res.json()
    assert len(members) == 1
    assert members[0]["email"] == "newuser@cloudguard.io"
    assert members[0]["role"] == "OWNER"


def test_workspace_selection_reload_and_aws_connection_authorization(monkeypatch):
    from app.aws.sts_service import aws_sts_service

    # Mock STS verify_role so no real AWS call is made during unit test
    def fake_verify_role(role_arn: str, region: str = "us-east-1", external_id=None):
        return {
            "credentials": {
                "AccessKeyId": "ASIAFAKEACCESSKEY123",
                "SecretAccessKey": "fakeSecretKey1234567890",
                "SessionToken": "fakeSessionToken1234567890",
            },
            "identity": {
                "account_id": "123456789012",
                "identity_arn": "arn:aws:sts::123456789012:assumed-role/CloudGuardAuditRole/cloudguard-audit-session",
            },
            "account_id": "123456789012",
            "identity_arn": "arn:aws:sts::123456789012:assumed-role/CloudGuardAuditRole/cloudguard-audit-session",
        }

    monkeypatch.setattr(aws_sts_service, "verify_role", fake_verify_role)

    # 1. User logs in and gets default workspace
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "awsowner@cloudguard.io",
            "password": "StrongPassword123!",
            "full_name": "AWS Owner",
        },
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "awsowner@cloudguard.io", "password": "StrongPassword123!"},
    ).json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {token}"}

    # 2. User creates a new workspace and selects it
    created_ws = client.post(
        "/api/v1/workspaces",
        json={"name": "Production AWS Workspace"},
        headers=owner_headers,
    )
    assert created_ws.status_code == 201
    selected_ws_id = created_ws.json()["id"]
    assert created_ws.json()["current_user_role"] == "OWNER"

    # 3. Simulate page refresh: list workspaces and verify selected_ws_id is present with OWNER role
    listed = client.get("/api/v1/workspaces", headers=owner_headers).json()
    matching = [w for w in listed if w["id"] == selected_ws_id]
    assert len(matching) == 1
    assert matching[0]["name"] == "Production AWS Workspace"
    assert matching[0]["current_user_role"] == "OWNER"

    # 4. Connect AWS account using the selected workspace ID (OWNER authorized)
    conn_res = client.post(
        "/api/v1/aws/connections",
        json={
            "workspace_id": selected_ws_id,
            "role_arn": "arn:aws:iam::123456789012:role/CloudGuardAuditRole",
            "region": "us-east-1",
            "external_id": "ext-123456",
        },
        headers=owner_headers,
    )
    assert conn_res.status_code == 201
    conn_data = conn_res.json()
    assert conn_data["workspace_id"] == selected_ws_id
    assert conn_data["account_id"] == "123456789012"
    assert conn_data["status"] == "CONNECTED"

    # 5. Verify listing connections for the selected workspace returns the connection
    list_conn_res = client.get(
        f"/api/v1/aws/connections?workspace_id={selected_ws_id}",
        headers=owner_headers,
    )
    assert list_conn_res.status_code == 200
    assert len(list_conn_res.json()) == 1
    assert list_conn_res.json()[0]["id"] == conn_data["id"]

    # 6. Verify a VIEWER in that workspace is forbidden from creating/modifying AWS connections
    _, viewer_token = create_test_user("viewer_aws@cloudguard.io", "Viewer AWS")
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
    client.post(
        f"/api/v1/workspaces/{selected_ws_id}/members",
        json={"email": "viewer_aws@cloudguard.io", "role": "VIEWER"},
        headers=owner_headers,
    )
    viewer_conn_res = client.post(
        "/api/v1/aws/connections",
        json={
            "workspace_id": selected_ws_id,
            "role_arn": "arn:aws:iam::123456789012:role/AnotherRole",
            "region": "us-east-1",
        },
        headers=viewer_headers,
    )
    assert viewer_conn_res.status_code == 403

