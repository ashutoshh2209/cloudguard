import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models import Base
from app.core.database import get_db
from app.schemas.resource import DiscoveredResourceData

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
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@patch("app.aws.sts_service.aws_sts_service.verify_role")
@patch("app.services.discovery_service.discover_ec2_resources")
@patch("app.services.discovery_service.discover_security_group_resources")
@patch("app.services.discovery_service.discover_s3_resources")
@patch("app.services.discovery_service.discover_iam_resources")
@patch("app.services.discovery_service.discover_rds_resources")
@patch("app.services.discovery_service.discover_cloudtrail_resources")
def test_full_frontend_api_contract_flow(
    mock_trail, mock_rds, mock_iam, mock_s3, mock_sg, mock_ec2, mock_verify_role
):
    """
    Simulates the exact frontend API contract sequence as invoked by:
    - AuthContext (register, login, me, loadWorkspaces)
    - Settings (AWSConnectionManager)
    - Resources (runDiscovery, listResources)
    - RunScanModal (scansApi.runScan)
    - ScanHistory & ScanDetailModal (scansApi.listScans, getScan)
    - Findings (findingsApi.list, updateStatus, aiApi.explainFinding)
    - Dashboard (fetchApi /dashboard/summary, /aws/status)
    - Reports (reportsApi.createReport, listReports, downloadReport)
    - CopilotDrawer (aiApi.askCopilot)
    - AuthContext (logout)
    """
    mock_verify_role.return_value = {
        "credentials": {
            "AccessKeyId": "ASIAIOSFODNN7EXAMPLE",
            "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "SessionToken": "AQoDYXdzEJr1EXAMPLE==",
            "Expiration": "2026-10-12T12:00:00Z",
        },
        "identity": {
            "account_id": "123456789012",
            "identity_arn": "arn:aws:sts::123456789012:assumed-role/CloudGuardRole/session",
            "user_id": "AROAIEXAMPLE:session",
        },
        "account_id": "123456789012",
    }
    mock_ec2.return_value = [
        DiscoveredResourceData(
            service="ec2",
            resource_type="instance",
            resource_id="i-0123456789abcdef0",
            resource_name="prod-web-server",
            region="us-east-1",
            arn="arn:aws:ec2:us-east-1:123456789012:instance/i-0123456789abcdef0",
            status="running",
            metadata={"PublicIpAddress": "54.210.10.20", "State": {"Name": "running"}},
        )
    ]
    mock_sg.return_value = [
        DiscoveredResourceData(
            service="ec2",
            resource_type="security_group",
            resource_id="sg-0123456789abcdef0",
            resource_name="wide-open-sg",
            region="us-east-1",
            arn="arn:aws:ec2:us-east-1:123456789012:security-group/sg-0123456789abcdef0",
            status="active",
            metadata={
                "IpPermissions": [{
                    "IpProtocol": "tcp",
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}]
                }]
            },
        )
    ]
    mock_s3.return_value = [
        DiscoveredResourceData(
            service="s3",
            resource_type="bucket",
            resource_id="my-unencrypted-bucket",
            resource_name="my-unencrypted-bucket",
            region="us-east-1",
            arn="arn:aws:s3:::my-unencrypted-bucket",
            status="active",
            metadata={
                "PublicAccessBlockConfiguration": {
                    "BlockPublicAcls": False,
                    "BlockPublicPolicy": False
                },
                "ServerSideEncryptionConfiguration": None
            },
        )
    ]
    mock_iam.return_value = []
    mock_rds.return_value = []
    mock_trail.return_value = []

    # 1. Register
    reg_res = client.post("/api/v1/auth/register", json={
        "full_name": "Integration User",
        "email": "integration@cloudguard.io",
        "password": "Password123!",
    })
    assert reg_res.status_code == 201, reg_res.text
    user_data = reg_res.json()
    assert user_data["email"] == "integration@cloudguard.io"
    assert "password_hash" not in user_data

    # 2. Login
    login_res = client.post("/api/v1/auth/login", json={
        "email": "integration@cloudguard.io",
        "password": "Password123!",
    })
    assert login_res.status_code == 200, login_res.text
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. /auth/me
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "integration@cloudguard.io"

    # 4. Create Workspace
    ws_res = client.post("/api/v1/workspaces", json={"name": "Prod Security Workspace"}, headers=headers)
    assert ws_res.status_code == 201
    workspace_id = ws_res.json()["id"]

    # 5. List Workspaces
    ws_list_res = client.get("/api/v1/workspaces", headers=headers)
    assert ws_list_res.status_code == 200
    assert len(ws_list_res.json()) >= 1

    # 6. Check AWS status before connection (should be disconnected)
    aws_pre = client.get(f"/api/v1/aws/status?workspace_id={workspace_id}", headers=headers)
    assert aws_pre.status_code == 200
    assert aws_pre.json()["connected"] is False

    # 7. Connect AWS IAM Role to Workspace
    conn_res = client.post("/api/v1/aws/connections", json={
        "workspace_id": workspace_id,
        "role_arn": "arn:aws:iam::123456789012:role/CloudGuardRole",
        "region": "us-east-1",
    }, headers=headers)
    assert conn_res.status_code == 201, conn_res.text
    conn_id = conn_res.json()["id"]

    # 8. Check AWS status after connection (should be connected via DB)
    aws_post = client.get(f"/api/v1/aws/status?workspace_id={workspace_id}", headers=headers)
    assert aws_post.status_code == 200
    assert aws_post.json()["connected"] is True
    assert aws_post.json()["account_id"] == "123456789012"

    # 9. Trigger Resource Discovery
    disc_res = client.post(f"/api/v1/discovery/run?workspace_id={workspace_id}", headers=headers)
    assert disc_res.status_code == 200
    assert disc_res.json()["resources_count"] >= 3

    # 10. List Resources
    res_list = client.get(f"/api/v1/resources?workspace_id={workspace_id}", headers=headers)
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 3

    # 11. Run Security Scan via RunScanModal payload
    scan_run_res = client.post("/api/v1/scans/", json={"workspace_id": workspace_id}, headers=headers)
    assert scan_run_res.status_code == 200, scan_run_res.text
    scan_data = scan_run_res.json()
    scan_id = scan_data["id"]
    assert scan_data["status"] == "COMPLETED"
    assert scan_data["summary"]["resources_scanned"] >= 3

    # 12. Scan History
    history_res = client.get(f"/api/v1/scans?workspace_id={workspace_id}", headers=headers)
    assert history_res.status_code == 200
    assert len(history_res.json()) >= 1

    # 13. Scan Detail
    detail_res = client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == scan_id

    # 14. List Findings
    findings_res = client.get(f"/api/v1/findings?workspace_id={workspace_id}", headers=headers)
    assert findings_res.status_code == 200
    findings = findings_res.json()
    assert len(findings) > 0
    target_finding_id = findings[0]["id"]

    # 15. Update Finding Status
    patch_res = client.patch(f"/api/v1/findings/{target_finding_id}?status=RESOLVED", headers=headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "RESOLVED"

    # 16. Dashboard Summary
    dash_res = client.get(f"/api/v1/dashboard/summary?workspace_id={workspace_id}", headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["total_resources"] >= 3
    assert dash_data["security_score"] is not None
    assert dash_data["rating"] in ["Excellent", "Good", "Fair", "Poor", "Critical", "A", "B", "C", "D", "F"]

    # 17. Create Security Report
    rep_create = client.post("/api/v1/reports", json={"scan_id": scan_id, "title": "Audit Report"}, headers=headers)
    assert rep_create.status_code == 200
    report_id = rep_create.json()["id"]

    # 18. List Reports
    rep_list = client.get(f"/api/v1/reports?workspace_id={workspace_id}", headers=headers)
    assert rep_list.status_code == 200
    assert rep_list.json()["total"] >= 1

    # 19. Download PDF Report
    pdf_res = client.get(f"/api/v1/reports/{report_id}/download", headers=headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF")

    # 20. AI Explain Finding
    ai_explain = client.post(f"/api/v1/ai/findings/{target_finding_id}/explain", headers=headers)
    assert ai_explain.status_code == 200
    assert "summary" in ai_explain.json()

    # 21. AI Scan Summary
    ai_sum = client.post(f"/api/v1/ai/scans/{scan_id}/summary", headers=headers)
    assert ai_sum.status_code == 200
    assert "key_risks" in ai_sum.json()

    # 22. AI Copilot Grounded Chat
    chat_res = client.post("/api/v1/ai/chat", json={
        "message": "What is my security score and what should I fix first?",
        "scan_id": scan_id,
        "workspace_id": workspace_id,
    }, headers=headers)
    assert chat_res.status_code == 200
    assert len(chat_res.json()["answer"]) > 0

    # 23. Logout (Revoke Token)
    logout_res = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200

    # 24. Verify Token Revocation
    revoked_me = client.get("/api/v1/auth/me", headers=headers)
    assert revoked_me.status_code == 401
