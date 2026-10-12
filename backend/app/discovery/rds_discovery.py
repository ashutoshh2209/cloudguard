from typing import List
from botocore.exceptions import ClientError
from app.schemas.inventory import RDSInstance
from app.schemas.resource import DiscoveredResourceData
from app.aws.connection import handle_boto3_errors
from app.core.logging import logger

@handle_boto3_errors
def discover_rds_instances(rds_client) -> List[RDSInstance]:
    """
    Discovers RDS database instances in the region (legacy Part 1 support).
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

def discover_rds_resources(
    rds_client,
    region: str = "us-east-1",
    account_id: str = ""
) -> List[DiscoveredResourceData]:
    """
    Discovers RDS database instances and returns normalized DiscoveredResourceData objects.
    Paginates through describe_db_instances.
    """
    resources = []
    try:
        paginator = rds_client.get_paginator('describe_db_instances')
        for page in paginator.paginate():
            for db in page.get("DBInstances", []):
                db_id = db["DBInstanceIdentifier"]
                status = db.get("DBInstanceStatus", "available")
                arn = db.get("DBInstanceArn", f"arn:aws:rds:{region}:{account_id}:db:{db_id}")

                metadata = {
                    "engine": db.get("Engine"),
                    "engine_version": db.get("EngineVersion"),
                    "instance_class": db.get("DBInstanceClass"),
                    "allocated_storage": db.get("AllocatedStorage"),
                    "multi_az": db.get("MultiAZ", False),
                    "publicly_accessible": db.get("PubliclyAccessible", False),
                    "storage_encrypted": db.get("StorageEncrypted", False),
                    "endpoint_address": db.get("Endpoint", {}).get("Address"),
                    "endpoint_port": db.get("Endpoint", {}).get("Port"),
                    "auto_minor_version_upgrade": db.get("AutoMinorVersionUpgrade", False),
                }

                resources.append(
                    DiscoveredResourceData(
                        service="rds",
                        resource_type="rds:db-instance",
                        resource_id=db_id,
                        resource_name=db_id,
                        region=region,
                        arn=arn,
                        status=status,
                        metadata=metadata,
                    )
                )
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        logger.warning(f"RDS discovery encountered AWS ClientError ({error_code}): {error_msg}")
        raise
    except Exception as e:
        logger.warning(f"Unexpected error discovering RDS instances: {e}")
        raise

    return resources
