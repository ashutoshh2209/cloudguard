from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field

class DiscoveredResourceData(BaseModel):
    """
    Normalized representation of an AWS resource gathered during discovery.
    """
    service: str
    resource_type: str
    resource_id: str
    resource_name: Optional[str] = None
    region: str
    arn: Optional[str] = None
    status: str = "active"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)

class ResourceResponse(BaseModel):
    id: str
    workspace_id: Optional[str] = None
    aws_connection_id: Optional[str] = None
    scan_id: Optional[str] = None
    service: str
    resource_type: str
    resource_id: str
    resource_name: Optional[str] = None
    name: Optional[str] = None
    region: str
    arn: Optional[str] = None
    status: str = "active"
    metadata: Optional[Dict[str, Any]] = None
    details: Optional[Dict[str, Any]] = None
    discovered_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ResourceListResponse(BaseModel):
    items: List[ResourceResponse]
    total: int
    skip: int = 0
    limit: int = 50
    service_counts: Dict[str, int] = Field(default_factory=dict)

class DiscoveryRunRequest(BaseModel):
    workspace_id: Optional[str] = Field(None, description="Workspace ID to discover resources for")
    connection_id: Optional[str] = Field(None, description="Optional specific AWS connection ID in workspace")

class DiscoveryResultResponse(BaseModel):
    workspace_id: Optional[str] = None
    aws_connection_id: Optional[str] = None
    account_id: Optional[str] = None
    resources_count: int
    service_summary: Dict[str, int]
    service_errors: Dict[str, str] = Field(default_factory=dict)
    discovered_at: datetime
