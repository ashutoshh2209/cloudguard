"""
Idempotent seed script for CloudGuard local demonstration mode.

Creates or updates a dedicated local demo account and sets up a deterministic
demonstration workspace with clearly labeled simulated security findings.

Usage:
    python seed.py
    python create_test_user.py

Environment variables (read from .env or environment):
    DEMO_USER_EMAIL      (default: demo@cloudguard.io)
    DEMO_USER_PASSWORD   (default: DemoPassword123!)
    DEMO_USER_NAME       (default: Security Lead)
    DEMO_WORKSPACE_NAME  (default: Demonstration Workspace)
"""
import os
import sys
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

load_dotenv()

from app.core.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.resource import CloudResource
from app.models.scan import Scan
from app.models.finding import Finding
from app.models.category_score import CategoryScore
from app.models.check_result import CheckResult
from app.models.aws_connection import AWSConnection
from app.core.security import hash_password


def seed_demo_environment() -> dict:
    """
    Idempotently sets up:
      1. Demo user with secure password hash
      2. Clean personal workspace (for live AWS connections)
      3. Demonstration workspace with clearly labeled simulated findings
    Never logs passwords, tokens, or secrets.
    """
    # Verify/create tables
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Read demo credentials from environment variables
        demo_email = os.getenv("DEMO_USER_EMAIL", "demo@cloudguard.io").lower().strip()
        demo_password = os.getenv("DEMO_USER_PASSWORD", "DemoPassword123!")
        demo_name = os.getenv("DEMO_USER_NAME", "Security Lead").strip()
        demo_ws_name = os.getenv("DEMO_WORKSPACE_NAME", "Demonstration Workspace").strip()

        now = datetime.now(timezone.utc)

        # 2. Idempotently create or update demo user
        user = db.query(User).filter(User.email == demo_email).first()
        hashed_pwd = hash_password(demo_password)

        if not user:
            user = User(
                id=str(uuid.uuid4()),
                email=demo_email,
                password_hash=hashed_pwd,
                full_name=demo_name,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"[Seed] Created demo user: {demo_email} (ID: {user.id})")
        else:
            user.password_hash = hashed_pwd
            user.full_name = demo_name
            user.is_active = True
            user.updated_at = now
            db.commit()
            db.refresh(user)
            print(f"[Seed] Verified/updated demo user: {demo_email} (ID: {user.id})")

        # 3. Ensure Personal Workspace exists (clean slate for live AWS testing)
        personal_ws = (
            db.query(Workspace)
            .filter(Workspace.owner_id == user.id, Workspace.name == "Personal Workspace")
            .first()
        )
        if not personal_ws:
            personal_ws = Workspace(
                id=str(uuid.uuid4()),
                name="Personal Workspace",
                owner_id=user.id,
                created_at=now,
                updated_at=now,
            )
            db.add(personal_ws)
            db.commit()
            db.refresh(personal_ws)

            member = WorkspaceMember(
                id=str(uuid.uuid4()),
                workspace_id=personal_ws.id,
                user_id=user.id,
                role="OWNER",
                created_at=now,
            )
            db.add(member)
            db.commit()
            print(f"[Seed] Created Personal Workspace (ID: {personal_ws.id})")
        else:
            print(f"[Seed] Personal Workspace verified (ID: {personal_ws.id})")

        # 4. Ensure Demonstration Workspace exists (for safe professor demonstration)
        demo_ws = (
            db.query(Workspace)
            .filter(Workspace.owner_id == user.id, Workspace.name == demo_ws_name)
            .first()
        )
        if not demo_ws:
            demo_ws = Workspace(
                id=str(uuid.uuid4()),
                name=demo_ws_name,
                owner_id=user.id,
                created_at=now,
                updated_at=now,
            )
            db.add(demo_ws)
            db.commit()
            db.refresh(demo_ws)

            demo_member = WorkspaceMember(
                id=str(uuid.uuid4()),
                workspace_id=demo_ws.id,
                user_id=user.id,
                role="OWNER",
                created_at=now,
            )
            db.add(demo_member)
            db.commit()
            print(f"[Seed] Created Demonstration Workspace (ID: {demo_ws.id})")
        else:
            print(f"[Seed] Demonstration Workspace verified (ID: {demo_ws.id})")

        # 5. Ensure simulated AWS connection exists for Demonstration Workspace
        demo_conn = (
            db.query(AWSConnection)
            .filter(AWSConnection.id == "demo-simulated-connection")
            .first()
        )
        if not demo_conn:
            demo_conn = AWSConnection(
                id="demo-simulated-connection",
                workspace_id=demo_ws.id,
                account_id="123456789012 (Demo)",
                role_arn="arn:aws:iam::123456789012:role/CloudGuardDemoRole",
                region="us-east-1",
                status="CONNECTED",
                created_at=now,
                updated_at=now,
                last_verified_at=now,
            )
            db.add(demo_conn)
            db.commit()
            print(f"[Seed] Created simulated AWS connection for Demonstration Workspace (ID: {demo_conn.id})")
        else:
            print(f"[Seed] Simulated AWS connection verified (ID: {demo_conn.id})")

        # 6. Populate deterministic simulated resources and findings in Demonstration Workspace
        # Check if demonstration scan already exists
        demo_scan = (
            db.query(Scan)
            .filter(Scan.workspace_id == demo_ws.id, Scan.aws_connection_id == "demo-simulated-connection")
            .first()
        )

        simulated_resources_defs = [
            {
                "resource_id": "demo-s3-public-bucket",
                "service": "s3",
                "resource_type": "bucket",
                "region": "us-east-1",
                "arn": "arn:aws:demo:us-east-1:123456789012:s3:demo-s3-public-bucket",
                "status": "active",
                "metadata_json": {
                    "simulated": True,
                    "PublicAccessBlockConfiguration": {"BlockPublicAcls": False, "BlockPublicPolicy": False},
                },
            },
            {
                "resource_id": "demo-web-server-ec2",
                "service": "ec2",
                "resource_type": "instance",
                "region": "us-east-1",
                "arn": "arn:aws:demo:us-east-1:123456789012:instance/demo-web-server-ec2",
                "status": "running",
                "metadata_json": {
                    "simulated": True,
                    "PublicIpAddress": "54.210.10.99",
                    "State": {"Name": "running"},
                },
            },
            {
                "resource_id": "demo-open-ssh-sg",
                "service": "ec2",
                "resource_type": "security_group",
                "region": "us-east-1",
                "arn": "arn:aws:demo:us-east-1:123456789012:security-group/demo-open-ssh-sg",
                "status": "active",
                "metadata_json": {
                    "simulated": True,
                    "IpPermissions": [{
                        "IpProtocol": "tcp",
                        "FromPort": 22,
                        "ToPort": 22,
                        "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                    }],
                },
            },
            {
                "resource_id": "demo-unencrypted-rds",
                "service": "rds",
                "resource_type": "db_instance",
                "region": "us-east-1",
                "arn": "arn:aws:demo:us-east-1:123456789012:rds:demo-unencrypted-rds",
                "status": "available",
                "metadata_json": {
                    "simulated": True,
                    "StorageEncrypted": False,
                    "PubliclyAccessible": False,
                },
            },
            {
                "resource_id": "demo-iam-admin-no-mfa",
                "service": "iam",
                "resource_type": "user",
                "region": "global",
                "arn": "arn:aws:demo::123456789012:user/demo-iam-admin-no-mfa",
                "status": "active",
                "metadata_json": {
                    "simulated": True,
                    "HasAdminAccess": True,
                    "MFADevices": [],
                },
            },
            {
                "resource_id": "demo-cloudtrail-disabled",
                "service": "cloudtrail",
                "resource_type": "trail",
                "region": "us-east-1",
                "arn": "arn:aws:demo:us-east-1:123456789012:trail/demo-cloudtrail-disabled",
                "status": "inactive",
                "metadata_json": {
                    "simulated": True,
                    "IsLogging": False,
                    "IsMultiRegionTrail": False,
                },
            },
        ]

        # Seed or refresh simulated resources
        for rdef in simulated_resources_defs:
            existing_r = (
                db.query(CloudResource)
                .filter(CloudResource.workspace_id == demo_ws.id, CloudResource.resource_id == rdef["resource_id"])
                .first()
            )
            if not existing_r:
                res = CloudResource(
                    id=str(uuid.uuid4()),
                    workspace_id=demo_ws.id,
                    aws_connection_id="demo-simulated-connection",
                    service=rdef["service"],
                    resource_type=rdef["resource_type"],
                    resource_id=rdef["resource_id"],
                    resource_name=rdef["resource_id"],
                    name=rdef["resource_id"],
                    region=rdef["region"],
                    arn=rdef["arn"],
                    status=rdef["status"],
                    metadata_json=rdef["metadata_json"],
                    discovered_at=now,
                    updated_at=now,
                )
                db.add(res)
        db.commit()

        # Seed or refresh demonstration scan
        if not demo_scan:
            scan_id = str(uuid.uuid4())
            demo_scan = Scan(
                id=scan_id,
                workspace_id=demo_ws.id,
                aws_connection_id="demo-simulated-connection",
                status="COMPLETED",
                started_at=now,
                completed_at=now,
                resources_scanned=len(simulated_resources_defs),
                checks_attempted=11,
                checks_completed=11,
                checks_passed=6,
                checks_failed=5,
                checks_errored=0,
                coverage_percentage=100,
                security_score=68,
                security_rating="Fair",
                created_at=now,
            )
            db.add(demo_scan)
            db.commit()

            # Seed simulated findings clearly labeled
            simulated_findings_defs = [
                {
                    "rule_id": "s3-public-access",
                    "resource_id": "demo-s3-public-bucket",
                    "title": "[SIMULATED] S3 Bucket Allows Public Access",
                    "description": "S3 bucket configuration permits public access policies or public ACLs.",
                    "severity": "CRITICAL",
                    "category": "Storage",
                    "service": "s3",
                    "region": "us-east-1",
                    "risk_score": 92,
                    "priority": "P1",
                    "recommendation": "Enable S3 Block Public Access at the bucket and account level.",
                    "evidence": {
                        "simulated": True,
                        "source": "Deterministic Demonstration Mode (Simulated - Not from live AWS account)",
                        "bucket": "demo-s3-public-bucket",
                        "block_public_acls": False,
                        "block_public_policy": False,
                    },
                },
                {
                    "rule_id": "security-group-exposed-ports",
                    "resource_id": "demo-open-ssh-sg",
                    "title": "[SIMULATED] EC2 Security Group Exposes SSH (Port 22) to World",
                    "description": "Security Group rule permits ingress on SSH port 22 from 0.0.0.0/0.",
                    "severity": "HIGH",
                    "category": "Network",
                    "service": "ec2",
                    "region": "us-east-1",
                    "risk_score": 82,
                    "priority": "P2",
                    "recommendation": "Restrict SSH inbound access to specific corporate IP CIDR or bastion host.",
                    "evidence": {
                        "simulated": True,
                        "source": "Deterministic Demonstration Mode (Simulated - Not from live AWS account)",
                        "port": 22,
                        "cidr": "0.0.0.0/0",
                    },
                },
                {
                    "rule_id": "rds-encryption",
                    "resource_id": "demo-unencrypted-rds",
                    "title": "[SIMULATED] RDS Database Storage Encryption Not Enabled",
                    "description": "Relational Database Service instance is running with unencrypted storage.",
                    "severity": "MEDIUM",
                    "category": "Database",
                    "service": "rds",
                    "region": "us-east-1",
                    "risk_score": 64,
                    "priority": "P3",
                    "recommendation": "Enable AWS KMS customer managed or default encryption for RDS instances.",
                    "evidence": {
                        "simulated": True,
                        "source": "Deterministic Demonstration Mode (Simulated - Not from live AWS account)",
                        "storage_encrypted": False,
                    },
                },
                {
                    "rule_id": "iam-mfa",
                    "resource_id": "demo-iam-admin-no-mfa",
                    "title": "[SIMULATED] Privileged IAM User Missing Multi-Factor Authentication",
                    "description": "IAM user with administrator permissions does not have MFA configured.",
                    "severity": "HIGH",
                    "category": "Identity",
                    "service": "iam",
                    "region": "global",
                    "risk_score": 78,
                    "priority": "P2",
                    "recommendation": "Enforce MFA for all users with AdministratorAccess or console credentials.",
                    "evidence": {
                        "simulated": True,
                        "source": "Deterministic Demonstration Mode (Simulated - Not from live AWS account)",
                        "mfa_active": False,
                    },
                },
                {
                    "rule_id": "cloudtrail-logging",
                    "resource_id": "demo-cloudtrail-disabled",
                    "title": "[SIMULATED] CloudTrail Logging Disabled or Single-Region Only",
                    "description": "CloudTrail trail is either inactive or does not capture events in all regions.",
                    "severity": "MEDIUM",
                    "category": "Monitoring",
                    "service": "cloudtrail",
                    "region": "us-east-1",
                    "risk_score": 52,
                    "priority": "P3",
                    "recommendation": "Enable multi-region logging for CloudTrail to record global AWS API actions.",
                    "evidence": {
                        "simulated": True,
                        "source": "Deterministic Demonstration Mode (Simulated - Not from live AWS account)",
                        "is_logging": False,
                    },
                },
            ]

            for fdef in simulated_findings_defs:
                finding = Finding(
                    id=str(uuid.uuid4()),
                    scan_id=demo_scan.id,
                    workspace_id=demo_ws.id,
                    resource_id=fdef["resource_id"],
                    rule_id=fdef["rule_id"],
                    title=fdef["title"],
                    description=fdef["description"],
                    severity=fdef["severity"],
                    category=fdef["category"],
                    service=fdef["service"],
                    region=fdef["region"],
                    risk_score=fdef["risk_score"],
                    priority=fdef["priority"],
                    status="OPEN",
                    recommendation=fdef["recommendation"],
                    evidence=fdef["evidence"],
                    risk_factors=["simulated_demonstration"],
                    created_at=now,
                    detected_at=now,
                )
                db.add(finding)

            # Category scores
            cat_scores = [
                ("Storage", 70, "Fair", 1, 1, 0),
                ("Network", 75, "Fair", 1, 0, 1),
                ("Database", 80, "Good", 1, 0, 0),
                ("Identity", 65, "Fair", 1, 0, 1),
                ("Monitoring", 85, "Good", 1, 0, 0),
            ]
            for cat, score, cat_status, count, crit, high in cat_scores:
                cs = CategoryScore(
                    id=str(uuid.uuid4()),
                    scan_id=demo_scan.id,
                    category=cat,
                    score=score,
                    status=cat_status,
                    finding_count=count,
                    critical_count=crit,
                    high_count=high,
                )
                db.add(cs)

            db.commit()
            print(f"[Seed] Created simulated demonstration scan with 5 findings (Scan ID: {demo_scan.id})")
        else:
            print(f"[Seed] Demonstration scan verified (Scan ID: {demo_scan.id})")

        print("[Seed] Seed process completed idempotently.")
        return {
            "user_id": user.id,
            "email": user.email,
            "personal_workspace_id": personal_ws.id,
            "demonstration_workspace_id": demo_ws.id,
        }

    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_environment()
