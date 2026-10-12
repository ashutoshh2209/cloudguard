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
    AWSConnection,
    CloudResource,
    Scan,
    CheckResult,
    Finding,
)
from app.core.database import get_db
from app.core.security import hash_password, create_access_token
from app.rules.base import CheckStatus, RuleEvaluationResult
from app.rules.registry import RuleRegistry
from app.rules.s3.public_access import S3PublicAccessRule
from app.rules.s3.encryption import S3NoEncryptionRule
from app.rules.s3.block_public_access import S3BlockPublicAccessDisabledRule
from app.rules.iam.mfa import IAMMFADisabledRule
from app.rules.iam.admin_privileges import IAMAdminPrivilegesRule
from app.rules.ec2.public_ip import EC2PublicIPRule
from app.rules.security_groups.exposed_ports import (
    SSHOpenToWorldRule,
    RDPOpenToWorldRule,
    DatabasePortOpenToWorldRule,
)
from app.rules.rds.public_access import RDSPublicAccessRule
from app.rules.rds.encryption import RDSNoEncryptionRule
from app.rules.cloudtrail.logging import CloudTrailDisabledRule
from app.scanner.deterministic_scanner import deterministic_scanner

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

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


def create_user_and_workspace(email: str, name: str, role: str = "OWNER"):
    db = TestingSessionLocal()
    user = User(
        email=email,
        password_hash=hash_password("Password123!"),
        full_name=name,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    ws = Workspace(name=f"{name}'s Workspace", owner_id=user.id)
    db.add(ws)
    db.commit()
    db.refresh(ws)

    member = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=role)
    db.add(member)

    conn = AWSConnection(
        workspace_id=ws.id,
        account_id="111222333444",
        role_arn="arn:aws:iam::111222333444:role/AuditRole",
        region="us-east-1",
        status="CONNECTED",
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)

    token = create_access_token(subject=user.id)
    user_id, ws_id, conn_id = user.id, ws.id, conn.id
    db.close()
    return user_id, token, ws_id, conn_id


# =============================================================================
# 1. Individual Rule Deterministic Evaluation Tests
# =============================================================================

def test_s3_rules_evaluation():
    # S3 Public Access
    pub_rule = S3PublicAccessRule()
    # Passing (private)
    res_pass = pub_rule.evaluate_check({"metadata": {"public_access": {"is_public": False}}})
    assert res_pass.status == CheckStatus.PASS
    # Failing (public)
    res_fail = pub_rule.evaluate_check({"metadata": {"public_access": {"is_public": True, "reason": "Public policy"}}})
    assert res_fail.status == CheckStatus.FAIL
    assert res_fail.evidence["public_access"] is True
    # Error (malformed)
    res_err = pub_rule.evaluate_check({"metadata": {"public_access": 12345}})
    assert res_err.status == CheckStatus.ERROR

    # S3 Encryption
    enc_rule = S3NoEncryptionRule()
    # Passing (encrypted)
    assert enc_rule.evaluate_check({"metadata": {"encryption": {"is_encrypted": True}}}).status == CheckStatus.PASS
    # Failing (unencrypted)
    res_enc_fail = enc_rule.evaluate_check({"metadata": {"encryption": {"is_encrypted": False}}})
    assert res_enc_fail.status == CheckStatus.FAIL
    assert res_enc_fail.evidence["encrypted"] is False
    # Error (malformed)
    assert enc_rule.evaluate_check({"metadata": {"encryption": "invalid_type"}}).status == CheckStatus.ERROR

    # S3 Block Public Access
    bpa_rule = S3BlockPublicAccessDisabledRule()
    # Passing (all enabled)
    assert bpa_rule.evaluate_check({"metadata": {"block_public_access": {"is_fully_enabled": True}}}).status == CheckStatus.PASS
    # Failing (disabled)
    res_bpa_fail = bpa_rule.evaluate_check({"metadata": {"block_public_access": {"is_fully_enabled": False, "missing_protections": ["BlockPublicAcls"]}}})
    assert res_bpa_fail.status == CheckStatus.FAIL
    assert res_bpa_fail.evidence["block_public_access_enabled"] is False
    # Error (malformed)
    assert bpa_rule.evaluate_check({"metadata": {"block_public_access": [1, 2, 3]}}).status == CheckStatus.ERROR


