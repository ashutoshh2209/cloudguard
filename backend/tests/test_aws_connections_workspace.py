from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from botocore.exceptions import ClientError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models import Base, User, Workspace, WorkspaceMember, AWSConnection
from app.core.database import get_db
from app.core.security import hash_password, create_access_token
from app.services.aws_connection_service import aws_connection_service

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

VALID_ROLE_ARN = "arn:aws:iam::123456789012:role/CloudGuardAuditRole"
INVALID_ROLE_ARN = "invalid-role-arn"
REGION = "us-east-1"

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def create_test_user(email: str, full_name: str) -> tuple[str, str]:
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
    user_id = user.id
    token = create_access_token(subject=user_id)
    db.close()
    return user_id, token

def create_test_workspace(owner_id: str, name: str = "Production Workspace") -> str:
    db = TestingSessionLocal()
    ws = Workspace(name=name, owner_id=owner_id)
    db.add(ws)
    db.commit()
    db.refresh(ws)
    ws_id = ws.id

    member = WorkspaceMember(workspace_id=ws_id, user_id=owner_id, role="OWNER")
    db.add(member)
    db.commit()
    db.close()
    return ws_id

def add_workspace_member(ws_id: str, user_id: str, role: str):
    db = TestingSessionLocal()
    member = WorkspaceMember(workspace_id=ws_id, user_id=user_id, role=role)
    db.add(member)
    db.commit()
    db.close()

def mock_sts_success(mock_session, mock_boto3_client, account_id="123456789012"):
    mock_sts_client = MagicMock()
    mock_boto3_client.return_value = mock_sts_client
    mock_sts_client.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "AKIAIOSFODNN7EXAMPLE",
            "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "SessionToken": "session-token-xyz-123",
        }
    }
    mock_session_instance = MagicMock()
    mock_session.return_value = mock_session_instance
    mock_session_sts_client = MagicMock()
    mock_session_instance.client.return_value = mock_session_sts_client
    mock_session_sts_client.get_caller_identity.return_value = {
        "Account": account_id,
        "Arn": f"arn:aws:sts::{account_id}:assumed-role/CloudGuardAuditRole/session",
    }
    return mock_sts_client, mock_session_sts_client


def test_unauthenticated_requests():
    """All workspace-scoped AWS endpoints must reject unauthenticated requests."""
    assert client.post("/api/v1/aws/connections", json={"role_arn": VALID_ROLE_ARN, "workspace_id": "ws-1"}).status_code == 401
    assert client.get("/api/v1/aws/connections").status_code == 401
    assert client.get("/api/v1/aws/connections/conn-1").status_code == 401
    assert client.delete("/api/v1/aws/connections/conn-1").status_code == 401
    assert client.post("/api/v1/aws/connections/conn-1/verify").status_code == 401


def test_create_connection_validation():
    """Request validation for Role ARN, region, and workspace existence."""
    alice_id, token = create_test_user("alice@cloudguard.io", "Alice")
    ws_id = create_test_workspace(alice_id)
    headers = {"Authorization": f"Bearer {token}"}

    # Invalid ARN format
    res = client.post(
        "/api/v1/aws/connections",
        json={"workspace_id": ws_id, "role_arn": INVALID_ROLE_ARN, "region": "us-east-1"},
        headers=headers,
    )
    assert res.status_code == 422

    # Invalid Region format
    res = client.post(
        "/api/v1/aws/connections",
        json={"workspace_id": ws_id, "role_arn": VALID_ROLE_ARN, "region": "invalid_region!!!"},
        headers=headers,
    )
    assert res.status_code == 422

    # Nonexistent workspace
    res = client.post(
        "/api/v1/aws/connections",
        json={"workspace_id": "nonexistent-ws", "role_arn": VALID_ROLE_ARN, "region": "us-east-1"},
        headers=headers,
    )
    assert res.status_code == 404


