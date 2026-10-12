from typing import List
from botocore.exceptions import ClientError
from app.schemas.inventory import S3Bucket
from app.schemas.resource import DiscoveredResourceData
from app.aws.connection import handle_boto3_errors
from app.core.logging import logger

@handle_boto3_errors
def discover_s3_buckets(s3_client) -> List[S3Bucket]:
    """
    Discovers S3 buckets globally (legacy Part 1 support).
    """
    response = s3_client.list_buckets()
    buckets = []
    for bucket in response.get("Buckets", []):
        buckets.append(
            S3Bucket(
                name=bucket["Name"],
                creation_date=str(bucket["CreationDate"]) if "CreationDate" in bucket else None
            )
        )
    return buckets

def discover_s3_resources(
    s3_client,
    account_id: str = "",
    default_region: str = "us-east-1"
) -> List[DiscoveredResourceData]:
    """
    Discovers S3 buckets and returns normalized DiscoveredResourceData objects.
    """
    resources = []
    try:
        response = s3_client.list_buckets()
        for bucket in response.get("Buckets", []):
            bucket_name = bucket["Name"]
            creation_date = str(bucket["CreationDate"]) if "CreationDate" in bucket else None
            
            # Bucket region
            bucket_region = default_region
            try:
                loc_resp = s3_client.get_bucket_location(Bucket=bucket_name)
                loc = loc_resp.get("LocationConstraint")
                if loc:
                    bucket_region = loc
                elif loc is None:
                    bucket_region = "us-east-1"
            except Exception:
                # If GetBucketLocation is denied or fails, fallback to default region
                bucket_region = default_region

            resources.append(
                DiscoveredResourceData(
                    service="s3",
                    resource_type="s3:bucket",
                    resource_id=bucket_name,
                    resource_name=bucket_name,
                    region=bucket_region,
                    arn=f"arn:aws:s3:::{bucket_name}",
                    status="active",
                    metadata={
                        "creation_date": creation_date,
                    }
                )
            )
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        logger.warning(f"S3 discovery encountered AWS ClientError ({error_code}): {error_msg}")
        raise
    except Exception as e:
        logger.warning(f"Unexpected error discovering S3 buckets: {e}")
        raise

    return resources
