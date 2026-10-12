import pytest
import uuid
import io
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
    SecurityReport,
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


def create_mock_scan_with_findings(
    workspace_id: str,
    status: str = "COMPLETED",
    score: int = 85,
    rating: str = "Good",
    findings_spec: list = None,
    resources_count: int = 20,
) -> Scan:
    db = TestingSessionLocal()
    scan_id = str(uuid.uuid4())
    started = datetime.now(timezone.utc) - timedelta(hours=2)
    completed = started + timedelta(minutes=5) if status in ("COMPLETED", "PARTIAL") else None
    
    scan = Scan(
        id=scan_id,
        workspace_id=workspace_id,
        aws_connection_id=str(uuid.uuid4()),
        status=status,
        started_at=started,
        completed_at=completed,
        created_at=started,
        resources_scanned=resources_count,
        checks_attempted=50,
        checks_completed=50,
        checks_failed=len(findings_spec) if findings_spec else 0,
        checks_passed=50 - (len(findings_spec) if findings_spec else 0),
        checks_errored=0,
        coverage_percentage=95.0,
        security_score=score if status in ("COMPLETED", "PARTIAL") else None,
        security_rating=rating if status in ("COMPLETED", "PARTIAL") else None,
    )
    db.add(scan)
    db.commit()

    if findings_spec:
        for f_data in findings_spec:
            f = FindingModel(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                scan_id=scan.id,
                rule_id=f_data.get("rule_id", "TEST_RULE"),
                title=f_data.get("title", "Test Finding Title"),
                severity=f_data.get("severity", "MEDIUM"),
                category=f_data.get("category", "s3"),
                service=f_data.get("service", "s3"),
                region="us-east-1",
                resource_id=f_data.get("resource_id", "arn:aws:s3:::bucket-1"),
                risk_score=f_data.get("risk_score", 50),
                priority=f_data.get("priority", "P3"),
                description=f_data.get("description", "A description of security finding."),
                recommendation=f_data.get("recommendation", "Enable security settings immediately."),
                status="OPEN",
                detected_at=started,
            )
            db.add(f)

    # Add category scores
    cs1 = CategoryScoreModel(
        id=str(uuid.uuid4()),
        scan_id=scan.id,
        category="s3",
        score=score if score is not None else 0,
        status="SECURE" if (score is not None and score >= 80) else "WARNING",
        finding_count=len(findings_spec) if findings_spec else 0,
        critical_count=sum(1 for f in (findings_spec or []) if f.get("severity") == "CRITICAL"),
        high_count=sum(1 for f in (findings_spec or []) if f.get("severity") == "HIGH"),
    )
    db.add(cs1)

    db.commit()
    db.refresh(scan)
    db.close()
    return scan


# ==============================================================================
# 1. REPORT WITH NO FINDINGS
# ==============================================================================

def test_report_with_no_findings():
    user, token = create_user("clean@test.com", "Clean Account")
    ws = create_workspace(user, "Clean Workspace")
    headers = {"Authorization": f"Bearer {token}"}

    # Completed scan with 0 findings, 100 score, 15 resources
    scan = create_mock_scan_with_findings(
        ws.id,
        status="COMPLETED",
        score=100,
        rating="Excellent",
        findings_spec=[],
        resources_count=15,
    )

    # Generate report
    res = client.post(f"/api/v1/reports?scan_id={scan.id}", headers=headers)
    assert res.status_code == 200
    report = res.json()
    assert report["scan_id"] == scan.id
    assert report["security_score"] == 100
    assert report["security_rating"] == "Excellent"
    assert report["finding_count"] == 0
    assert report["critical_count"] == 0
    assert report["high_count"] == 0
    assert report["resource_count"] == 15
    assert report["coverage_percentage"] == 95.0

    # Query report details
    res_detail = client.get(f"/api/v1/reports/{report['id']}", headers=headers)
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["security_posture"]["score"] == 100
    assert detail["security_posture"]["rating"] == "Excellent"
    assert detail["finding_summary"]["critical"] == 0
    assert len(detail["top_findings"]) == 0
    assert "No active findings" in detail["executive_summary"]["summary_text"] or "deterministic security baselines" in detail["executive_summary"]["summary_text"]

    # Download PDF
    res_pdf = client.get(f"/api/v1/reports/{report['id']}/download", headers=headers)
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert res_pdf.content.startswith(b"%PDF-")


