from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.aws.schemas import ConnectRequest, ConnectResponse, StatusResponse, DisconnectResponse
from app.aws.sts_service import aws_sts_service
from app.aws.client_factory import AWSClientFactory
from app.models.aws_connection import AWSConnection
from app.core.config import settings
from app.core.logging import logger

class AWSConnectionService:
    """
    Manages AWS connection lifecycle, STS role assumption, verification,
    and in-memory temporary credentials storage.
    
    Security: Temporary credentials (AccessKeyId, SecretAccessKey, SessionToken)
    exist ONLY in backend memory for active sessions and are NEVER persisted
    in the database, exposed via API endpoints, or logged.
    """

    def __init__(self):
        # In-memory storage for multi-connection temporary credentials
        self._credentials_store: Dict[str, dict] = {}
        self._factories: Dict[str, AWSClientFactory] = {}

        # Backward compatibility for legacy single-connection flows
        self._current_credentials: Optional[dict] = None
        self._client_factory: Optional[AWSClientFactory] = None
        self._account_id: Optional[str] = None
        self._identity_arn: Optional[str] = None
        self._region: Optional[str] = None
        self._is_connected: bool = False

    def create_connection(
        self,
        db: Session,
        workspace_id: str,
        role_arn: str,
        region: str,
        external_id: Optional[str] = None,
    ) -> AWSConnection:
        """
        Assumes the specified IAM role via STS, verifies identity,
        saves the connection record in the database, and stores credentials in memory.
        """
        logger.info(f"Creating AWS connection for workspace {workspace_id} using role {role_arn} in region {region}")

        # 1. Assume Role and verify caller identity
        result = aws_sts_service.verify_role(
            role_arn=role_arn,
            region=region,
            external_id=external_id,
        )

        credentials = result["credentials"]
        identity = result["identity"]
        account_id = result["account_id"]

        now = datetime.now(timezone.utc)

        # 2. Check if a connection with the same role ARN already exists in this workspace
        connection = (
            db.query(AWSConnection)
            .filter(
                AWSConnection.workspace_id == workspace_id,
                AWSConnection.role_arn == role_arn,
            )
            .first()
        )

        if connection:
            connection.region = region
            connection.external_id = external_id
            connection.account_id = account_id
            connection.status = "CONNECTED"
            connection.last_verified_at = now
            connection.updated_at = now
        else:
            connection = AWSConnection(
                workspace_id=workspace_id,
                account_id=account_id,
                role_arn=role_arn,
                external_id=external_id,
                region=region,
                status="CONNECTED",
                created_at=now,
                updated_at=now,
                last_verified_at=now,
            )
            db.add(connection)

        db.commit()
        db.refresh(connection)

        # 3. Store temporary credentials safely in memory (NEVER IN DB)
        self._credentials_store[connection.id] = credentials
        self._factories[connection.id] = AWSClientFactory(credentials, region)

        # 4. Synchronize legacy singleton state for backward compatibility
        self._current_credentials = credentials
        self._client_factory = self._factories[connection.id]
        self._account_id = account_id
        self._identity_arn = identity.get("identity_arn")
        self._region = region
        self._is_connected = True

        logger.info(f"AWS connection {connection.id} established for account {account_id}")
        return connection

    def verify_connection(self, db: Session, connection: AWSConnection) -> AWSConnection:
        """
        Re-verifies an existing connection using STS AssumeRole + GetCallerIdentity.
        Updates status and last_verified_at timestamp.
        """
        logger.info(f"Re-verifying AWS connection {connection.id} ({connection.role_arn})")
        now = datetime.now(timezone.utc)

        try:
            result = aws_sts_service.verify_role(
                role_arn=connection.role_arn,
                region=connection.region,
                external_id=connection.external_id,
            )
            credentials = result["credentials"]

            connection.status = "CONNECTED"
            connection.last_verified_at = now
            connection.updated_at = now
            db.commit()
            db.refresh(connection)

            # Update in-memory credentials
            self._credentials_store[connection.id] = credentials
            self._factories[connection.id] = AWSClientFactory(credentials, connection.region)

            # Update legacy state
            self._current_credentials = credentials
            self._client_factory = self._factories[connection.id]
            self._is_connected = True

            logger.info(f"AWS connection {connection.id} successfully re-verified")
            return connection
        except Exception:
            connection.status = "ERROR"
            connection.updated_at = now
            db.commit()
            db.refresh(connection)
            raise

    def delete_connection(self, db: Session, connection: AWSConnection) -> None:
        """
        Removes an AWS connection from database and purges in-memory credentials.
        """
        conn_id = connection.id
        logger.info(f"Deleting AWS connection {conn_id}")

        self._credentials_store.pop(conn_id, None)
        self._factories.pop(conn_id, None)

        if self._account_id == connection.account_id:
            self._current_credentials = None
            self._client_factory = None
            self._account_id = None
            self._identity_arn = None
            self._region = None
            self._is_connected = False

        db.delete(connection)
        db.commit()
        logger.info(f"AWS connection {conn_id} deleted")

    def get_credentials(self, connection_id: str) -> Optional[dict]:
        """Returns in-memory temporary credentials for an active connection."""
        return self._credentials_store.get(connection_id)

    def get_client_factory_for_connection(self, connection_id: str) -> Optional[AWSClientFactory]:
        """Returns AWSClientFactory for a specific connection."""
        return self._factories.get(connection_id)

    # -------------------------------------------------------------------------
    # Backward Compatibility for Part 1 & 2 Legacy Endpoints
    # -------------------------------------------------------------------------

    def connect(self, request: ConnectRequest) -> ConnectResponse:
        region = request.region or settings.AWS_DEFAULT_REGION
        logger.info(f"Attempting legacy connection to AWS Role: {request.role_arn} in region {region}")

        result = aws_sts_service.verify_role(role_arn=request.role_arn, region=region)
        credentials = result["credentials"]
        identity = result["identity"]

        self._current_credentials = credentials
        self._client_factory = AWSClientFactory(credentials, region)
        self._account_id = identity["account_id"]
        self._identity_arn = identity["identity_arn"]
        self._region = region
        self._is_connected = True

        return ConnectResponse(
            connected=True,
            account_id=self._account_id,
            region=self._region,
            identity_arn=self._identity_arn,
            message="AWS account connected successfully",
        )

    def get_status(self) -> StatusResponse:
        if not self._is_connected:
            return StatusResponse(
                connected=False,
                message="No active AWS connection",
            )
        return StatusResponse(
            connected=True,
            account_id=self._account_id,
            region=self._region,
            identity_arn=self._identity_arn,
            message="AWS account is connected",
        )

    def disconnect(self) -> DisconnectResponse:
        self._current_credentials = None
        self._client_factory = None
        self._account_id = None
        self._identity_arn = None
        self._region = None
        self._is_connected = False
        self._credentials_store.clear()
        self._factories.clear()

        return DisconnectResponse(
            connected=False,
            message="AWS connection cleared",
        )

    def get_client_factory(self) -> Optional[AWSClientFactory]:
        return self._client_factory

# Global singleton instance
aws_connection_service = AWSConnectionService()
