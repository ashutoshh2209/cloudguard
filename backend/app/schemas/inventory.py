from typing import List, Optional
from pydantic import BaseModel

class S3Bucket(BaseModel):
    name: str
    creation_date: Optional[str]

class EC2Instance(BaseModel):
    instance_id: str
    instance_type: str
    state: str
    public_ip: Optional[str]

class SecurityGroup(BaseModel):
    group_id: str
    group_name: str
    description: str

class IAMUser(BaseModel):
    user_name: str
    arn: str
    create_date: Optional[str]

class IAMRole(BaseModel):
    role_name: str
    arn: str

class RDSInstance(BaseModel):
    db_instance_identifier: str
    engine: str
    status: str

class CloudTrail(BaseModel):
    name: str
    home_region: str
    s3_bucket_name: Optional[str]

class ResourceInventory(BaseModel):
    s3_buckets: List[S3Bucket]
    ec2_instances: List[EC2Instance]
    security_groups: List[SecurityGroup]
    iam_users: List[IAMUser]
    iam_roles: List[IAMRole]
    rds_instances: List[RDSInstance]
    cloudtrails: List[CloudTrail]