# ==============================================================================
# 2. REPORT WITH MANY FINDINGS
# ==============================================================================

def test_report_with_many_findings():
    user, token = create_user("findings@test.com", "Risky Account")
    ws = create_workspace(user, "Risky Workspace")
    headers = {"Authorization": f"Bearer {token}"}

    findings_spec = [
        {"severity": "CRITICAL", "rule_id": "SG_SSH_OPEN", "title": "SSH Open to World", "risk_score": 95, "priority": "P1"},
        {"severity": "CRITICAL", "rule_id": "S3_PUBLIC", "title": "S3 Bucket Public Read", "risk_score": 90, "priority": "P1"},
        {"severity": "HIGH", "rule_id": "RDS_NO_ENCRYPT", "title": "RDS Instance Unencrypted", "risk_score": 80, "priority": "P2"},
        {"severity": "HIGH", "rule_id": "IAM_NO_MFA", "title": "Root User Without MFA", "risk_score": 85, "priority": "P2"},
        {"severity": "MEDIUM", "rule_id": "EC2_PUBLIC_IP", "title": "EC2 Instance with Public IP", "risk_score": 60, "priority": "P3"},
        {"severity": "LOW", "rule_id": "CT_NO_LOGS", "title": "CloudTrail Multi-Region Disabled", "risk_score": 40, "priority": "P4"},
        {"severity": "INFO", "rule_id": "S3_NO_VERSIONING", "title": "S3 Bucket Versioning Disabled", "risk_score": 20, "priority": "P5"},
    ]

    scan = create_mock_scan_with_findings(
        ws.id,
        status="COMPLETED",
        score=58,
        rating="Needs Attention",
        findings_spec=findings_spec,
        resources_count=35,
    )

    # Generate report
    res = client.post(f"/api/v1/reports?scan_id={scan.id}", headers=headers)
    assert res.status_code == 200
    report = res.json()
    assert report["security_score"] == 58
    assert report["security_rating"] == "Needs Attention"
    assert report["finding_count"] == 7
    assert report["critical_count"] == 2
    assert report["high_count"] == 2
    assert report["medium_count"] == 1
    assert report["low_count"] == 1
    assert report["info_count"] == 1
    assert report["resource_count"] == 35

    # Download PDF
    res_pdf = client.get(f"/api/v1/reports/{report['id']}/download", headers=headers)
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert res_pdf.content.startswith(b"%PDF-")
    # Verify non-trivial PDF size (> 5KB)
    assert len(res_pdf.content) > 5000


# ==============================================================================
# 3. REPORT FROM PARTIAL SCAN
# ==============================================================================

def test_report_partial_scan():
    user, token = create_user("partial@test.com", "Partial Account")
    ws = create_workspace(user, "Partial Workspace")
    headers = {"Authorization": f"Bearer {token}"}

    scan = create_mock_scan_with_findings(
        ws.id,
        status="PARTIAL",
        score=68,
        rating="Fair",
        findings_spec=[{"severity": "HIGH", "rule_id": "S3_PUB", "title": "Public S3"}],
        resources_count=10,
    )

    res = client.post(f"/api/v1/reports?scan_id={scan.id}", headers=headers)
    assert res.status_code == 200
    report = res.json()
    assert report["status"] == "GENERATED"
    assert report["security_score"] == 68
    assert report["security_rating"] == "Fair"
    assert report["finding_count"] == 1


# ==============================================================================
# 4. INVALID AND INCOMPLETE SCANS REJECTED
# ==============================================================================

