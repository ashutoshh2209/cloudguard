import pytest
import uuid
from datetime import datetime, timezone
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
    CloudResource,
)
from app.core.database import get_db
from app.core.security import hash_password, create_access_token
from app.risk.service import (
    RiskEngineService,
    calculate_finding_risk,
    calculate_security_score,
    calculate_category_scores,
    get_rating_label,
)
from app.findings.schemas import CheckSummary, Severity, Finding as FindingSchema
from app.scanner.deterministic_scanner import deterministic_scanner


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


# ==========================================
# 1. RISK ENGINE SERVICE UNIT TESTS
# ==========================================

def test_risk_score_and_priority_modifiers():
    """Verify base scores and modifiers for contextual risk factors."""
    # Critical SSH open to world
    f1 = {
        "severity": "CRITICAL",
        "rule_id": "SG_SSH_OPEN_TO_WORLD",
        "category": "network",
    }
    calculate_finding_risk(f1)
    # Base 90 + 5 (Internet exposed) = 95 -> P1
    assert f1["risk_score"] == 95
    assert f1["priority"] == "P1"
    assert "Internet exposed" in f1["risk_factors"]
    assert "Critical severity" in f1["risk_factors"]

    # High public S3 bucket
    f2 = {
        "severity": "HIGH",
        "rule_id": "S3_PUBLIC_ACCESS",
        "category": "storage",
    }
    calculate_finding_risk(f2)
    # Base 70 + 5 (Public storage) = 75 -> P2
    assert f2["risk_score"] == 75
    assert f2["priority"] == "P2"
    assert "Publicly accessible storage" in f2["risk_factors"]

    # Medium database exposed
    f3 = {
        "severity": "MEDIUM",
        "rule_id": "RDS_PUBLIC_ACCESS",
        "category": "database",
    }
    calculate_finding_risk(f3)
    # Base 45 + 5 (Database exposed) = 50 -> P3
    assert f3["risk_score"] == 50
    assert f3["priority"] == "P3"
    assert "Database exposed" in f3["risk_factors"]

    # Medium CloudTrail disabled
    f4 = {
        "severity": "MEDIUM",
        "rule_id": "CLOUDTRAIL_DISABLED",
        "category": "logging",
    }
    calculate_finding_risk(f4)
    # Base 45 + 3 (No logging) = 48 -> P3
    assert f4["risk_score"] == 48
    assert f4["priority"] == "P3"
    assert "No logging / monitoring" in f4["risk_factors"]

    # Low finding without modifiers
    f5 = {
        "severity": "LOW",
        "rule_id": "MISC_TAG_MISSING",
        "category": "compute",
    }
    calculate_finding_risk(f5)
    # Base 20 -> P4
    assert f5["risk_score"] == 20
    assert f5["priority"] == "P4"


def test_overall_security_score_explainability():
    """Verify security score calculations are deterministic, capped, and explainable."""
    # 0 checks attempted -> (None, "Not Scored")
    score, rating = calculate_security_score([], CheckSummary(passed=0, failed=0, errors=0, skipped=0))
    assert score is None
    assert rating == "Not Scored"

    # Perfect account with 20 passed checks -> 100 "Excellent"
    score, rating = calculate_security_score([], CheckSummary(passed=20, failed=0, errors=0, skipped=0))
    assert score == 100
    assert rating == "Excellent"

    # 1 Critical finding (penalty 10) -> 90 "Excellent"
    f_crit = [{"severity": "CRITICAL", "status": "OPEN"}]
    score, rating = calculate_security_score(f_crit, CheckSummary(passed=19, failed=1, errors=0, skipped=0))
    assert score == 90
    assert rating == "Excellent"

    # 2 Critical findings (penalty 20) -> 80 "Good"
    f_2crit = [
        {"severity": "CRITICAL", "status": "OPEN"},
        {"severity": "CRITICAL", "status": "OPEN"},
    ]
    score, rating = calculate_security_score(f_2crit, CheckSummary(passed=18, failed=2, errors=0, skipped=0))
    assert score == 80
    assert rating == "Good"

    # 5 Critical findings -> raw penalty 50, but capped at 40 -> score = 60 "Needs Attention"
    f_5crit = [{"severity": "CRITICAL", "status": "OPEN"} for _ in range(5)]
    score, rating = calculate_security_score(f_5crit, CheckSummary(passed=15, failed=5, errors=0, skipped=0))
    assert score == 60
    assert rating == "Needs Attention"

    # 30 Low findings -> raw penalty 30, but low capped at 10 -> score = 90 "Excellent"
    f_30low = [{"severity": "LOW", "status": "OPEN"} for _ in range(30)]
    score, rating = calculate_security_score(f_30low, CheckSummary(passed=10, failed=30, errors=0, skipped=0))
    assert score == 90
    assert rating == "Excellent"

    # RESOLVED findings should not penalize score
    f_resolved = [{"severity": "CRITICAL", "status": "RESOLVED"}]
    score, rating = calculate_security_score(f_resolved, CheckSummary(passed=19, failed=1, errors=0, skipped=0))
    assert score == 100
    assert rating == "Excellent"


