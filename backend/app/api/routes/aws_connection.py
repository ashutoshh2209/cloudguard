from fastapi import APIRouter

from app.aws.schemas import ConnectRequest, ConnectResponse, StatusResponse, DisconnectResponse
from app.services.aws_connection_service import aws_connection_service

router = APIRouter()

@router.post("/connect", response_model=ConnectResponse)
async def connect_aws(request: ConnectRequest):
    """
    Validates an AWS IAM Role ARN, assumes the role via STS to obtain temporary credentials,
    and verifies the connection by fetching caller identity.
    Credentials are NEVER exposed in the response.
    """
    return aws_connection_service.connect(request)

@router.get("/status", response_model=StatusResponse)
async def get_connection_status():
    """
    Retrieves the current application-level AWS connection state.
    """
    return aws_connection_service.get_status()

@router.post("/disconnect", response_model=DisconnectResponse)
async def disconnect_aws():
    """
    Clears the temporary in-memory connection state and AWS credentials.
    """
    return aws_connection_service.disconnect()
