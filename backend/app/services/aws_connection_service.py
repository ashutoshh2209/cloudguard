from typing import Optional

from app.aws.schemas import ConnectRequest, ConnectResponse, StatusResponse, DisconnectResponse
from app.aws.connection import assume_role, verify_identity
from app.aws.client_factory import AWSClientFactory
from app.core.config import settings
from app.core.logging import logger

class AWSConnectionService:
    """
    Manages AWS connection state and orchestrates role assumption/verification.
    For Part 2, state is kept in-memory to prove the flow works securely.
    """
    
    def __init__(self):
        self._current_credentials: Optional[dict] = None
        self._client_factory: Optional[AWSClientFactory] = None
        
        # Safe connection metadata
        self._account_id: Optional[str] = None
        self._identity_arn: Optional[str] = None
        self._region: Optional[str] = None
        self._is_connected: bool = False

    def connect(self, request: ConnectRequest) -> ConnectResponse:
        region = request.region or settings.AWS_DEFAULT_REGION
        
        logger.info(f"Attempting to connect to AWS Role: {request.role_arn} in region {region}")
        
        # 1. Assume Role to get temporary credentials
        credentials = assume_role(request.role_arn, region)
        
        # 2. Store credentials internally (DO NOT EXPOSE)
        self._current_credentials = credentials
        
        # 3. Initialize the client factory for future use
        self._client_factory = AWSClientFactory(credentials, region)
        
        # 4. Verify Identity
        identity = verify_identity(credentials, region)
        
        # 5. Store safe connection state
        self._account_id = identity["account_id"]
        self._identity_arn = identity["identity_arn"]
        self._region = region
        self._is_connected = True
        
        logger.info(f"Successfully connected to AWS Account: {self._account_id}")
        
        return ConnectResponse(
            connected=True,
            account_id=self._account_id,
            region=self._region,
            identity_arn=self._identity_arn,
            message="AWS account connected successfully"
        )
        
    def get_status(self) -> StatusResponse:
        """Returns the current application-level connection state."""
        if not self._is_connected:
            return StatusResponse(
                connected=False,
                message="No active AWS connection"
            )
            
        return StatusResponse(
            connected=True,
            account_id=self._account_id,
            region=self._region,
            identity_arn=self._identity_arn,
            message="AWS account is connected"
        )
        
    def disconnect(self) -> DisconnectResponse:
        """Clears the in-memory temporary credentials and connection state."""
        self._current_credentials = None
        self._client_factory = None
        self._account_id = None
        self._identity_arn = None
        self._region = None
        self._is_connected = False
        
        logger.info("AWS connection cleared")
        
        return DisconnectResponse(
            connected=False,
            message="AWS connection cleared"
        )
        
    def get_client_factory(self) -> Optional[AWSClientFactory]:
        """Exposes the factory for future scanners."""
        return self._client_factory

# Global singleton instance for Part 2 in-memory tracking
aws_connection_service = AWSConnectionService()
