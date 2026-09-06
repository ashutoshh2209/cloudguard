class CloudGuardAWSError(Exception):
    """Base exception for all AWS-related errors in CloudGuard."""
    pass

class InvalidRoleArnError(CloudGuardAWSError):
    """Raised when the provided Role ARN is malformed."""
    pass

class AWSAuthenticationError(CloudGuardAWSError):
    """Raised when authentication with AWS fails."""
    pass

class AWSAccessDeniedError(CloudGuardAWSError):
    """Raised when access is denied for an AWS operation."""
    pass

class AWSConnectionError(CloudGuardAWSError):
    """Raised when there is a network or endpoint connectivity issue."""
    pass

class AWSRegionError(CloudGuardAWSError):
    """Raised when an invalid region is provided."""
    pass
