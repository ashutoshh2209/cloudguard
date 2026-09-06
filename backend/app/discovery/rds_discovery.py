from typing import List
from app.schemas.inventory import RDSInstance
from app.aws.connection import handle_boto3_errors

@handle_boto3_errors
def discover_rds_instances(rds_client) -> List[RDSInstance]:
    """
    Discovers RDS database instances in the region.
    """
    instances = []
    paginator = rds_client.get_paginator('describe_db_instances')
    for page in paginator.paginate():
        for db in page.get("DBInstances", []):
            instances.append(
                RDSInstance(
                    db_instance_identifier=db["DBInstanceIdentifier"],
                    engine=db["Engine"],
                    status=db["DBInstanceStatus"]
                )
            )
    return instances