def test_iam_rules_evaluation():
    # IAM MFA
    mfa_rule = IAMMFADisabledRule()
    # Passing: service user without console access
    assert mfa_rule.evaluate_check({"metadata": {"has_console_access": False}}).status == CheckStatus.PASS
    # Passing: console user with MFA
    assert mfa_rule.evaluate_check({"metadata": {"has_console_access": True, "mfa": {"mfa_enabled": True}}}).status == CheckStatus.PASS
    # Failing: console user without MFA
    res_mfa_fail = mfa_rule.evaluate_check({"metadata": {"has_console_access": True, "mfa": {"mfa_enabled": False}}})
    assert res_mfa_fail.status == CheckStatus.FAIL
    assert res_mfa_fail.evidence["mfa_enabled"] is False
    # Error (malformed)
    assert mfa_rule.evaluate_check({"metadata": {"has_console_access": True, "mfa": "not_dict"}}).status == CheckStatus.ERROR

    # IAM Admin Privileges
    admin_rule = IAMAdminPrivilegesRule()
    # Passing: standard least privilege user
    assert admin_rule.evaluate_check({"metadata": {"policies": ["ReadOnlyAccess"]}}).status == CheckStatus.PASS
    # Failing: AdministratorAccess attached
    res_admin_fail = admin_rule.evaluate_check({"metadata": {"policies": ["arn:aws:iam::aws:policy/AdministratorAccess"]}})
    assert res_admin_fail.status == CheckStatus.FAIL
    assert res_admin_fail.evidence["admin_privileges"] is True
    # Error (malformed)
    assert admin_rule.evaluate_check({"metadata": {"policies": 1234}}).status == CheckStatus.ERROR


def test_ec2_public_ip_rule_evaluation():
    rule = EC2PublicIPRule()
    # Passing: private instance without public IP
    assert rule.evaluate_check({"metadata": {"public_ip": None, "state": "running"}}).status == CheckStatus.PASS
    # Failing: instance with assigned public IP
    res_fail = rule.evaluate_check({"metadata": {"public_ip": "54.214.12.34", "state": "running"}})
    assert res_fail.status == CheckStatus.FAIL
    assert res_fail.evidence["public_ip"] == "54.214.12.34"
    # Not Applicable: terminated instance
    assert rule.evaluate_check({"metadata": {"public_ip": "54.214.12.34", "state": "terminated"}}).status == CheckStatus.NOT_APPLICABLE
    # Error: malformed public_ip
    assert rule.evaluate_check({"metadata": {"public_ip": [1, 2, 3]}}).status == CheckStatus.ERROR


