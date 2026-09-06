from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from botocore.exceptions import ClientError

from app.main import app
from app.core.config import settings

client = TestClient(app)

VALID_ROLE_ARN = "arn:aws:iam::123456789012:role/CloudGuardScannerRole"
INVALID_ROLE_ARN = "invalid-role-arn"
REGION = "us-east-1"

def test_connect_invalid_arn():
    response = client.post(
        f"{settings.API_V1_STR}/aws/connect",
        json={"role_arn": INVALID_ROLE_ARN, "region": REGION}
    )
    assert response.status_code == 422 # Pydantic validation fails first

@patch("app.aws.connection.boto3.client")
@patch("app.aws.connection.boto3.Session")
def test_connect_success(mock_session, mock_boto3_client):
    # Mock STS AssumeRole response
    mock_sts_client = MagicMock()
    mock_boto3_client.return_value = mock_sts_client
    mock_sts_client.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "AKIAIOSFODNN7EXAMPLE",
            "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "SessionToken": "session-token-123"
        }
    }
    
    # Mock STS GetCallerIdentity response
    mock_session_instance = MagicMock()
    mock_session.return_value = mock_session_instance
    mock_session_sts_client = MagicMock()
    mock_session_instance.client.return_value = mock_session_sts_client
    mock_session_sts_client.get_caller_identity.return_value = {
        "Account": "123456789012",
        "Arn": "arn:aws:sts::123456789012:assumed-role/CloudGuardScannerRole/session"
    }

    response = client.post(
        f"{settings.API_V1_STR}/aws/connect",
        json={"role_arn": VALID_ROLE_ARN, "region": REGION}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["account_id"] == "123456789012"
    assert "identity_arn" in data
    # Ensure credentials are NOT leaked in response
    assert "Credentials" not in data
    assert "AccessKeyId" not in data

@patch("app.aws.connection.boto3.client")
def test_connect_access_denied(mock_boto3_client):
    mock_sts_client = MagicMock()
    mock_boto3_client.return_value = mock_sts_client
    
    # Simulate AccessDenied Exception
    error_response = {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}
    mock_sts_client.assume_role.side_effect = ClientError(error_response, "AssumeRole")

    response = client.post(
        f"{settings.API_V1_STR}/aws/connect",
        json={"role_arn": VALID_ROLE_ARN, "region": REGION}
    )
    
    assert response.status_code == 403
    assert "authorized to assume" in response.json()["detail"]

def test_disconnect():
    response = client.post(f"{settings.API_V1_STR}/aws/disconnect")
    assert response.status_code == 200
    assert response.json()["connected"] is False

def test_status_disconnected():
    # Calling disconnect first to ensure clean state
    client.post(f"{settings.API_V1_STR}/aws/disconnect")
    
    response = client.get(f"{settings.API_V1_STR}/aws/status")
    assert response.status_code == 200
    assert response.json()["connected"] is False