def test_create_connection_anti_idor_and_role_permissions():
    """Users cannot add connections to workspaces they are not members of or have only VIEWER role."""
    alice_id, alice_token = create_test_user("alice@cloudguard.io", "Alice")
    bob_id, bob_token = create_test_user("bob@cloudguard.io", "Bob")
    ws_alice_id = create_test_workspace(alice_id)

    # Bob tries to connect AWS to Alice's workspace (not a member) -> 403
    res = client.post(
        "/api/v1/aws/connections",
        json={"workspace_id": ws_alice_id, "role_arn": VALID_ROLE_ARN, "region": "us-east-1"},
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert res.status_code == 403
    assert "not a member" in res.json()["detail"].lower()

    # Bob is added as VIEWER -> 403 Insufficient permissions
    add_workspace_member(ws_alice_id, bob_id, "VIEWER")
    res = client.post(
        "/api/v1/aws/connections",
        json={"workspace_id": ws_alice_id, "role_arn": VALID_ROLE_ARN, "region": "us-east-1"},
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert res.status_code == 403
    assert "insufficient permissions" in res.json()["detail"].lower()


@patch("app.aws.connection.boto3.client")
@patch("app.aws.connection.boto3.Session")
def test_create_connection_success(mock_session, mock_boto3_client):
    """Owner successfully creates and verifies AWS connection via STS AssumeRole."""
    mock_sts_success(mock_session, mock_boto3_client)
    alice_id, token = create_test_user("alice@cloudguard.io", "Alice")
    ws_id = create_test_workspace(alice_id)

    res = client.post(
        "/api/v1/aws/connections",
        json={
            "workspace_id": ws_id,
            "role_arn": VALID_ROLE_ARN,
            "region": REGION,
            "external_id": "test-external-id",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["workspace_id"] == ws_id
    assert data["role_arn"] == VALID_ROLE_ARN
    assert data["account_id"] == "123456789012"
    assert data["region"] == REGION
    assert data["external_id"] == "test-external-id"
    assert data["status"] == "CONNECTED"
    assert "last_verified_at" in data

    # Critical security check: Never expose credentials in response
    assert "AccessKeyId" not in data
    assert "SecretAccessKey" not in data
    assert "SessionToken" not in data
    assert "credentials" not in data


@patch("app.aws.connection.boto3.client")
def test_create_connection_access_denied(mock_boto3_client):
    """AWS STS AccessDenied returns 403 and descriptive error."""
    mock_sts = MagicMock()
    mock_boto3_client.return_value = mock_sts
    mock_sts.assume_role.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access Denied by IAM policy"}},
        "AssumeRole"
    )

    alice_id, token = create_test_user("alice@cloudguard.io", "Alice")
    ws_id = create_test_workspace(alice_id)

    res = client.post(
        "/api/v1/aws/connections",
        json={"workspace_id": ws_id, "role_arn": VALID_ROLE_ARN, "region": REGION},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert "authorized to assume" in res.json()["detail"].lower()


@patch("app.aws.connection.boto3.client")
def test_create_connection_throttling(mock_boto3_client):
    """AWS STS Throttling returns 429."""
    mock_sts = MagicMock()
    mock_boto3_client.return_value = mock_sts
    mock_sts.assume_role.side_effect = ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
        "AssumeRole"
    )

    alice_id, token = create_test_user("alice@cloudguard.io", "Alice")
    ws_id = create_test_workspace(alice_id)

    res = client.post(
        "/api/v1/aws/connections",
        json={"workspace_id": ws_id, "role_arn": VALID_ROLE_ARN, "region": REGION},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 429


@patch("app.aws.connection.boto3.client")
@patch("app.aws.connection.boto3.Session")
def test_create_connection_account_id_mismatch(mock_session, mock_boto3_client):
    """If STS identity account does not match Role ARN account ID, returns 400."""
    mock_sts_success(mock_session, mock_boto3_client, account_id="999999999999")

    alice_id, token = create_test_user("alice@cloudguard.io", "Alice")
    ws_id = create_test_workspace(alice_id)

    res = client.post(
        "/api/v1/aws/connections",
        json={"workspace_id": ws_id, "role_arn": VALID_ROLE_ARN, "region": REGION},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    assert "account id mismatch" in res.json()["detail"].lower()


@patch("app.aws.connection.boto3.client")
@patch("app.aws.connection.boto3.Session")
def test_list_and_get_connections_anti_idor(mock_session, mock_boto3_client):
    """Verify list and get operations enforce multi-tenant isolation."""
    mock_sts_success(mock_session, mock_boto3_client)
    alice_id, alice_token = create_test_user("alice@cloudguard.io", "Alice")
    bob_id, bob_token = create_test_user("bob@cloudguard.io", "Bob")
    ws_alice_id = create_test_workspace(alice_id, "Alice WS")
    ws_bob_id = create_test_workspace(bob_id, "Bob WS")

    # Alice creates a connection
    created_res = client.post(
        "/api/v1/aws/connections",
        json={"workspace_id": ws_alice_id, "role_arn": VALID_ROLE_ARN, "region": REGION},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert created_res.status_code == 201
    conn_id = created_res.json()["id"]

    # Alice lists connections for her workspace
    list_res = client.get(
        f"/api/v1/aws/connections?workspace_id={ws_alice_id}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["id"] == conn_id

    # Bob tries to list Alice's workspace connections (anti-IDOR) -> 403
    bob_list_res = client.get(
        f"/api/v1/aws/connections?workspace_id={ws_alice_id}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert bob_list_res.status_code == 403

    # Alice gets single connection -> 200
    get_res = client.get(
        f"/api/v1/aws/connections/{conn_id}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert get_res.status_code == 200
    assert get_res.json()["id"] == conn_id

    # Bob tries to get Alice's connection by ID (anti-IDOR) -> 403
    bob_get_res = client.get(
        f"/api/v1/aws/connections/{conn_id}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert bob_get_res.status_code == 403


@patch("app.aws.connection.boto3.client")
@patch("app.aws.connection.boto3.Session")
def test_verify_connection_endpoint(mock_session, mock_boto3_client):
    """Test POST /api/v1/aws/connections/{id}/verify."""
    mock_sts_success(mock_session, mock_boto3_client)
    alice_id, alice_token = create_test_user("alice@cloudguard.io", "Alice")
    ws_id = create_test_workspace(alice_id)

    # 1. Create connection
    conn_res = client.post(
        "/api/v1/aws/connections",
        json={"workspace_id": ws_id, "role_arn": VALID_ROLE_ARN, "region": REGION},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    conn_id = conn_res.json()["id"]

    # 2. Re-verify successfully
    verify_res = client.post(
        f"/api/v1/aws/connections/{conn_id}/verify",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "CONNECTED"

    # 3. Verify fails when STS fails and status marks ERROR
    mock_sts_client = MagicMock()
    mock_boto3_client.return_value = mock_sts_client
    mock_sts_client.assume_role.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "IAM role trust policy was removed"}},
        "AssumeRole"
    )

    failed_verify_res = client.post(
        f"/api/v1/aws/connections/{conn_id}/verify",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert failed_verify_res.status_code == 403

    # Check that database record was updated to ERROR
    db = TestingSessionLocal()
    db_conn = db.query(AWSConnection).filter(AWSConnection.id == conn_id).first()
    assert db_conn.status == "ERROR"
    db.close()


@patch("app.aws.connection.boto3.client")
@patch("app.aws.connection.boto3.Session")
def test_delete_connection_endpoint(mock_session, mock_boto3_client):
    """Test DELETE /api/v1/aws/connections/{id} clears DB and in-memory credentials."""
    mock_sts_success(mock_session, mock_boto3_client)
    alice_id, alice_token = create_test_user("alice@cloudguard.io", "Alice")
    bob_id, bob_token = create_test_user("bob@cloudguard.io", "Bob")
    ws_id = create_test_workspace(alice_id)
    add_workspace_member(ws_id, bob_id, "VIEWER")

    # Create connection
    conn_res = client.post(
        "/api/v1/aws/connections",
        json={"workspace_id": ws_id, "role_arn": VALID_ROLE_ARN, "region": REGION},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    conn_id = conn_res.json()["id"]

    # Verify credentials in memory
    assert aws_connection_service.get_credentials(conn_id) is not None

    # Bob (VIEWER) tries to delete -> 403
    res_viewer = client.delete(
        f"/api/v1/aws/connections/{conn_id}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert res_viewer.status_code == 403

    # Alice (OWNER) deletes -> 200
    res_owner = client.delete(
        f"/api/v1/aws/connections/{conn_id}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_owner.status_code == 200
    assert res_owner.json()["message"] == "AWS connection deleted successfully"

    # Verify connection was removed from DB and in-memory store
    db = TestingSessionLocal()
    assert db.query(AWSConnection).filter(AWSConnection.id == conn_id).first() is None
    db.close()
    assert aws_connection_service.get_credentials(conn_id) is None
