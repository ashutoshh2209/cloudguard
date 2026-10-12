import boto3
from botocore.exceptions import ClientError, EndpointConnectionError, NoCredentialsError, PartialCredentialsError

from app.aws.exceptions import (
    AWSAuthenticationError,
    AWSAccessDeniedError,
    AWSConnectionError,
    AWSRegionError,
    AWSThrottlingError,
    AWSInvalidConfigurationError,
    InvalidRoleArnError
)
from app.core.config import settings

def handle_boto3_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            if error_code in ("AccessDenied", "UnauthorizedOperation"):
                raise AWSAccessDeniedError("CloudGuard is not authorized to assume this AWS IAM role")
            elif error_code in ("InvalidParameterValue", "ValidationError"):
                raise InvalidRoleArnError(f"Invalid AWS parameter: {error_msg}")
            elif error_code in ("MalformedPolicyDocument", "InvalidIdentityToken"):
                raise AWSInvalidConfigurationError(f"Invalid AWS role configuration or trust policy: {error_msg}")
            elif error_code in ("InvalidClientTokenId", "ExpiredToken"):
                raise AWSAuthenticationError("AWS credentials are invalid or expired")
            elif error_code in ("Throttling", "ThrottlingException", "RequestLimitExceeded", "RequestThrottled"):
                raise AWSThrottlingError(f"AWS STS request throttled: {error_msg}")
            else:
                raise AWSConnectionError(f"AWS ClientError: {error_code}")
        except (NoCredentialsError, PartialCredentialsError):
            raise AWSAuthenticationError("AWS credentials not found or incomplete in backend environment")
        except EndpointConnectionError:
            raise AWSConnectionError("Unable to connect to AWS at this time (network/endpoint error)")
        except ValueError as e:
            if "Invalid endpoint" in str(e) or "region" in str(e).lower():
                raise AWSRegionError("Invalid AWS region provided")
            raise AWSConnectionError(str(e))
        except (AWSAccessDeniedError, AWSAuthenticationError, AWSRegionError, AWSThrottlingError, AWSInvalidConfigurationError, InvalidRoleArnError, AWSConnectionError):
            raise
        except Exception as e:
            raise AWSConnectionError(f"Unexpected AWS error: {str(e)}")
    return wrapper

@handle_boto3_errors
def assume_role(role_arn: str, region: str, external_id: str | None = None) -> dict:
    """
    Assumes the specified IAM role and returns temporary credentials.
    """
    sts_client = boto3.client("sts", region_name=region)
    
    assume_role_kwargs = {
        "RoleArn": role_arn,
        "RoleSessionName": settings.AWS_ROLE_SESSION_NAME,
    }
    
    ext_id = external_id or settings.CLOUDGUARD_EXTERNAL_ID
    if ext_id:
        assume_role_kwargs["ExternalId"] = ext_id
        
    response = sts_client.assume_role(**assume_role_kwargs)
    return response["Credentials"]

@handle_boto3_errors
def verify_identity(credentials: dict, region: str) -> dict:
    """
    Verifies the identity of the provided temporary credentials.
    """
    session = boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
        region_name=region
    )
    
    sts_client = session.client("sts")
    response = sts_client.get_caller_identity()
    return {
        "account_id": response.get("Account"),
        "identity_arn": response.get("Arn"),
    }
