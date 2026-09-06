from typing import List
from app.schemas.inventory import S3Bucket
from app.aws.connection import handle_boto3_errors

@handle_boto3_errors
def discover_s3_buckets(s3_client) -> List[S3Bucket]:
    """
    Discovers S3 buckets globally.
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
