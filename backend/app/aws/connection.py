import re
import boto3
from botocore.credentials import Credentials, ReadOnlyCredentials
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
from app.core.logging import logger

_ACCESS_KEY_PATTERN = re.compile(r"^(AKIA|ASIA|ABIA|ACCA|AGPA|AIDA|AIPA|ANPA|ANVA|APKA|AROA|ASCA|AZIA)[A-Z0-9]{12,124}$")


def _clean_cred_value(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in ("'", '"'):
        cleaned = cleaned[1:-1].strip()
    return cleaned or None


def _validate_caller_credentials(access_key: str | None, secret_key: str | None) -> None:
    if not access_key or not secret_key:
        raise AWSAuthenticationError(
            "AWS caller credentials not found or incomplete in backend environment (~/.aws/credentials or environment variables)."
        )
    if any(c.isspace() for c in access_key) or any(c.isspace() for c in secret_key):
        raise AWSAuthenticationError(
            "AWS caller credentials in backend configuration are malformed (contain spaces or invalid characters). "
            "Please configure a valid IAM Access Key ID and Secret Access Key."
        )
    if not _ACCESS_KEY_PATTERN.match(access_key):
        raise AWSAuthenticationError(
            "AWS Access Key ID in backend configuration is malformed (expected an IAM access key starting with AKIA or ASIA)."
        )
    if len(secret_key) < 16 or secret_key.upper().startswith(("YOUR_", "REPLACE_", "EXAMPLE")):
        raise AWSAuthenticationError(
            "AWS Secret Access Key in backend configuration is malformed or set to a placeholder value."
        )


def _build_sts_client(region: str):
    cfg_ak = _clean_cred_value(getattr(settings, "AWS_ACCESS_KEY_ID", None))
    cfg_sk = _clean_cred_value(getattr(settings, "AWS_SECRET_ACCESS_KEY", None))
    cfg_st = _clean_cred_value(getattr(settings, "AWS_SESSION_TOKEN", None))

    if cfg_ak or cfg_sk:
        _validate_caller_credentials(cfg_ak, cfg_sk)
        client_kwargs = {
            "region_name": region,
            "aws_access_key_id": cfg_ak,
            "aws_secret_access_key": cfg_sk,
        }
        if cfg_st:
            client_kwargs["aws_session_token"] = cfg_st
        return boto3.client("sts", **client_kwargs)

    sts_client = boto3.client("sts", region_name=region)

    # If sts_client is a real botocore client (not a unittest MagicMock), validate resolved caller credentials
    signer = getattr(sts_client, "_request_signer", None)
    creds = getattr(signer, "_credentials", None)
    if isinstance(creds, (Credentials, ReadOnlyCredentials)):
        frozen = creds.get_frozen_credentials()
        raw_ak = frozen.access_key if frozen else None
        raw_sk = frozen.secret_key if frozen else None
        raw_st = frozen.token if frozen else None

        clean_ak = _clean_cred_value(raw_ak)
        clean_sk = _clean_cred_value(raw_sk)
        clean_st = _clean_cred_value(raw_st)

        _validate_caller_credentials(clean_ak, clean_sk)

        if clean_ak != raw_ak or clean_sk != raw_sk or clean_st != raw_st:
            rebuilt_kwargs = {
                "region_name": region,
                "aws_access_key_id": clean_ak,
                "aws_secret_access_key": clean_sk,
            }
            if clean_st:
                rebuilt_kwargs["aws_session_token"] = clean_st
            return boto3.client("sts", **rebuilt_kwargs)

    return sts_client


def handle_boto3_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            if error_code in ("AccessDenied", "AccessDeniedException", "UnauthorizedOperation"):
                if "service_control_policy" in error_msg.lower():
                    raise AWSAccessDeniedError(
                        "CloudGuard is not authorized to assume this AWS IAM role in the requested region due to an AWS Organizations Service Control Policy (SCP)."
                    )
                raise AWSAccessDeniedError("CloudGuard is not authorized to assume this AWS IAM role")
            elif error_code in ("InvalidParameterValue", "ValidationError"):
                raise InvalidRoleArnError(f"Invalid AWS parameter: {error_msg}")
            elif error_code in ("MalformedPolicyDocument", "InvalidIdentityToken"):
                raise AWSInvalidConfigurationError(f"Invalid AWS role configuration or trust policy: {error_msg}")
            elif error_code in (
                "InvalidClientTokenId",
                "UnrecognizedClientException",
                "ExpiredToken",
                "ExpiredTokenException",
                "IncompleteSignature",
                "IncompleteSignatureException",
                "SignatureDoesNotMatch",
                "MissingAuthenticationToken",
            ):
                raise AWSAuthenticationError(
                    "AWS credentials are invalid, expired, or malformed. Verify the backend caller's AWS Access Key ID and Secret Access Key."
                )
            elif error_code in ("RequestTimeTooSkewed", "AuthFailure"):
                raise AWSAuthenticationError(
                    "AWS rejected the request signature due to clock skew or invalid credentials."
                )
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
    Assumes the specified IAM role via AWS STS using SigV4 and returns temporary credentials.
    Falls back to the global STS control-plane region (us-east-1) if an AWS Organizations SCP
    restricts regional STS endpoints in the requested region.
    """
    clean_role_arn = role_arn.strip()
    clean_region = (region or settings.AWS_DEFAULT_REGION).strip()
    sts_client = _build_sts_client(clean_region)

    assume_role_kwargs = {
        "RoleArn": clean_role_arn,
        "RoleSessionName": settings.AWS_ROLE_SESSION_NAME,
    }

    ext_id = _clean_cred_value(external_id) or _clean_cred_value(settings.CLOUDGUARD_EXTERNAL_ID)
    if ext_id:
        assume_role_kwargs["ExternalId"] = ext_id

    try:
        response = sts_client.assume_role(**assume_role_kwargs)
    except ClientError as e:
        err_code = e.response.get("Error", {}).get("Code", "")
        err_msg = e.response.get("Error", {}).get("Message", "")
        if (
            err_code in ("AccessDenied", "AccessDeniedException")
            and "service_control_policy" in err_msg.lower()
            and clean_region != "us-east-1"
        ):
            logger.info(
                f"Regional STS endpoint in {clean_region} restricted by Organization SCP; "
                "falling back to global STS control-plane endpoint (us-east-1)."
            )
            global_sts_client = _build_sts_client("us-east-1")
            response = global_sts_client.assume_role(**assume_role_kwargs)
        else:
            raise

    return response["Credentials"]


@handle_boto3_errors
def verify_identity(credentials: dict, region: str) -> dict:
    """
    Verifies the identity of the provided temporary credentials via STS GetCallerIdentity.
    Falls back to us-east-1 if an AWS Organizations SCP restricts the regional STS endpoint.
    """
    clean_region = (region or settings.AWS_DEFAULT_REGION).strip()
    session = boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
        region_name=clean_region,
    )

    sts_client = session.client("sts")
    try:
        response = sts_client.get_caller_identity()
    except ClientError as e:
        err_code = e.response.get("Error", {}).get("Code", "")
        err_msg = e.response.get("Error", {}).get("Message", "")
        if (
            err_code in ("AccessDenied", "AccessDeniedException")
            and "service_control_policy" in err_msg.lower()
            and clean_region != "us-east-1"
        ):
            global_sts_client = session.client("sts", region_name="us-east-1")
            response = global_sts_client.get_caller_identity()
        else:
            raise

    return {
        "account_id": response.get("Account"),
        "identity_arn": response.get("Arn"),
    }
