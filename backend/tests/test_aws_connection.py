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


def test_malformed_caller_credentials_rejected_with_sanitized_message(monkeypatch):
    """If caller credentials contain CLI commands or whitespace, fail fast with 401 and never expose secrets."""
    monkeypatch.setattr(settings, "AWS_ACCESS_KEY_ID", "aws sts get-caller-identity")
    monkeypatch.setattr(settings, "AWS_SECRET_ACCESS_KEY", "super-secret-value-do-not-expose-1234567890")

    response = client.post(
        f"{settings.API_V1_STR}/aws/connect",
        json={"role_arn": VALID_ROLE_ARN, "region": "ap-south-1"},
    )
    assert response.status_code == 401
    detail = response.json()["detail"]
    assert "malformed" in detail.lower()
    assert "super-secret-value-do-not-expose" not in detail
    assert "aws sts get-caller-identity" not in detail


@patch("app.aws.connection.boto3.client")
def test_incomplete_signature_maps_to_401_sanitized_error(mock_boto3_client):
    """AWS IncompleteSignature ClientError maps to 401 AWSAuthenticationError with a helpful message."""
    mock_sts_client = MagicMock()
    mock_boto3_client.return_value = mock_sts_client
    error_response = {
        "Error": {
            "Code": "IncompleteSignature",
            "Message": "Invalid key=value pair (missing equal-sign) in Authorization header",
        }
    }
    mock_sts_client.assume_role.side_effect = ClientError(error_response, "AssumeRole")

    response = client.post(
        f"{settings.API_V1_STR}/aws/connect",
        json={"role_arn": VALID_ROLE_ARN, "region": "ap-south-1"},
    )
    assert response.status_code == 401
    assert "invalid, expired, or malformed" in response.json()["detail"].lower()


@patch("app.aws.connection.boto3.client")
@patch("app.aws.connection.boto3.Session")
def test_regional_scp_restriction_falls_back_to_global_sts(mock_session, mock_boto3_client):
    """When an AWS Organization SCP blocks regional STS (e.g. ap-south-1), fallback to global STS (us-east-1)."""
    regional_sts = MagicMock()
    global_sts = MagicMock()

    scp_error = ClientError(
        {
            "Error": {
                "Code": "AccessDenied",
                "Message": (
                    "User is not authorized to perform: sts:AssumeRole on resource with an explicit deny "
                    "in a service control policy: arn:aws:organizations::821672147646:policy/o-123/service_control_policy/p-123"
                ),
            }
        },
        "AssumeRole",
    )
    regional_sts.assume_role.side_effect = scp_error
    global_sts.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "ASIATEST123456789012",
            "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "SessionToken": "session-token-123",
        }
    }

    def client_side_effect(service_name, **kwargs):
        if kwargs.get("region_name") == "ap-south-1":
            return regional_sts
        return global_sts

    mock_boto3_client.side_effect = client_side_effect

    mock_session_instance = MagicMock()
    mock_session.return_value = mock_session_instance
    mock_session_sts = MagicMock()
    mock_session_instance.client.return_value = mock_session_sts
    mock_session_sts.get_caller_identity.return_value = {
        "Account": "123456789012",
        "Arn": "arn:aws:sts::123456789012:assumed-role/CloudGuardScannerRole/cloudguard-security-scan",
    }

    response = client.post(
        f"{settings.API_V1_STR}/aws/connect",
        json={"role_arn": VALID_ROLE_ARN, "region": "ap-south-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["account_id"] == "123456789012"
    assert data["region"] == "ap-south-1"

