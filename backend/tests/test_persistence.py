import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import settings
from app.models.aws_connection import AWSConnection
from app.models.scan import Scan
from app.models.resource import CloudResource
from app.models.finding import Finding
from app.models.check_result import CheckResult
from app.models.category_score import CategoryScore
from app.models import Base
from app.database.dependencies import get_db

# Create a file-based SQLite database for testing to avoid connection scoping issues
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
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables
    Base.metadata.drop_all(bind=engine)

@patch("app.services.aws_connection_service.aws_connection_service.get_client_factory")
@patch("app.services.aws_connection_service.aws_connection_service.get_status")
@patch("app.scanner.manager.discovery_service.run_discovery")
def test_run_scan_persistence_success(mock_run_discovery, mock_get_status, mock_get_client_factory):
    # Mock connection info
    mock_factory = MagicMock()
    mock_get_client_factory.return_value = mock_factory
    
    mock_status = MagicMock()
    mock_status.connected = True
    mock_status.region = "us-east-1"
    mock_status.account_id = "123456789012"
    mock_get_status.return_value = mock_status
    
    # Pre-populate the aws_connections table in our in-memory DB because scan foreign keys to it
    db = TestingSessionLocal()
    from app.repositories.aws_connection import aws_connection_repo
    aws_connection_repo.create(db, account_id="123456789012", role_arn="arn:aws:iam::123456789012:role/CloudGuard", region="us-east-1")
    db.commit()
    db.close()
    
    def create_client_side_effect(service_name):
        mock_client = MagicMock()
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
        cloudtrails=[]
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
    
    def create_client_override(service_name):
        if service_name == "ec2": return mock_ec2_client
        return MagicMock()
    mock_factory.create_client.side_effect = create_client_override

    # Trigger scan with account_id query param
    response = client.post(f"{settings.API_V1_STR}/scans/?account_id=123456789012")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "COMPLETED"
    assert data["account_id"] == "123456789012"
    assert data["summary"]["resources_scanned"] == 3
    
    scan_id = data["scan_id"]
    
    # Test get scan status from DB
    status_response = client.get(f"{settings.API_V1_STR}/scans/{scan_id}")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "COMPLETED"
    
    # Test list findings from DB
    findings_response = client.get(f"{settings.API_V1_STR}/scans/findings/?severity=CRITICAL&scan_id={scan_id}")
    assert findings_response.status_code == 200
    assert len(findings_response.json()) >= 1
    
    # Test Dashboard API from DB
    dash_response = client.get(f"{settings.API_V1_STR}/dashboard")
    assert dash_response.status_code == 200
    dash_data = dash_response.json()
    assert dash_data["security_score"] is not None
    assert len(dash_data["top_risks"]) > 0
