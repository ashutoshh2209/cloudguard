import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional

ARN_REGEX = r"^arn:aws:iam::\d{12}:role/[\w+=,.@-]+$"

class ConnectRequest(BaseModel):
    role_arn: str = Field(..., description="The AWS IAM Role ARN to assume.")
    region: Optional[str] = Field(None, description="The AWS region to connect to.")

    @field_validator("role_arn")
    @classmethod
    def validate_role_arn(cls, v: str) -> str:
        if not re.match(ARN_REGEX, v):
            raise ValueError("Invalid AWS IAM Role ARN format.")
        return v

class ConnectResponse(BaseModel):
    connected: bool
    account_id: str
    region: str
    identity_arn: str
    message: str

class StatusResponse(BaseModel):
    connected: bool
    account_id: Optional[str] = None
    region: Optional[str] = None
    identity_arn: Optional[str] = None
    message: str

class DisconnectResponse(BaseModel):
    connected: bool
    message: str