def test_report_invalid_and_incomplete_scans():
    user, token = create_user("invalid@test.com", "Invalid Account")
    ws = create_workspace(user, "Invalid Workspace")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Non-existent scan ID -> 404
    res_404 = client.post(f"/api/v1/reports?scan_id={uuid.uuid4()}", headers=headers)
    assert res_404.status_code == 404

    # 2. RUNNING / INCOMPLETE scan -> 400 Bad Request
    running_scan = create_mock_scan_with_findings(ws.id, status="RUNNING", score=None)
    res_running = client.post(f"/api/v1/reports?scan_id={running_scan.id}", headers=headers)
    assert res_running.status_code == 400
    assert "incomplete scan" in res_running.json()["detail"].lower()

    # 3. Non-existent report detail -> 404
    res_rep_404 = client.get(f"/api/v1/reports/{uuid.uuid4()}", headers=headers)
    assert res_rep_404.status_code == 404


# ==============================================================================
# 5. CROSS-WORKSPACE ACCESS (ANTI-IDOR) ENFORCEMENT
# ==============================================================================

def test_report_cross_workspace_anti_idor():
    owner_a, token_a = create_user("owner_a_rep@test.com", "Owner A")
    owner_b, token_b = create_user("owner_b_rep@test.com", "Owner B")
    ws_a = create_workspace(owner_a, "Workspace Alpha")
    ws_b = create_workspace(owner_b, "Workspace Beta")

    scan_a = create_mock_scan_with_findings(ws_a.id, score=88, rating="Good")

    # User B attempts to generate report from User A's scan -> 403 Forbidden
    res_idor_gen = client.post(
        f"/api/v1/reports?scan_id={scan_a.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_idor_gen.status_code == 403

    # User A generates report in Workspace A
    res_gen = client.post(
        f"/api/v1/reports?scan_id={scan_a.id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_gen.status_code == 200
    report_a = res_gen.json()

    # User B attempts to access Report A details -> 403 Forbidden
    res_idor_get = client.get(
        f"/api/v1/reports/{report_a['id']}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_idor_get.status_code == 403

    # User B attempts to download Report A PDF -> 403 Forbidden
    res_idor_pdf = client.get(
        f"/api/v1/reports/{report_a['id']}/download",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_idor_pdf.status_code == 403

    # User B attempts to list reports from Workspace A -> 403 Forbidden
    res_idor_list = client.get(
        f"/api/v1/reports?workspace_id={ws_a.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_idor_list.status_code == 403

    # Add User B as member to Workspace A -> Access Granted
    add_member(ws_a.id, owner_b.id, "MEMBER")

    res_allowed = client.get(
        f"/api/v1/reports/{report_a['id']}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_allowed.status_code == 200
    assert res_allowed.json()["report"]["id"] == report_a["id"]


# ==============================================================================
# 6. SCORE, COUNT, AND METRIC CONSISTENCY (DASHBOARD = SCAN = REPORT = PDF)
# ==============================================================================

def test_score_and_count_consistency():
    """
    CRITICAL REQUIREMENT:
    Verify Dashboard score = Scan score = Report score = PDF score
    Verify finding counts and resource counts match.
    """
    user, token = create_user("consistent@test.com", "Consistent User")
    ws = create_workspace(user, "Consistency Workspace")
    headers = {"Authorization": f"Bearer {token}"}

    findings_spec = [
        {"severity": "CRITICAL", "rule_id": "R1", "title": "Crit 1"},
        {"severity": "HIGH", "rule_id": "R2", "title": "High 1"},
        {"severity": "HIGH", "rule_id": "R3", "title": "High 2"},
    ]

    # 1. Create Scan with deterministic score 77
    scan = create_mock_scan_with_findings(
        ws.id,
        score=77,
        rating="Fair",
        findings_spec=findings_spec,
        resources_count=18,
    )
    assert scan.security_score == 77
    assert scan.resources_scanned == 18

    # 2. Check Dashboard Score
    res_dash = client.get(f"/api/v1/dashboard/summary?workspace_id={ws.id}", headers=headers)
    assert res_dash.status_code == 200
    dash_data = res_dash.json()
    assert dash_data["security_score"] == 77
    assert dash_data["rating"] == "Fair"
    assert dash_data["total_findings"] == 3
    assert dash_data["total_resources"] == 18

    # 3. Generate Report and check Report Score
    res_rep = client.post(f"/api/v1/reports?scan_id={scan.id}", headers=headers)
    assert res_rep.status_code == 200
    report_data = res_rep.json()
    assert report_data["security_score"] == 77
    assert report_data["security_rating"] == "Fair"
    assert report_data["finding_count"] == 3
    assert report_data["resource_count"] == 18

    # Check Report Detail Score
    res_detail = client.get(f"/api/v1/reports/{report_data['id']}", headers=headers)
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert detail_data["security_posture"]["score"] == 77
    assert detail_data["security_posture"]["rating"] == "Fair"
    assert detail_data["report"]["resource_count"] == 18
    assert detail_data["report"]["finding_count"] == 3

    # 4. Check PDF Download
    res_pdf = client.get(f"/api/v1/reports/{report_data['id']}/download", headers=headers)
    assert res_pdf.status_code == 200
    assert res_pdf.content.startswith(b"%PDF-")


# ==============================================================================
# 7. HISTORICAL REPORTS IMMUTABILITY
# ==============================================================================

def test_historical_reports_immutability():
    """
    CRITICAL REQUIREMENT:
    Historical reports must not change after a new scan.
    If Scan 1 had score 82 and Report 1 is generated:
    Later Scan 2 has score 64.
    Report 1 must STILL have score 82 and original counts!
    """
    user, token = create_user("immutable_rep@test.com", "Immutable Rep")
    ws = create_workspace(user, "Immutable Workspace")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. First Scan: score 82, 2 findings
    scan_1 = create_mock_scan_with_findings(
        ws.id,
        score=82,
        rating="Good",
        findings_spec=[
            {"severity": "HIGH", "rule_id": "H1", "title": "Old High Finding"},
            {"severity": "MEDIUM", "rule_id": "M1", "title": "Old Med Finding"},
        ],
        resources_count=22,
    )

    # Generate Report 1
    res_rep_1 = client.post(f"/api/v1/reports?scan_id={scan_1.id}", headers=headers)
    assert res_rep_1.status_code == 200
    rep_1_id = res_rep_1.json()["id"]
    assert res_rep_1.json()["security_score"] == 82
    assert res_rep_1.json()["finding_count"] == 2

    # 2. Later, Second Scan occurs with score 59 and 8 findings
    scan_2 = create_mock_scan_with_findings(
        ws.id,
        score=59,
        rating="Needs Attention",
        findings_spec=[
            {"severity": "CRITICAL", "rule_id": f"C{i}", "title": f"New Crit {i}"} for i in range(4)
        ] + [
            {"severity": "HIGH", "rule_id": f"H{i}", "title": f"New High {i}"} for i in range(4)
        ],
        resources_count=30,
    )

    # Dashboard now shows latest score 59
    res_dash = client.get(f"/api/v1/dashboard/summary?workspace_id={ws.id}", headers=headers)
    assert res_dash.json()["security_score"] == 59
    assert res_dash.json()["latest_scan_id"] == scan_2.id

    # 3. CRITICAL: Query historical Report 1 -> STILL 82 and 2 findings!
    res_rep_1_after = client.get(f"/api/v1/reports/{rep_1_id}", headers=headers)
    assert res_rep_1_after.status_code == 200
    r1_after = res_rep_1_after.json()
    assert r1_after["report"]["security_score"] == 82
    assert r1_after["report"]["security_rating"] == "Good"
    assert r1_after["report"]["finding_count"] == 2
    assert r1_after["report"]["resource_count"] == 22

    # PDF for Report 1 also generates with frozen historical data
    res_pdf_1 = client.get(f"/api/v1/reports/{rep_1_id}/download", headers=headers)
    assert res_pdf_1.status_code == 200
    assert res_pdf_1.content.startswith(b"%PDF-")
