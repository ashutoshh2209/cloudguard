from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_run_discovery_without_connection():
    # Ensure no connection exists
    client.post(f"{settings.API_V1_STR}/aws/disconnect")
    
    response = client.post(f"{settings.API_V1_STR}/discovery/run")
    assert response.status_code == 400
    assert "No active AWS connection" in response.json()["detail"]

@patch("app.services.aws_connection_service.aws_connection_service.get_client_factory")
def test_run_discovery_success(mock_get_client_factory):
    # Mock the client factory
    mock_factory = MagicMock()
    mock_get_client_factory.return_value = mock_factory
    
    # Mock individual clients
    mock_s3 = MagicMock()
    mock_ec2 = MagicMock()
    mock_iam = MagicMock()
    mock_rds = MagicMock()
    mock_cloudtrail = MagicMock()
    
    def create_client_side_effect(service_name):
        if service_name == 's3': return mock_s3
        if service_name == 'ec2': return mock_ec2
        if service_name == 'iam': return mock_iam
        if service_name == 'rds': return mock_rds
        if service_name == 'cloudtrail': return mock_cloudtrail
        return MagicMock()
        
    mock_factory.create_client.side_effect = create_client_side_effect
    
    # Set up mock responses for each discovery module
    mock_s3.list_buckets.return_value = {
        "Buckets": [{"Name": "test-bucket", "CreationDate": "2023-01-01T00:00:00Z"}]
    }
    
    mock_ec2_paginator = MagicMock()
    mock_ec2_paginator.paginate.return_value = [{
        "Reservations": [{"Instances": [{"InstanceId": "i-12345", "InstanceType": "t2.micro", "State": {"Name": "running"}}]}]
    }]
    mock_ec2_sg_paginator = MagicMock()
    mock_ec2_sg_paginator.paginate.return_value = [{
        "SecurityGroups": [{"GroupId": "sg-123", "GroupName": "default"}]
    }]
    
    def get_paginator_side_effect(operation):
        if operation == 'describe_instances': return mock_ec2_paginator
        if operation == 'describe_security_groups': return mock_ec2_sg_paginator
        if operation == 'list_users':
            paginator = MagicMock()
            paginator.paginate.return_value = [{"Users": [{"UserName": "admin", "Arn": "arn:aws:iam::123:user/admin"}]}]
            return paginator
        if operation == 'list_roles':
            paginator = MagicMock()
            paginator.paginate.return_value = [{"Roles": [{"RoleName": "test-role", "Arn": "arn:aws:iam::123:role/test-role"}]}]
            return paginator
        if operation == 'describe_db_instances':
            paginator = MagicMock()
            paginator.paginate.return_value = [{"DBInstances": [{"DBInstanceIdentifier": "test-db", "Engine": "mysql", "DBInstanceStatus": "available"}]}]
            return paginator
        return MagicMock()
        
    mock_ec2.get_paginator.side_effect = get_paginator_side_effect
    mock_iam.get_paginator.side_effect = get_paginator_side_effect
    mock_rds.get_paginator.side_effect = get_paginator_side_effect
    
    mock_cloudtrail.describe_trails.return_value = {
        "trailList": [{"Name": "test-trail", "HomeRegion": "us-east-1"}]
    }

    response = client.post(f"{settings.API_V1_STR}/discovery/run")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["s3_buckets"]) == 1
    assert data["s3_buckets"][0]["name"] == "test-bucket"
    
    assert len(data["ec2_instances"]) == 1
    assert data["ec2_instances"][0]["instance_id"] == "i-12345"
    
    assert len(data["security_groups"]) == 1
    
    assert len(data["iam_users"]) == 1
    assert len(data["iam_roles"]) == 1
    
    assert len(data["rds_instances"]) == 1
    
    assert len(data["cloudtrails"]) == 1
