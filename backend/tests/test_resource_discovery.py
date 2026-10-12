from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from botocore.exceptions import ClientError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models import Base, User, Workspace, WorkspaceMember, AWSConnection, CloudResource
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

ROLE_ARN = "arn:aws:iam::123456789012:role/CloudGuardAudit"
REGION = "us-east-1"

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def create_user_workspace_and_connection(email: str, name: str) -> tuple[str, str, str, str]:
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
    user_id = user.id
    token = create_access_token(subject=user_id)

    ws = Workspace(name=f"{name}'s Workspace", owner_id=user_id)
    db.add(ws)
    db.commit()
    db.refresh(ws)
    ws_id = ws.id

    member = WorkspaceMember(workspace_id=ws_id, user_id=user_id, role="OWNER")
    db.add(member)

    conn = AWSConnection(
        id=f"conn-{user_id[:8]}",
        workspace_id=ws_id,
        account_id="123456789012",
        role_arn=ROLE_ARN,
        region=REGION,
        status="CONNECTED",
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    conn_id = conn.id
    db.close()

    return user_id, token, ws_id, conn_id

def add_member(ws_id: str, user_id: str, role: str):
    db = TestingSessionLocal()
    member = WorkspaceMember(workspace_id=ws_id, user_id=user_id, role=role)
    db.add(member)
    db.commit()
    db.close()


def setup_mock_factory(mock_client_factory, s3=None, ec2=None, iam=None, rds=None, cloudtrail=None):
    mock_factory = MagicMock()
    mock_client_factory.return_value = mock_factory

    def create_client_impl(service_name, region_name=None):
        if service_name == "s3":
            return s3 or MagicMock()
        if service_name == "ec2":
            return ec2 or MagicMock()
        if service_name == "iam":
            return iam or MagicMock()
        if service_name == "rds":
            return rds or MagicMock()
        if service_name == "cloudtrail":
            return cloudtrail or MagicMock()
        return MagicMock()

    mock_factory.create_client.side_effect = create_client_impl
    return mock_factory


@patch("app.services.aws_connection_service.aws_connection_service.get_client_factory_for_connection")
def test_s3_discovery(mock_client_factory):
    """Test S3 bucket discovery and normalization into database."""
    mock_s3 = MagicMock()
    mock_s3.list_buckets.return_value = {
        "Buckets": [
            {"Name": "prod-data-bucket", "CreationDate": "2026-01-10T12:00:00Z"},
            {"Name": "public-assets-bucket", "CreationDate": "2026-02-15T08:30:00Z"},
        ]
    }
    mock_s3.get_bucket_location.side_effect = lambda Bucket: {"LocationConstraint": "us-east-1"}

    setup_mock_factory(mock_client_factory, s3=mock_s3)
    user_id, token, ws_id, conn_id = create_user_workspace_and_connection("alice@cloudguard.io", "Alice")

    res = client.post(
        "/api/v1/discovery/run",
        json={"workspace_id": ws_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["service_summary"]["s3"] == 2

    # Verify database persistence
    db = TestingSessionLocal()
    resources = db.query(CloudResource).filter(CloudResource.workspace_id == ws_id, CloudResource.service == "s3").all()
    assert len(resources) == 2
    names = [r.resource_name for r in resources]
    assert "prod-data-bucket" in names
    assert "public-assets-bucket" in names
    assert resources[0].arn.startswith("arn:aws:s3:::")
    db.close()


@patch("app.services.aws_connection_service.aws_connection_service.get_client_factory_for_connection")
def test_ec2_and_security_group_discovery(mock_client_factory):
    """Test EC2 instances and Security Groups discovery."""
    mock_ec2 = MagicMock()
    
    # Mock EC2 instances
    ec2_paginator = MagicMock()
    ec2_paginator.paginate.return_value = [{
        "Reservations": [{
            "Instances": [{
                "InstanceId": "i-0abcd1234ef567890",
                "InstanceType": "t3.medium",
                "State": {"Name": "running"},
                "PublicIpAddress": "54.210.10.20",
                "PrivateIpAddress": "10.0.1.50",
                "VpcId": "vpc-0123456",
                "Tags": [{"Key": "Name", "Value": "prod-web-server"}, {"Key": "Env", "Value": "prod"}],
                "SecurityGroups": [{"GroupId": "sg-999", "GroupName": "web-sg"}],
            }]
        }]
    }]

    # Mock Security Groups
    sg_paginator = MagicMock()
    sg_paginator.paginate.return_value = [{
        "SecurityGroups": [{
            "GroupId": "sg-0123456789",
            "GroupName": "launch-wizard-1",
            "Description": "Public SSH access",
            "VpcId": "vpc-0123456",
            "IpPermissions": [{"FromPort": 22, "ToPort": 22, "IpProtocol": "tcp"}],
            "IpPermissionsEgress": [{"IpProtocol": "-1"}],
        }]
    }]

    def get_paginator(operation):
        if operation == "describe_instances": return ec2_paginator
        if operation == "describe_security_groups": return sg_paginator
        return MagicMock()

    mock_ec2.get_paginator.side_effect = get_paginator
    setup_mock_factory(mock_client_factory, ec2=mock_ec2)

    user_id, token, ws_id, conn_id = create_user_workspace_and_connection("alice@cloudguard.io", "Alice")

    res = client.post(
        "/api/v1/discovery/run",
        json={"workspace_id": ws_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["service_summary"]["ec2"] == 1
    assert data["service_summary"]["security_group"] == 1

    # Verify database
    db = TestingSessionLocal()
    ec2_item = db.query(CloudResource).filter(CloudResource.resource_id == "i-0abcd1234ef567890").first()
    assert ec2_item is not None
    assert ec2_item.resource_name == "prod-web-server"
    assert ec2_item.status == "running"
    assert ec2_item.metadata_json["instance_type"] == "t3.medium"
    assert ec2_item.metadata_json["public_ip"] == "54.210.10.20"

    sg_item = db.query(CloudResource).filter(CloudResource.resource_id == "sg-0123456789").first()
    assert sg_item is not None
    assert sg_item.resource_name == "launch-wizard-1"
    assert sg_item.metadata_json["inbound_rules_count"] == 1
    db.close()


@patch("app.services.aws_connection_service.aws_connection_service.get_client_factory_for_connection")
def test_iam_discovery(mock_client_factory):
    """Test IAM users and roles discovery."""
    mock_iam = MagicMock()
    user_paginator = MagicMock()
    user_paginator.paginate.return_value = [{
        "Users": [
            {"UserName": "deployer", "UserId": "AIDA12345", "Arn": "arn:aws:iam::123456789012:user/deployer", "Path": "/"}
        ]
    }]
    role_paginator = MagicMock()
    role_paginator.paginate.return_value = [{
        "Roles": [
            {"RoleName": "LambdaExecutionRole", "RoleId": "AROA98765", "Arn": "arn:aws:iam::123456789012:role/LambdaExecutionRole", "Path": "/"}
        ]
    }]

    def get_paginator(operation):
        if operation == "list_users": return user_paginator
        if operation == "list_roles": return role_paginator
        return MagicMock()

    mock_iam.get_paginator.side_effect = get_paginator
    setup_mock_factory(mock_client_factory, iam=mock_iam)

    user_id, token, ws_id, conn_id = create_user_workspace_and_connection("alice@cloudguard.io", "Alice")

    res = client.post(
        "/api/v1/discovery/run",
        json={"workspace_id": ws_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["service_summary"]["iam"] == 2 # 1 user + 1 role

    db = TestingSessionLocal()
    iam_user = db.query(CloudResource).filter(CloudResource.resource_type == "iam:user").first()
    assert iam_user.resource_id == "deployer"
    assert iam_user.region == "global"

    iam_role = db.query(CloudResource).filter(CloudResource.resource_type == "iam:role").first()
    assert iam_role.resource_id == "LambdaExecutionRole"
    db.close()


@patch("app.services.aws_connection_service.aws_connection_service.get_client_factory_for_connection")
def test_rds_discovery(mock_client_factory):
    """Test RDS DB instance discovery and metadata extraction."""
    mock_rds = MagicMock()
    rds_paginator = MagicMock()
    rds_paginator.paginate.return_value = [{
        "DBInstances": [{
            "DBInstanceIdentifier": "postgres-prod",
            "Engine": "postgres",
            "EngineVersion": "15.3",
            "DBInstanceClass": "db.m5.large",
            "DBInstanceStatus": "available",
            "AllocatedStorage": 100,
            "MultiAZ": True,
            "PubliclyAccessible": False,
            "StorageEncrypted": True,
            "Endpoint": {"Address": "postgres-prod.xyz.us-east-1.rds.amazonaws.com", "Port": 5432},
        }]
    }]
    mock_rds.get_paginator.return_value = rds_paginator

    setup_mock_factory(mock_client_factory, rds=mock_rds)
    user_id, token, ws_id, conn_id = create_user_workspace_and_connection("alice@cloudguard.io", "Alice")

    res = client.post(
        "/api/v1/discovery/run",
        json={"workspace_id": ws_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["service_summary"]["rds"] == 1

    db = TestingSessionLocal()
    rds_item = db.query(CloudResource).filter(CloudResource.resource_id == "postgres-prod").first()
    assert rds_item is not None
    assert rds_item.metadata_json["engine"] == "postgres"
    assert rds_item.metadata_json["multi_az"] is True
    assert rds_item.metadata_json["publicly_accessible"] is False
    db.close()


@patch("app.services.aws_connection_service.aws_connection_service.get_client_factory_for_connection")
def test_cloudtrail_discovery(mock_client_factory):
    """Test CloudTrail trails discovery."""
    mock_ct = MagicMock()
    mock_ct.describe_trails.return_value = {
        "trailList": [{
            "Name": "main-audit-trail",
            "TrailARN": "arn:aws:cloudtrail:us-east-1:123456789012:trail/main-audit-trail",
            "HomeRegion": "us-east-1",
            "IsMultiRegionTrail": True,
            "S3BucketName": "audit-logs-bucket",
            "LogFileValidationEnabled": True,
        }]
    }

    setup_mock_factory(mock_client_factory, cloudtrail=mock_ct)
    user_id, token, ws_id, conn_id = create_user_workspace_and_connection("alice@cloudguard.io", "Alice")

    res = client.post(
        "/api/v1/discovery/run",
        json={"workspace_id": ws_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["service_summary"]["cloudtrail"] == 1

    db = TestingSessionLocal()
    trail_item = db.query(CloudResource).filter(CloudResource.resource_id == "main-audit-trail").first()
    assert trail_item is not None
    assert trail_item.metadata_json["is_multi_region"] is True
    assert trail_item.metadata_json["s3_bucket_name"] == "audit-logs-bucket"
    db.close()


@patch("app.services.aws_connection_service.aws_connection_service.get_client_factory_for_connection")
def test_pagination_multiple_pages(mock_client_factory):
    """Test pagination handling across multi-page AWS API responses."""
    mock_ec2 = MagicMock()
    ec2_paginator = MagicMock()
    ec2_paginator.paginate.return_value = [
        {"Reservations": [{"Instances": [{"InstanceId": "i-page1", "InstanceType": "t3.micro", "State": {"Name": "running"}}]}]},
        {"Reservations": [{"Instances": [{"InstanceId": "i-page2", "InstanceType": "t3.small", "State": {"Name": "running"}}]}]},
        {"Reservations": [{"Instances": [{"InstanceId": "i-page3", "InstanceType": "t3.medium", "State": {"Name": "stopped"}}]}]},
    ]
    sg_paginator = MagicMock()
    sg_paginator.paginate.return_value = [{"SecurityGroups": []}]

    def get_paginator(op):
        if op == "describe_instances": return ec2_paginator
        return sg_paginator

    mock_ec2.get_paginator.side_effect = get_paginator
    setup_mock_factory(mock_client_factory, ec2=mock_ec2)

    user_id, token, ws_id, conn_id = create_user_workspace_and_connection("alice@cloudguard.io", "Alice")

    res = client.post(
        "/api/v1/discovery/run",
        json={"workspace_id": ws_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["service_summary"]["ec2"] == 3

    db = TestingSessionLocal()
    instances = db.query(CloudResource).filter(CloudResource.workspace_id == ws_id, CloudResource.service == "ec2", CloudResource.resource_type == "ec2:instance").all()
    assert len(instances) == 3
    instance_ids = [i.resource_id for i in instances]
    assert "i-page1" in instance_ids
    assert "i-page2" in instance_ids
    assert "i-page3" in instance_ids
    db.close()


@patch("app.services.aws_connection_service.aws_connection_service.get_client_factory_for_connection")
def test_service_access_denied_graceful_handling(mock_client_factory):
    """If one service (e.g. RDS) raises AccessDenied, other services still succeed."""
    mock_s3 = MagicMock()
    mock_s3.list_buckets.return_value = {"Buckets": [{"Name": "resilient-bucket"}]}
    mock_s3.get_bucket_location.return_value = {"LocationConstraint": "us-east-1"}

    mock_rds = MagicMock()
    mock_rds.get_paginator.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "User is not authorized to perform rds:DescribeDBInstances"}},
        "DescribeDBInstances"
    )

    setup_mock_factory(mock_client_factory, s3=mock_s3, rds=mock_rds)
    user_id, token, ws_id, conn_id = create_user_workspace_and_connection("alice@cloudguard.io", "Alice")

    res = client.post(
        "/api/v1/discovery/run",
        json={"workspace_id": ws_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    # S3 succeeded
    assert data["service_summary"]["s3"] == 1
    # RDS recorded graceful error
    assert "rds" in data["service_errors"]
    assert "AccessDenied" in data["service_errors"]["rds"]

    # Verify S3 was persisted to DB despite RDS failing
    db = TestingSessionLocal()
    s3_item = db.query(CloudResource).filter(CloudResource.resource_id == "resilient-bucket").first()
    assert s3_item is not None
    db.close()


@patch("app.services.aws_connection_service.aws_connection_service.get_client_factory_for_connection")
def test_empty_results(mock_client_factory):
    """Empty AWS accounts return 0 resources cleanly with no errors."""
    mock_s3 = MagicMock()
    mock_s3.list_buckets.return_value = {"Buckets": []}

    mock_ec2 = MagicMock()
    ec2_paginator = MagicMock()
    ec2_paginator.paginate.return_value = [{"Reservations": []}]
    sg_paginator = MagicMock()
    sg_paginator.paginate.return_value = [{"SecurityGroups": []}]
    mock_ec2.get_paginator.side_effect = lambda op: ec2_paginator if op == "describe_instances" else sg_paginator

    mock_iam = MagicMock()
    iam_paginator = MagicMock()
    iam_paginator.paginate.return_value = [{"Users": [], "Roles": []}]
    mock_iam.get_paginator.return_value = iam_paginator

    mock_rds = MagicMock()
    rds_paginator = MagicMock()
    rds_paginator.paginate.return_value = [{"DBInstances": []}]
    mock_rds.get_paginator.return_value = rds_paginator

    mock_ct = MagicMock()
    mock_ct.describe_trails.return_value = {"trailList": []}

    setup_mock_factory(mock_client_factory, s3=mock_s3, ec2=mock_ec2, iam=mock_iam, rds=mock_rds, cloudtrail=mock_ct)

    user_id, token, ws_id, conn_id = create_user_workspace_and_connection("alice@cloudguard.io", "Alice")

    res = client.post(
        "/api/v1/discovery/run",
        json={"workspace_id": ws_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["resources_count"] == 0
    assert data["service_errors"] == {}


@patch("app.services.aws_connection_service.aws_connection_service.get_client_factory_for_connection")
def test_workspace_isolation_anti_idor(mock_client_factory):
    """Verify that User B cannot trigger discovery or list resources for User A's workspace."""
    mock_s3 = MagicMock()
    mock_s3.list_buckets.return_value = {"Buckets": [{"Name": "alice-private-bucket"}]}
    mock_s3.get_bucket_location.return_value = {"LocationConstraint": "us-east-1"}

    setup_mock_factory(mock_client_factory, s3=mock_s3)

    alice_id, alice_token, ws_alice_id, _ = create_user_workspace_and_connection("alice@cloudguard.io", "Alice")
    bob_id, bob_token, ws_bob_id, _ = create_user_workspace_and_connection("bob@cloudguard.io", "Bob")

    # 1. Alice runs discovery for her workspace -> 200
    alice_res = client.post(
        "/api/v1/discovery/run",
        json={"workspace_id": ws_alice_id},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert alice_res.status_code == 200

    # 2. Bob tries to run discovery for Alice's workspace -> 403 Forbidden
    bob_run_res = client.post(
        "/api/v1/discovery/run",
        json={"workspace_id": ws_alice_id},
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert bob_run_res.status_code == 403
    assert "not a member" in bob_run_res.json()["detail"].lower()

    # 3. Bob tries to list Alice's resources -> 403 Forbidden
    bob_list_res = client.get(
        f"/api/v1/resources?workspace_id={ws_alice_id}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert bob_list_res.status_code == 403
    assert "not a member" in bob_list_res.json()["detail"].lower()

    # 4. Charlie added as VIEWER to Alice's workspace tries to run discovery -> 403 Forbidden
    charlie_db = TestingSessionLocal()
    charlie = User(email="charlie@cloudguard.io", password_hash=hash_password("Pass123!"), full_name="Charlie", is_active=True)
    charlie_db.add(charlie)
    charlie_db.commit()
    charlie_db.refresh(charlie)
    charlie_token = create_access_token(subject=charlie.id)
    charlie_db.close()

    add_member(ws_alice_id, charlie.id, "VIEWER")

    viewer_run_res = client.post(
        "/api/v1/discovery/run",
        json={"workspace_id": ws_alice_id},
        headers={"Authorization": f"Bearer {charlie_token}"},
    )
    assert viewer_run_res.status_code == 403
    assert "viewers cannot" in viewer_run_res.json()["detail"].lower()

    # But Charlie as VIEWER CAN view the resources (read-only) -> 200
    viewer_view_res = client.get(
        f"/api/v1/resources?workspace_id={ws_alice_id}",
        headers={"Authorization": f"Bearer {charlie_token}"},
    )
    assert viewer_view_res.status_code == 200
    assert len(viewer_view_res.json()) >= 1
