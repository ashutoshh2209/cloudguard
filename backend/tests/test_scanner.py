from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import settings
from app.models import Base
from app.core.database import get_db

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

import pytest
@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    from app.repositories.aws_connection import aws_connection_repo
    aws_connection_repo.create(db, account_id="123456789012", role_arn="arn:aws:iam::123456789012:role/CloudGuard", region="us-east-1")
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)

def test_run_scan_without_connection():
    # Ensure no connection exists
    client.post(f"{settings.API_V1_STR}/aws/disconnect")
    
    response = client.post(f"{settings.API_V1_STR}/scans", params={"account_id": "000000000000"})
    assert response.status_code == 404
    assert "AWS connection not found" in response.json()["detail"]

@patch("app.services.aws_connection_service.aws_connection_service.get_client_factory")
@patch("app.services.aws_connection_service.aws_connection_service.get_status")
@patch("app.scanner.manager.discovery_service.run_discovery")
def test_run_scan_success(mock_run_discovery, mock_get_status, mock_get_client_factory):
    # Mock connection info
    mock_factory = MagicMock()
    mock_get_client_factory.return_value = mock_factory
    mock_status = MagicMock()
    mock_status.region = "us-east-1"
    mock_status.account_id = "123456789012"
    mock_get_status.return_value = mock_status
    
    def create_client_side_effect(service_name):
        mock_client = MagicMock()
        # Setup specific mock behaviors for scanner context prep if needed
        if service_name == "s3":
            mock_client.get_bucket_encryption.return_value = {} # Simulated as encrypted if no exception
            
            # For public access test, let's mock one bucket as public via policy, one as not.
            # But the scanner prepares context based on buckets. We'll simplify the mock since we just
            # want to test the orchestration and rule execution logic primarily.
            
        return mock_client
        
    mock_factory.create_client.side_effect = create_client_side_effect
    
    # Mock Discovery results
    from app.schemas.inventory import ResourceInventory, S3Bucket, EC2Instance, SecurityGroup, IAMUser, IAMRole, RDSInstance, CloudTrail
    
    inventory = ResourceInventory(
        s3_buckets=[S3Bucket(name="test-bucket", creation_date=None)],
        ec2_instances=[EC2Instance(instance_id="i-123", instance_type="t2", state="running", public_ip="1.2.3.4")],
        security_groups=[SecurityGroup(group_id="sg-123", group_name="default", description="")],
        iam_users=[],
        iam_roles=[],
        rds_instances=[],
        cloudtrails=[CloudTrail(name="test-trail", home_region="us-east-1", s3_bucket_name=None)]
    )
    mock_run_discovery.return_value = inventory
    
    # Let's mock the security group describe call to simulate open SSH
    mock_ec2_client = MagicMock()
    mock_ec2_client.describe_security_groups.return_value = {
        "SecurityGroups": [{
            "GroupId": "sg-123",
            "IpPermissions": [{
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}]
            }]
        }]
    }
    
    # Override the factory to return this specific EC2 client
    def create_client_override(service_name):
        if service_name == "ec2": return mock_ec2_client
        return MagicMock()
    mock_factory.create_client.side_effect = create_client_override

    # Trigger scan
    response = client.post(f"{settings.API_V1_STR}/scans", params={"account_id": "123456789012"})
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "COMPLETED"
    assert data["account_id"] == "123456789012"
    assert data["summary"]["resources_scanned"] == 4
    
    findings = data["findings"]
    assert len(findings) > 0
    
    # Verify EC2 Public IP finding
    public_ip_finding = next((f for f in findings if f["rule_id"] == "EC2_PUBLIC_IP"), None)
    assert public_ip_finding is not None
    assert public_ip_finding["severity"] == "MEDIUM"
    
    # Verify SG SSH Open finding
    ssh_finding = next((f for f in findings if f["rule_id"] == "SSH_OPEN_TO_WORLD"), None)
    assert ssh_finding is not None
    assert ssh_finding["severity"] == "CRITICAL"
    
    scan_id = data["scan_id"]
    
    # Test get scan status
    status_response = client.get(f"{settings.API_V1_STR}/scans/{scan_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "COMPLETED"
    
    # Test list findings
    findings_response = client.get(f"{settings.API_V1_STR}/scans/findings/?severity=CRITICAL")
    assert findings_response.status_code == 200
    assert len(findings_response.json()) >= 1
    
    # Test finding details
    finding_id = ssh_finding["finding_id"]
    finding_detail_response = client.get(f"{settings.API_V1_STR}/scans/findings/{finding_id}")
    assert finding_detail_response.status_code == 200
    assert finding_detail_response.json()["rule_id"] == "SSH_OPEN_TO_WORLD"
