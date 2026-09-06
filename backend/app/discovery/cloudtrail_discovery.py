from typing import List
from app.schemas.inventory import CloudTrail
from app.aws.connection import handle_boto3_errors

@handle_boto3_errors
def discover_cloudtrails(cloudtrail_client) -> List[CloudTrail]:
    """
    Discovers CloudTrail trails in the region.
    """
    trails = []
    # describe_trails does not have a paginator in boto3 by default, and typically returns a small list.
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
