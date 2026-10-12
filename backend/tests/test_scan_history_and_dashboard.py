import pytest
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models import (
    Base,
    User,
    Workspace,
    WorkspaceMember,
    Scan,
    Finding as FindingModel,
    CategoryScore as CategoryScoreModel,
    CheckResult as CheckResultModel,
    AWSConnection,
)
from app.core.database import get_db
from app.core.security import hash_password, create_access_token


SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
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


def create_user(email: str, name: str) -> tuple[User, str]:
    db = TestingSessionLocal()
    user = User(
        email=email,
        password_hash=hash_password("SecurePass123!"),
        full_name=name,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(subject=user.id)
    db.close()
    return user, token


def create_workspace(owner: User, name: str) -> Workspace:
    db = TestingSessionLocal()
    ws = Workspace(name=name, owner_id=owner.id)
    db.add(ws)
    db.commit()
    db.refresh(ws)
    db.close()
    return ws


def add_member(workspace_id: str, user_id: str, role: str):
    db = TestingSessionLocal()
    m = WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role=role)
    db.add(m)
    db.commit()
    db.close()


def create_mock_scan(
    workspace_id: str,
    status: str = "COMPLETED",
    score: int = 80,
    rating: str = "Good",
    hours_ago: int = 1,
    connection_id: str = None,
) -> Scan:
    db = TestingSessionLocal()
    scan_id = str(uuid.uuid4())
    started = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    completed = started + timedelta(minutes=5) if status in ("COMPLETED", "PARTIAL") else None
    
    scan = Scan(
        id=scan_id,
        workspace_id=workspace_id,
        aws_connection_id=connection_id or str(uuid.uuid4()),
        status=status,
        started_at=started,
        completed_at=completed,
        created_at=started,
        resources_scanned=25,
        checks_attempted=50,
        checks_completed=50,
        checks_failed=5 if status != "FAILED" else 0,
        checks_passed=45 if status != "FAILED" else 0,
        checks_errored=0,
        coverage_percentage=92.5,
        security_score=score if status in ("COMPLETED", "PARTIAL") else None,
        security_rating=rating if status in ("COMPLETED", "PARTIAL") else None,
    )
    db.add(scan)
    db.commit()

    # Add sample check result
    cr = CheckResultModel(
        id=str(uuid.uuid4()),
        scan_id=scan.id,
        resource_id="arn:aws:s3:::test-bucket-1",
        rule_id="S3_BUCKET_PUBLIC_ACCESS_BLOCK",
        status="PASS",
        message="Bucket public access is blocked",
        checked_at=started,
    )
    db.add(cr)

    # Add sample category scores
    cs = CategoryScoreModel(
        id=str(uuid.uuid4()),
        scan_id=scan.id,
        category="s3",
        score=score,
        status="SECURE" if score >= 80 else "WARNING",
        finding_count=1,
        critical_count=0,
        high_count=1,
    )
    db.add(cs)

    # Add sample finding
    f = FindingModel(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        scan_id=scan.id,
        rule_id="S3_ENCRYPTION_DISABLED",
        title="S3 Default Encryption Disabled",
        severity="HIGH",
        category="s3",
        risk_score=75,
        priority="P2",
        service="s3",
        region="us-east-1",
        resource_id="arn:aws:s3:::test-bucket-1",
        status="OPEN",
        detected_at=started,
    )
    db.add(f)

    db.commit()
    db.refresh(scan)
    db.close()
    return scan


# ==============================================================================
# 1. SCAN HISTORY LIST & PAGINATION & FILTERING TESTS
# ==============================================================================

