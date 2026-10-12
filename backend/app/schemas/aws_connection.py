import re
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict

IAM_ROLE_ARN_PATTERN = r"^arn:aws:iam::\d{12}:role/[\w+=,.@/-]+$"
AWS_REGION_PATTERN = r"^[a-z]{2}(?:-gov)?-[a-z]+-\d+$"

class AWSConnectionCreateRequest(BaseModel):
    workspace_id: str = Field(..., description="Target workspace ID to associate the connection with")
    role_arn: str = Field(..., description="The AWS IAM Role ARN to assume")
    region: Optional[str] = Field("us-east-1", description="Default AWS region (e.g. us-east-1)")
    external_id: Optional[str] = Field(None, description="Optional external ID for IAM role trust policy")

    @field_validator("role_arn")
    @classmethod
    def validate_role_arn(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("Role ARN is required")
        v = v.strip()
        if not re.match(IAM_ROLE_ARN_PATTERN, v):
            raise ValueError("Invalid AWS IAM Role ARN format. Must follow arn:aws:iam::<12-digit-account-id>:role/<role-name>")
        return v

    @field_validator("region")
    @classmethod
    def validate_region(cls, v: Optional[str]) -> str:
        if not v:
            return "us-east-1"
        v = v.strip().lower()
        if not re.match(AWS_REGION_PATTERN, v):
            raise ValueError(f"Invalid AWS region format: '{v}'")
        return v

    @field_validator("external_id")
    @classmethod
    def validate_external_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            return v if v else None
        return None

class AWSConnectionResponse(BaseModel):
    id: str
    workspace_id: Optional[str]
    account_id: str
    role_arn: str
    external_id: Optional[str] = None
    region: str
    status: str
    created_at: datetime
    updated_at: datetime
    last_verified_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AWSConnectionVerifyResponse(BaseModel):
    id: str
    workspace_id: Optional[str]
    account_id: str
    role_arn: str
    region: str
    status: str
    last_verified_at: datetime
    message: str = "AWS connection verified successfully"

class AWSConnectionDeleteResponse(BaseModel):
    id: str
    message: str = "AWS connection deleted successfully"
