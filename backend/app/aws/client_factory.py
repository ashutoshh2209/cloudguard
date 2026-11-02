import boto3
from typing import Optional

class AWSClientFactory:
    """
    Factory to create boto3 clients from temporary credentials.
    Future scanners (S3, EC2, IAM, etc.) will use this to get clients.
    """
    def __init__(self, credentials: dict, region: str):
        self._credentials = credentials
        self._region = region
        self._session: Optional[boto3.Session] = None

    @property
    def session(self) -> boto3.Session:
        if not self._session:
            self._session = boto3.Session(
                aws_access_key_id=self._credentials["AccessKeyId"],
                aws_secret_access_key=self._credentials["SecretAccessKey"],
                aws_session_token=self._credentials["SessionToken"],
                region_name=self._region
            )
        return self._session

    def create_client(self, service_name: str, region_name: Optional[str] = None):
        """
        Creates and returns a boto3 client for the specified service.
        Example: client_factory.create_client('s3')
        """
        target_region = region_name or ("us-east-1" if service_name in ("iam", "s3", "sts") else self._region)
        return self.session.client(service_name, region_name=target_region)

    def create_resource(self, service_name: str, region_name: Optional[str] = None):
        """
        Creates and returns a boto3 resource for the specified service.
        Example: client_factory.create_resource('s3')
        """
        return self.session.resource(service_name, region_name=region_name or self._region)