def test_scans_empty_state():
    user, token = create_user("owner1@test.com", "Owner One")
    ws = create_workspace(user, "Workspace A")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/v1/scans?workspace_id={ws.id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_scans_pagination_and_sorting():
    user, token = create_user("owner2@test.com", "Owner Two")
    ws = create_workspace(user, "Workspace B")
    headers = {"Authorization": f"Bearer {token}"}

    # Create 3 scans at different times: 3 hours ago, 2 hours ago, 1 hour ago
    s1 = create_mock_scan(ws.id, score=70, hours_ago=3)
    s2 = create_mock_scan(ws.id, score=80, hours_ago=2)
    s3 = create_mock_scan(ws.id, score=90, hours_ago=1)

    # Default listing: newest first (s3, then s2, then s1)
    res = client.get(f"/api/v1/scans?workspace_id={ws.id}", headers=headers)
    assert res.status_code == 200
    scans = res.json()
    assert len(scans) == 3
    assert scans[0]["id"] == s3.id
    assert scans[1]["id"] == s2.id
    assert scans[2]["id"] == s1.id

    # Test limit=2
    res_limit = client.get(f"/api/v1/scans?workspace_id={ws.id}&limit=2", headers=headers)
    assert res_limit.status_code == 200
    data_limit = res_limit.json()
    assert len(data_limit) == 2
    assert data_limit[0]["id"] == s3.id
    assert data_limit[1]["id"] == s2.id

    # Test skip=1&limit=1
    res_skip = client.get(f"/api/v1/scans?workspace_id={ws.id}&skip=1&limit=1", headers=headers)
    assert res_skip.status_code == 200
    data_skip = res_skip.json()
    assert len(data_skip) == 1
    assert data_skip[0]["id"] == s2.id


def test_scans_status_filtering():
    user, token = create_user("owner3@test.com", "Owner Three")
    ws = create_workspace(user, "Workspace C")
    headers = {"Authorization": f"Bearer {token}"}

    create_mock_scan(ws.id, status="COMPLETED", score=85, hours_ago=3)
    create_mock_scan(ws.id, status="FAILED", hours_ago=2)
    create_mock_scan(ws.id, status="PARTIAL", score=65, hours_ago=1)

    # Filter COMPLETED
    res_comp = client.get(f"/api/v1/scans?workspace_id={ws.id}&status=COMPLETED", headers=headers)
    assert res_comp.status_code == 200
    assert len(res_comp.json()) == 1
    assert res_comp.json()[0]["status"] == "COMPLETED"

    # Filter FAILED
    res_fail = client.get(f"/api/v1/scans?workspace_id={ws.id}&status=FAILED", headers=headers)
    assert res_fail.status_code == 200
    assert len(res_fail.json()) == 1
    assert res_fail.json()[0]["status"] == "FAILED"

    # Filter PARTIAL
    res_part = client.get(f"/api/v1/scans?workspace_id={ws.id}&status=PARTIAL", headers=headers)
    assert res_part.status_code == 200
    assert len(res_part.json()) == 1
    assert res_part.json()[0]["status"] == "PARTIAL"


def test_scans_anti_idor_and_membership():
    owner_a, token_a = create_user("user_a@test.com", "User A")
    owner_b, token_b = create_user("user_b@test.com", "User B")
    ws_a = create_workspace(owner_a, "Workspace Alpha")
    ws_b = create_workspace(owner_b, "Workspace Beta")

    create_mock_scan(ws_a.id, score=90)
    create_mock_scan(ws_b.id, score=60)

    # User B tries to list User A's workspace scans -> 403 Forbidden
    res_idor = client.get(f"/api/v1/scans?workspace_id={ws_a.id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res_idor.status_code == 403

    # Add User B as VIEWER to Workspace A
    add_member(ws_a.id, owner_b.id, "VIEWER")

    # Now User B can view scans in Workspace A
    res_allowed = client.get(f"/api/v1/scans?workspace_id={ws_a.id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res_allowed.status_code == 200
    assert len(res_allowed.json()) == 1
    assert res_allowed.json()[0]["security_score"] == 90


# ==============================================================================
# 2. SCAN DETAIL ENDPOINT TESTS
# ==============================================================================

def test_scan_detail_success_and_anti_idor():
    owner_a, token_a = create_user("owner_detail_a@test.com", "Owner Detail A")
    owner_b, token_b = create_user("owner_detail_b@test.com", "Owner Detail B")
    ws_a = create_workspace(owner_a, "Workspace Alpha")
    ws_b = create_workspace(owner_b, "Workspace Beta")

    scan_a = create_mock_scan(ws_a.id, score=88, rating="Good")

    # Owner A gets scan detail
    res_a = client.get(f"/api/v1/scans/{scan_a.id}", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    detail = res_a.json()
    assert detail["id"] == scan_a.id
    assert detail["security_score"] == 88
    assert detail["security_rating"] == "Good"
    assert detail["coverage_percentage"] == 92.5
    assert len(detail["check_results"]) >= 1
    assert detail["check_results"][0]["rule_id"] == "S3_BUCKET_PUBLIC_ACCESS_BLOCK"
    assert len(detail["findings"]) >= 1
    assert "s3" in detail["category_scores"]

    # Owner B attempts to access scan A -> 403 Forbidden (IDOR prevention)
    res_b = client.get(f"/api/v1/scans/{scan_a.id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 403

    # Non-existent scan returns 404
    res_404 = client.get(f"/api/v1/scans/{uuid.uuid4()}", headers={"Authorization": f"Bearer {token_a}"})
    assert res_404.status_code == 404


# ==============================================================================
# 3. DASHBOARD SUMMARY ENDPOINT & HISTORICAL TRENDS TESTS
# ==============================================================================

def test_dashboard_summary_unscored_empty_state():
    user, token = create_user("dash_empty@test.com", "Dash Empty")
    ws = create_workspace(user, "Empty Workspace")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/v1/dashboard/summary?workspace_id={ws.id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["security_score"] is None
    assert data["rating"] == "Not Scored"
    assert data["total_findings"] == 0
    assert data["total_resources"] == 0
    assert data["latest_scan_id"] is None
    assert data["previous_score"] is None
    assert data["score_delta"] is None
    assert data["score_trend"] == []


def test_dashboard_summary_single_scan_no_fabricated_trend():
    user, token = create_user("dash_single@test.com", "Dash Single")
    ws = create_workspace(user, "Single Workspace")
    headers = {"Authorization": f"Bearer {token}"}

    s = create_mock_scan(ws.id, score=78, rating="Fair", hours_ago=2)

    res = client.get(f"/api/v1/dashboard/summary?workspace_id={ws.id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["security_score"] == 78
    assert data["rating"] == "Fair"
    assert data["latest_scan_id"] == s.id
    assert data["previous_score"] is None
    assert data["score_delta"] is None
    # Crucial requirement: No fabricated trends! Exactly 1 point for 1 scan.
    assert len(data["score_trend"]) == 1
    assert data["score_trend"][0]["scan_id"] == s.id
    assert data["score_trend"][0]["score"] == 78


def test_dashboard_summary_multiple_scans_trend_and_delta():
    user, token = create_user("dash_multi@test.com", "Dash Multi")
    ws = create_workspace(user, "Multi Workspace")
    headers = {"Authorization": f"Bearer {token}"}

    # Scan 1: 5 hours ago, score 65
    s1 = create_mock_scan(ws.id, score=65, rating="Needs Attention", hours_ago=5)
    # Scan 2: 3 hours ago, score 72
    s2 = create_mock_scan(ws.id, score=72, rating="Fair", hours_ago=3)
    # Scan 3 (Latest): 1 hour ago, score 84
    s3 = create_mock_scan(ws.id, score=84, rating="Good", hours_ago=1)

    res = client.get(f"/api/v1/dashboard/summary?workspace_id={ws.id}", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["security_score"] == 84
    assert data["rating"] == "Good"
    assert data["latest_scan_id"] == s3.id
    # Previous score is s2 (72)
    assert data["previous_score"] == 72
    # Score delta is 84 - 72 = +12
    assert data["score_delta"] == 12

    # Trend points must be in chronological order: s1 -> s2 -> s3
    assert len(data["score_trend"]) == 3
    assert data["score_trend"][0]["scan_id"] == s1.id
    assert data["score_trend"][0]["score"] == 65
    assert data["score_trend"][1]["scan_id"] == s2.id
    assert data["score_trend"][1]["score"] == 72
    assert data["score_trend"][2]["scan_id"] == s3.id
    assert data["score_trend"][2]["score"] == 84


# ==============================================================================
# 4. IMMUTABILITY OF HISTORICAL SCANS
# ==============================================================================

def test_historical_scans_immutability():
    """
    CRITICAL REQUIREMENT:
    Verify that historical scans remain immutable.
    If Scan A had score 72 and Scan B later has score 61:
    Scan A must still return 72, and Scan B must return 61.
    """
    user, token = create_user("immutable_user@test.com", "Immutable User")
    ws = create_workspace(user, "Immutable Workspace")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Scan A with score 72
    scan_a = create_mock_scan(ws.id, score=72, rating="Fair", hours_ago=4)

    # Verify Scan A score is 72
    res_a_initial = client.get(f"/api/v1/scans/{scan_a.id}", headers=headers)
    assert res_a_initial.status_code == 200
    assert res_a_initial.json()["security_score"] == 72

    # 2. Later, Scan B completes with score 61
    scan_b = create_mock_scan(ws.id, score=61, rating="Needs Attention", hours_ago=1)

    # Verify Scan B score is 61
    res_b = client.get(f"/api/v1/scans/{scan_b.id}", headers=headers)
    assert res_b.status_code == 200
    assert res_b.json()["security_score"] == 61

    # 3. Verify Scan A is STILL 72 (completely immutable, not updated by scan B)
    res_a_after = client.get(f"/api/v1/scans/{scan_a.id}", headers=headers)
    assert res_a_after.status_code == 200
    assert res_a_after.json()["security_score"] == 72
    assert res_a_after.json()["security_rating"] == "Fair"

    # 4. Verify dashboard reflects Scan B as latest and Scan A as previous
    res_dash = client.get(f"/api/v1/dashboard/summary?workspace_id={ws.id}", headers=headers)
    dash_data = res_dash.json()
    assert dash_data["security_score"] == 61
    assert dash_data["previous_score"] == 72
    assert dash_data["score_delta"] == -11  # 61 - 72 = -11