def test_category_scores_breakdown():
    """Verify category grouping and individual scores."""
    findings = [
        {"severity": "CRITICAL", "category": "identity", "status": "OPEN"},
        {"severity": "HIGH", "category": "identity", "status": "OPEN"},
        {"severity": "MEDIUM", "category": "network", "status": "OPEN"},
    ]
    cat_scores = calculate_category_scores(findings)
    assert "IDENTITY" in cat_scores
    assert "NETWORK" in cat_scores

    # IDENTITY: 10 + 6 penalty = 16 -> 84 score
    assert cat_scores["IDENTITY"]["score"] == 84
    assert cat_scores["IDENTITY"]["findings"] == 2
    assert cat_scores["IDENTITY"]["critical"] == 1
    assert cat_scores["IDENTITY"]["high"] == 1
    assert cat_scores["IDENTITY"]["status"] == "GOOD"

    # NETWORK: 3 penalty -> 97 score
    assert cat_scores["NETWORK"]["score"] == 97
    assert cat_scores["NETWORK"]["status"] == "SECURE"


# ==========================================
# 2. FINDINGS API & ANTI-IDOR TESTS
# ==========================================

def test_findings_workspace_isolation_and_anti_idor():
    """Verify strict workspace authorization for findings (Anti-IDOR)."""
    user_a, token_a = create_user("usera@cloudguard.test", "User A")
    user_b, token_b = create_user("userb@cloudguard.test", "User B")

    ws_a = create_workspace(user_a, "Workspace Alpha")
    ws_b = create_workspace(user_b, "Workspace Beta")

    db = TestingSessionLocal()
    scan_a = Scan(id=str(uuid.uuid4()), workspace_id=ws_a.id, status="COMPLETED")
    scan_b = Scan(id=str(uuid.uuid4()), workspace_id=ws_b.id, status="COMPLETED")
    db.add_all([scan_a, scan_b])
    db.commit()

    f_a = FindingModel(
        id=str(uuid.uuid4()),
        workspace_id=ws_a.id,
        scan_id=scan_a.id,
        resource_id="res-a-1",
        rule_id="RULE_A",
        title="Violation A",
        severity="HIGH",
        category="network",
        status="OPEN",
        risk_score=75,
        priority="P2",
    )
    f_b = FindingModel(
        id=str(uuid.uuid4()),
        workspace_id=ws_b.id,
        scan_id=scan_b.id,
        resource_id="res-b-1",
        rule_id="RULE_B",
        title="Violation B",
        severity="CRITICAL",
        category="identity",
        status="OPEN",
        risk_score=95,
        priority="P1",
    )
    db.add_all([f_a, f_b])
    db.commit()
    db.close()

    # User A listing findings in Workspace A -> OK
    res_a = client.get(
        f"/api/v1/findings?workspace_id={ws_a.id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a.status_code == 200
    findings_data = res_a.json()
    assert len(findings_data) == 1
    assert findings_data[0]["id"] == f_a.id

    # User A attempting to list Workspace B findings -> 403 Forbidden
    res_idor = client.get(
        f"/api/v1/findings?workspace_id={ws_b.id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_idor.status_code == 403

    # User A listing without workspace_id returns only User A's findings
    res_all = client.get(
        "/api/v1/findings",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_all.status_code == 200
    ids = [f["id"] for f in res_all.json()]
    assert f_a.id in ids
    assert f_b.id not in ids

    # User A getting single finding f_a -> 200
    res_single = client.get(
        f"/api/v1/findings/{f_a.id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_single.status_code == 200
    assert res_single.json()["title"] == "Violation A"

    # User B attempting to get finding f_a -> 403 Forbidden
    res_single_idor = client.get(
        f"/api/v1/findings/{f_a.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_single_idor.status_code == 403


def test_findings_filtering_and_status_transitions():
    """Verify finding filtering and status updates (OPEN, RESOLVED, IGNORED)."""
    user, token = create_user("auditor@cloudguard.test", "Auditor")
    ws = create_workspace(user, "Auditor Workspace")

    db = TestingSessionLocal()
    scan = Scan(id=str(uuid.uuid4()), workspace_id=ws.id, status="COMPLETED")
    db.add(scan)
    db.commit()

    f1 = FindingModel(
        id=str(uuid.uuid4()),
        workspace_id=ws.id,
        scan_id=scan.id,
        resource_id="bucket-1",
        rule_id="S3_PUBLIC_ACCESS",
        service="s3",
        title="Public Bucket",
        severity="HIGH",
        category="storage",
        status="OPEN",
        risk_score=75,
        priority="P2",
    )
    f2 = FindingModel(
        id=str(uuid.uuid4()),
        workspace_id=ws.id,
        scan_id=scan.id,
        resource_id="sg-1",
        rule_id="SG_SSH_OPEN_TO_WORLD",
        service="ec2",
        title="Open SSH",
        severity="CRITICAL",
        category="network",
        status="OPEN",
        risk_score=95,
        priority="P1",
    )
    db.add_all([f1, f2])
    db.commit()
    db.close()

    # Filter by severity
    res_sev = client.get(
        f"/api/v1/findings?workspace_id={ws.id}&severity=CRITICAL",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_sev.status_code == 200
    assert len(res_sev.json()) == 1
    assert res_sev.json()[0]["id"] == f2.id

    # Filter by priority
    res_prio = client.get(
        f"/api/v1/findings?workspace_id={ws.id}&priority=P2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_prio.status_code == 200
    assert len(res_prio.json()) == 1
    assert res_prio.json()[0]["id"] == f1.id

    # Filter by service
    res_svc = client.get(
        f"/api/v1/findings?workspace_id={ws.id}&service=s3",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_svc.status_code == 200
    assert len(res_svc.json()) == 1
    assert res_svc.json()[0]["id"] == f1.id

    # Update status to RESOLVED
    res_update = client.patch(
        f"/api/v1/findings/{f1.id}",
        json={"status": "RESOLVED"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_update.status_code == 200
    assert res_update.json()["status"] == "RESOLVED"

    # Verify status changed in database
    db = TestingSessionLocal()
    refreshed_f1 = db.query(FindingModel).filter(FindingModel.id == f1.id).first()
    assert refreshed_f1.status == "RESOLVED"
    db.close()

    # Update status to IGNORED
    res_ignore = client.patch(
        f"/api/v1/findings/{f2.id}?status=IGNORED",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_ignore.status_code == 200
    assert res_ignore.json()["status"] == "IGNORED"

    # Invalid status should return 400
    res_invalid = client.patch(
        f"/api/v1/findings/{f1.id}",
        json={"status": "INVALID_STATE"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_invalid.status_code == 400


def test_viewer_role_cannot_modify_finding_status():
    """Verify that VIEWER role has read-only access and cannot alter finding status."""
    owner, _ = create_user("owner@cloudguard.test", "Owner")
    viewer, viewer_token = create_user("viewer@cloudguard.test", "Viewer")

    ws = create_workspace(owner, "Restricted Workspace")

    db = TestingSessionLocal()
    member = WorkspaceMember(workspace_id=ws.id, user_id=viewer.id, role="VIEWER")
    scan = Scan(id=str(uuid.uuid4()), workspace_id=ws.id, status="COMPLETED")
    finding = FindingModel(
        id=str(uuid.uuid4()),
        workspace_id=ws.id,
        scan_id=scan.id,
        resource_id="res-1",
        rule_id="RULE_1",
        title="Violation",
        severity="MEDIUM",
        category="storage",
        status="OPEN",
        risk_score=45,
        priority="P3",
    )
    db.add_all([member, scan, finding])
    db.commit()
    db.close()

    # Viewer can read findings
    res_read = client.get(
        f"/api/v1/findings/{finding.id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res_read.status_code == 200

    # Viewer cannot update status -> 403 Forbidden
    res_patch = client.patch(
        f"/api/v1/findings/{finding.id}",
        json={"status": "RESOLVED"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res_patch.status_code == 403


# ==========================================
# 3. DETERMINISTIC SCANNER + RISK ENGINE INTEGRATION
# ==========================================

def test_deterministic_scanner_produces_scored_findings_and_category_records():
    """Verify that scanning resources persists enriched findings, category scores, and scan score."""
    user, _ = create_user("engineer@cloudguard.test", "Engineer")
    ws = create_workspace(user, "Prod Workspace")

    db = TestingSessionLocal()
    # Add an insecure S3 bucket (public)
    bucket = CloudResource(
        id=str(uuid.uuid4()),
        workspace_id=ws.id,
        service="s3",
        resource_type="s3-bucket",
        resource_id="insecure-customer-data",
        resource_name="insecure-customer-data",
        region="us-east-1",
        metadata={
            "public_access_block": {
                "BlockPublicAcls": False,
                "IgnorePublicAcls": False,
                "BlockPublicPolicy": False,
                "RestrictPublicBuckets": False,
            },
            "policy_status": {"IsPublic": True},
        },
    )
    db.add(bucket)
    db.commit()
    db.close()

    # Run deterministic scan
    db = TestingSessionLocal()
    scan = deterministic_scanner.run_workspace_scan(db=db, workspace_id=ws.id)

    assert scan.status in ["COMPLETED", "PARTIAL"]
    assert scan.security_score is not None
    assert scan.security_rating is not None
    assert scan.checks_failed >= 1

    # Findings should be enriched
    findings = db.query(FindingModel).filter(FindingModel.scan_id == scan.id).all()
    assert len(findings) >= 1
    for f in findings:
        assert f.workspace_id == ws.id
        assert f.risk_score is not None
        assert f.priority in ["P1", "P2", "P3", "P4"]
        assert f.risk_factors is not None
        assert f.service == "s3"

    # CategoryScore records should exist
    cat_scores = db.query(CategoryScoreModel).filter(CategoryScoreModel.scan_id == scan.id).all()
    assert len(cat_scores) >= 1
    storage_cat = next((c for c in cat_scores if c.category == "STORAGE"), None)
    assert storage_cat is not None
    assert storage_cat.finding_count >= 1

    db.close()


# ==========================================
# 4. DASHBOARD INTEGRATION TESTS
# ==========================================

def test_dashboard_scoped_and_unscored():
    """Verify dashboard endpoint scoped to workspace and unscored empty state."""
    user, token = create_user("lead@cloudguard.test", "Lead")
    ws = create_workspace(user, "Empty Workspace")

    # Unscored workspace (no scans run yet)
    res_empty = client.get(
        f"/api/v1/dashboard?workspace_id={ws.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_empty.status_code == 200
    data_empty = res_empty.json()
    assert data_empty["security_score"] is None
    assert data_empty["rating"] == "Not Scored"

    # Add a completed scan with score
    db = TestingSessionLocal()
    scan = Scan(
        id=str(uuid.uuid4()),
        workspace_id=ws.id,
        status="COMPLETED",
        security_score=85,
        security_rating="Good",
        checks_completed=10,
        checks_passed=8,
        checks_failed=2,
    )
    finding = FindingModel(
        id=str(uuid.uuid4()),
        workspace_id=ws.id,
        scan_id=scan.id,
        resource_id="res-top-1",
        rule_id="RULE_TEST",
        title="Top Risk Vulnerability",
        severity="HIGH",
        category="storage",
        status="OPEN",
        risk_score=75,
        priority="P2",
    )
    cat_score = CategoryScoreModel(
        id=str(uuid.uuid4()),
        scan_id=scan.id,
        category="STORAGE",
        score=85,
        status="GOOD",
        finding_count=1,
        high_count=1,
    )
    db.add_all([scan, finding, cat_score])
    db.commit()
    db.close()

    res_scored = client.get(
        f"/api/v1/dashboard?workspace_id={ws.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_scored.status_code == 200
    data = res_scored.json()
    assert data["security_score"] == 85
    assert data["rating"] == "Good"
    assert data["findings_summary"]["high"] == 1
    assert len(data["top_risks"]) == 1
    assert data["top_risks"][0]["title"] == "Top Risk Vulnerability"
    assert "STORAGE" in data["category_scores"]
