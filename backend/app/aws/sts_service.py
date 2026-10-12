from typing import Optional, Dict, Any
from app.aws.connection import assume_role, verify_identity
from app.aws.exceptions import AWSInvalidConfigurationError
from app.core.logging import logger

class AWSSTSService:
    """
    Service responsible for interacting with AWS STS (Security Token Service).
    Handles IAM role assumption and caller identity verification.
    """

    def assume_role(
        self,
        role_arn: str,
        region: str,
        external_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Assumes the specified IAM role via STS and retrieves temporary credentials.
        """
        return assume_role(role_arn=role_arn, region=region, external_id=external_id)

    def get_caller_identity(
        self,
        credentials: Dict[str, Any],
        region: str,
    ) -> Dict[str, Any]:
        """
        Verifies and retrieves identity information using temporary credentials.
        """
        return verify_identity(credentials=credentials, region=region)

    def verify_role(
        self,
        role_arn: str,
        region: str,
        external_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full verification workflow:
        1. Assume role via STS.
        2. Call GetCallerIdentity.
        3. Validate Account ID against the Role ARN.
        4. Return temporary credentials and verified identity metadata.
        """
        credentials = self.assume_role(role_arn=role_arn, region=region, external_id=external_id)
        identity = self.get_caller_identity(credentials=credentials, region=region)
        
        # Verify account ID
        arn_parts = role_arn.split(":")
        if len(arn_parts) >= 5:
            expected_account_id = arn_parts[4]
            actual_account_id = identity.get("account_id")
            if expected_account_id and actual_account_id and expected_account_id != actual_account_id:
                raise AWSInvalidConfigurationError(
                    f"Account ID mismatch: Role ARN specifies {expected_account_id} but STS returned {actual_account_id}"
                )

        logger.info(f"STS verification succeeded for account: {identity.get('account_id')}")
        return {
            "credentials": credentials,
            "identity": identity,
            "account_id": identity.get("account_id"),
            "identity_arn": identity.get("identity_arn"),
        }

# Global reusable STS service instance
aws_sts_service = AWSSTSService()
