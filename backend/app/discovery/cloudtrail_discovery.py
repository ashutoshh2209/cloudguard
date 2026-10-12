from typing import List
from botocore.exceptions import ClientError
from app.schemas.inventory import CloudTrail
from app.schemas.resource import DiscoveredResourceData
from app.aws.connection import handle_boto3_errors
from app.core.logging import logger

@handle_boto3_errors
def discover_cloudtrails(cloudtrail_client) -> List[CloudTrail]:
    """
    Discovers CloudTrail trails in the region (legacy Part 1 support).
    """
    trails = []
    response = cloudtrail_client.describe_trails()
    for trail in response.get("trailList", []):
        trails.append(
            CloudTrail(
                name=trail["Name"],
                home_region=trail.get("HomeRegion", ""),
                s3_bucket_name=trail.get("S3BucketName")
            )
        )
    return trails

def discover_cloudtrail_resources(
    cloudtrail_client,
    region: str = "us-east-1",
    account_id: str = ""
) -> List[DiscoveredResourceData]:
    """
    Discovers CloudTrail trails and returns normalized DiscoveredResourceData objects.
    """
    resources = []
    try:
        response = cloudtrail_client.describe_trails()
        for trail in response.get("trailList", []):
            trail_name = trail["Name"]
            home_region = trail.get("HomeRegion", region)
            arn = trail.get("TrailARN", f"arn:aws:cloudtrail:{home_region}:{account_id}:trail/{trail_name}")

            metadata = {
                "home_region": home_region,
                "is_multi_region": trail.get("IsMultiRegionTrail", False),
                "s3_bucket_name": trail.get("S3BucketName"),
                "log_file_validation_enabled": trail.get("LogFileValidationEnabled", False),
                "include_global_service_events": trail.get("IncludeGlobalServiceEvents", False),
                "is_organization_trail": trail.get("IsOrganizationTrail", False),
                "kms_key_id": trail.get("KmsKeyId"),
            }

            resources.append(
                DiscoveredResourceData(
                    service="cloudtrail",
                    resource_type="cloudtrail:trail",
                    resource_id=trail_name,
                    resource_name=trail_name,
                    region=home_region,
                    arn=arn,
                    status="active",
                    metadata=metadata,
                )
            )
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        logger.warning(f"CloudTrail discovery encountered AWS ClientError ({error_code}): {error_msg}")
        raise
    except Exception as e:
        logger.warning(f"Unexpected error discovering CloudTrail trails: {e}")
        raise

    return resources
