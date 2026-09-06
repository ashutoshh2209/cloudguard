from fastapi import APIRouter
from app.schemas.inventory import ResourceInventory
from app.services.discovery_service import discovery_service

router = APIRouter()

@router.post("/run", response_model=ResourceInventory)
async def run_discovery():
    """
    Triggers AWS resource discovery.
    Requires an active AWS connection established via /api/v1/aws/connect.
    """
    return discovery_service.run_discovery()