def test_security_group_rules_evaluation():
    ssh_rule = SSHOpenToWorldRule()
    rdp_rule = RDPOpenToWorldRule()
    db_rule = DatabasePortOpenToWorldRule()

    # Safe permissions: only port 443 open to world, port 22 internal
    safe_perms = [
        {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
        {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "10.0.0.0/8"}]},
    ]
    assert ssh_rule.evaluate_check({"metadata": {"ip_permissions": safe_perms}}).status == CheckStatus.PASS
    assert rdp_rule.evaluate_check({"metadata": {"ip_permissions": safe_perms}}).status == CheckStatus.PASS
    assert db_rule.evaluate_check({"metadata": {"ip_permissions": safe_perms}}).status == CheckStatus.PASS

    # Vulnerable permissions: port 22, 3389, and 5432 open to 0.0.0.0/0
    vuln_perms = [
        {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
        {"IpProtocol": "tcp", "FromPort": 3389, "ToPort": 3389, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
        {"IpProtocol": "tcp", "FromPort": 5432, "ToPort": 5432, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
    ]
    res_ssh = ssh_rule.evaluate_check({"metadata": {"ip_permissions": vuln_perms}})
    assert res_ssh.status == CheckStatus.FAIL
    assert res_ssh.evidence["ports"] == [22]

    res_rdp = rdp_rule.evaluate_check({"metadata": {"ip_permissions": vuln_perms}})
    assert res_rdp.status == CheckStatus.FAIL
    assert res_rdp.evidence["ports"] == [3389]

    res_db = db_rule.evaluate_check({"metadata": {"ip_permissions": vuln_perms}})
    assert res_db.status == CheckStatus.FAIL
    assert 5432 in res_db.evidence["ports"]

    # Error: malformed ip_permissions
    assert ssh_rule.evaluate_check({"metadata": {"ip_permissions": "not_a_list"}}).status == CheckStatus.ERROR


def test_rds_rules_evaluation():
    pub_rule = RDSPublicAccessRule()
    enc_rule = RDSNoEncryptionRule()

    # Passing
    assert pub_rule.evaluate_check({"metadata": {"publicly_accessible": False}}).status == CheckStatus.PASS
    assert enc_rule.evaluate_check({"metadata": {"storage_encrypted": True}}).status == CheckStatus.PASS

    # Failing
    res_pub = pub_rule.evaluate_check({"metadata": {"publicly_accessible": True}})
    assert res_pub.status == CheckStatus.FAIL
    assert res_pub.evidence["publicly_accessible"] is True

    res_enc = enc_rule.evaluate_check({"metadata": {"storage_encrypted": False}})
    assert res_enc.status == CheckStatus.FAIL
    assert res_enc.evidence["encrypted"] is False

    # Error
    assert pub_rule.evaluate_check({"metadata": {"publicly_accessible": "not_bool"}}).status == CheckStatus.ERROR
    assert enc_rule.evaluate_check({"metadata": {"storage_encrypted": "not_bool"}}).status == CheckStatus.ERROR


def test_cloudtrail_rules_evaluation():
    rule = CloudTrailDisabledRule()
    # Passing
    assert rule.evaluate_check({"metadata": {"is_logging": True}}).status == CheckStatus.PASS
    # Failing
    res_fail = rule.evaluate_check({"metadata": {"is_logging": False}})
    assert res_fail.status == CheckStatus.FAIL
    assert res_fail.evidence["logging_enabled"] is False
    # Error
    assert rule.evaluate_check({"metadata": {"is_logging": 12345}}).status == CheckStatus.ERROR


# =============================================================================
# 2. Scanner Service Deterministic Execution & Repeatability Tests
# =============================================================================

def test_deterministic_scanner_execution_and_repeatability():
    """Verify that multiple consecutive scans on identical resources yield 100% deterministic results."""
    user_id, token, ws_id, conn_id = create_user_and_workspace("dev@cloudguard.io", "Developer")
    db = TestingSessionLocal()

    # Seed resources into workspace
    res1 = CloudResource(
        workspace_id=ws_id,
        aws_connection_id=conn_id,
        service="s3",
        resource_type="s3:bucket",
        resource_id="secure-bucket",
        resource_name="secure-bucket",
        region="us-east-1",
        metadata_json={
            "public_access": {"is_public": False},
            "encryption": {"is_encrypted": True},
            "block_public_access": {"is_fully_enabled": True},
        },
    )
    res2 = CloudResource(
        workspace_id=ws_id,
        aws_connection_id=conn_id,
        service="s3",
        resource_type="s3:bucket",
        resource_id="vulnerable-bucket",
        resource_name="vulnerable-bucket",
        region="us-east-1",
        metadata_json={
            "public_access": {"is_public": True, "reason": "Public ACL"},
            "encryption": {"is_encrypted": False},
            "block_public_access": {"is_fully_enabled": False},
        },
    )
    res3 = CloudResource(
        workspace_id=ws_id,
        aws_connection_id=conn_id,
        service="ec2",
        resource_type="ec2:security-group",
        resource_id="sg-vulnerable",
        resource_name="sg-vulnerable",
        region="us-east-1",
        metadata_json={
            "ip_permissions": [
                {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
            ]
        },
    )
    db.add_all([res1, res2, res3])
    db.commit()

    # Run scan 1
    scan1 = deterministic_scanner.run_workspace_scan(db, ws_id, conn_id)
    assert scan1.status == "COMPLETED"
    assert scan1.resources_scanned == 3
    s1_attempted = scan1.checks_attempted
    s1_passed = scan1.checks_passed
    s1_failed = scan1.checks_failed

    # Run scan 2
    scan2 = deterministic_scanner.run_workspace_scan(db, ws_id, conn_id)
    assert scan2.status == "COMPLETED"
    assert scan2.resources_scanned == 3
    assert scan2.checks_attempted == s1_attempted
    assert scan2.checks_passed == s1_passed
    assert scan2.checks_failed == s1_failed

    # Run scan 3
    scan3 = deterministic_scanner.run_workspace_scan(db, ws_id, conn_id)
    assert scan3.checks_attempted == s1_attempted
    assert scan3.checks_passed == s1_passed
    assert scan3.checks_failed == s1_failed

    # Verify check results and findings persisted
    checks_scan1 = db.query(CheckResult).filter(CheckResult.scan_id == scan1.id).all()
    assert len(checks_scan1) == s1_attempted

    findings_scan1 = db.query(Finding).filter(Finding.scan_id == scan1.id).all()
    assert len(findings_scan1) == s1_failed
    rule_ids_found = [f.rule_id for f in findings_scan1]
    assert "S3_PUBLIC_ACCESS" in rule_ids_found
    assert "S3_NO_ENCRYPTION" in rule_ids_found
    assert "S3_BLOCK_PUBLIC_ACCESS_DISABLED" in rule_ids_found
    assert "SSH_OPEN_TO_WORLD" in rule_ids_found

    db.close()


def test_scanner_error_handling_and_partial_status():
    """Verify that malformed data produces ERROR status and does NOT become PASS."""
    user_id, token, ws_id, conn_id = create_user_and_workspace("err@cloudguard.io", "ErrUser")
    db = TestingSessionLocal()

    # Seed resource with corrupted metadata
    corrupt_res = CloudResource(
        workspace_id=ws_id,
        aws_connection_id=conn_id,
        service="s3",
        resource_type="s3:bucket",
        resource_id="corrupt-bucket",
        resource_name="corrupt-bucket",
        region="us-east-1",
        metadata_json={
            "public_access": 99999, # invalid type
            "encryption": {"is_encrypted": True}, # valid
        },
    )
    db.add(corrupt_res)
    db.commit()

    scan = deterministic_scanner.run_workspace_scan(db, ws_id, conn_id)
    # Since some checks passed and 1 errored, final status should be PARTIAL
    assert scan.status == "PARTIAL"
    assert scan.checks_errored >= 1
    assert scan.checks_passed >= 1

    error_check = (
        db.query(CheckResult)
        .filter(CheckResult.scan_id == scan.id, CheckResult.status == "ERROR")
        .first()
    )
    assert error_check is not None
    assert error_check.rule_id == "S3_PUBLIC_ACCESS"
    assert error_check.status != "PASS"

    db.close()


# =============================================================================
# 3. API Endpoints, Workspace Authorization & Anti-IDOR Tests
# =============================================================================

def test_api_run_workspace_scan_success():
    user_id, token, ws_id, conn_id = create_user_and_workspace("alice@cloudguard.io", "Alice", role="OWNER")
    db = TestingSessionLocal()
    db.add(CloudResource(
        workspace_id=ws_id,
        aws_connection_id=conn_id,
        service="ec2",
        resource_type="ec2:instance",
        resource_id="i-test1",
        region="us-east-1",
        metadata_json={"public_ip": None, "state": "running"},
    ))
    db.commit()
    db.close()

    res = client.post(
        "/api/v1/scans/",
        json={"workspace_id": ws_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert data["workspace_id"] == ws_id
    assert data["summary"]["resources_scanned"] == 1
    assert "check_results" in data
    assert len(data["check_results"]) >= 1


def test_api_unauthenticated_request_rejected():
    res = client.post("/api/v1/scans/", json={"workspace_id": "ws-dummy"})
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]


def test_api_viewer_role_cannot_trigger_scan():
    user_id, token, ws_id, conn_id = create_user_and_workspace("viewer@cloudguard.io", "Viewer", role="VIEWER")
    res = client.post(
        "/api/v1/scans/",
        json={"workspace_id": ws_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert "Insufficient permissions" in res.json()["detail"]


def test_api_anti_idor_cross_workspace_scan_denied():
    user_a_id, token_a, ws_a_id, conn_a_id = create_user_and_workspace("usera@cloudguard.io", "UserA")
    user_b_id, token_b, ws_b_id, conn_b_id = create_user_and_workspace("userb@cloudguard.io", "UserB")

    # User A attempts to trigger scan on User B's workspace
    res = client.post(
        "/api/v1/scans/",
        json={"workspace_id": ws_b_id},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]


def test_api_anti_idor_cross_workspace_read_scan_denied():
    user_a_id, token_a, ws_a_id, conn_a_id = create_user_and_workspace("usera2@cloudguard.io", "UserA2")
    user_b_id, token_b, ws_b_id, conn_b_id = create_user_and_workspace("userb2@cloudguard.io", "UserB2")

    db = TestingSessionLocal()
    scan_b = Scan(
        workspace_id=ws_b_id,
        aws_connection_id=conn_b_id,
        status="COMPLETED",
        resources_scanned=1,
    )
    db.add(scan_b)
    db.commit()
    db.refresh(scan_b)
    scan_b_id = scan_b.id
    db.close()

    # User A attempts to read User B's scan
    res = client.get(
        f"/api/v1/scans/{scan_b_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]


def test_api_list_scans_workspace_scoped():
    user_id, token, ws_id, conn_id = create_user_and_workspace("lister@cloudguard.io", "Lister")
    db = TestingSessionLocal()
    db.add(Scan(workspace_id=ws_id, aws_connection_id=conn_id, status="COMPLETED"))
    db.commit()
    db.close()

    res = client.get(
        f"/api/v1/scans/?workspace_id={ws_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    scans = res.json()
    assert len(scans) == 1
    assert scans[0]["workspace_id"] == ws_id


def test_api_get_scan_checks_endpoint():
    user_id, token, ws_id, conn_id = create_user_and_workspace("checker@cloudguard.io", "Checker")
    db = TestingSessionLocal()
    scan = Scan(workspace_id=ws_id, aws_connection_id=conn_id, status="COMPLETED")
    db.add(scan)
    db.commit()
    db.refresh(scan)

    cr1 = CheckResult(
        scan_id=scan.id,
        resource_id="res-1",
        rule_id="S3_PUBLIC_ACCESS",
        status="PASS",
        message="Compliant",
    )
    cr2 = CheckResult(
        scan_id=scan.id,
        resource_id="res-2",
        rule_id="SSH_OPEN_TO_WORLD",
        status="FAIL",
        message="Open to world",
    )
    db.add_all([cr1, cr2])
    db.commit()
    db.close()

    # List all checks
    res_all = client.get(
        f"/api/v1/scans/{scan.id}/checks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_all.status_code == 200
    assert len(res_all.json()) == 2

    # Filter by status=FAIL
    res_fail = client.get(
        f"/api/v1/scans/{scan.id}/checks?status=FAIL",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_fail.status_code == 200
    assert len(res_fail.json()) == 1
    assert res_fail.json()[0]["rule_id"] == "SSH_OPEN_TO_WORLD"
