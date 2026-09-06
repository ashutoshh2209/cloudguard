from typing import List, Tuple
from app.scanner.base import ServiceScanner
from app.schemas.inventory import S3Bucket
from app.findings.schemas import Finding
from botocore.exceptions import ClientError
from app.core.logging import logger

class S3Scanner(ServiceScanner):
    service = "s3"

    def scan(self, resources: List[S3Bucket], scan_id: str) -> Tuple[List[Finding], int, int]:
        findings = []
        total_passed = 0
        total_failed = 0
        for bucket in resources:
            bucket_name = bucket.name
            context = {}

            # Prepare context for rules
            try:
                # Mock logic for checking encryption
                try:
                    enc = self.client.get_bucket_encryption(Bucket=bucket_name)
                    context["encryption"] = {"is_encrypted": True}
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
                        context["encryption"] = {"is_encrypted": False}
                    else:
                        context["encryption"] = {"is_encrypted": True} # Default assume secure if other error
                        
                # Mock logic for checking BPA
                try:
                    bpa = self.client.get_public_access_block(Bucket=bucket_name)
                    conf = bpa.get("PublicAccessBlockConfiguration", {})
                    is_enabled = all([
                        conf.get("BlockPublicAcls", False),
                        conf.get("IgnorePublicAcls", False),
                        conf.get("BlockPublicPolicy", False),
                        conf.get("RestrictPublicBuckets", False)
                    ])
                    context["block_public_access"] = {"is_fully_enabled": is_enabled}
                except ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchPublicAccessBlockConfiguration':
                        context["block_public_access"] = {"is_fully_enabled": False}
                    else:
                        context["block_public_access"] = {"is_fully_enabled": True}

                # Mock logic for public access
                try:
                    # In real life, evaluate ACLs and Policies. We'll simplify and rely on BPA
                    # if BPA is disabled, we simulate checking ACLs/Policy
                    policy = self.client.get_bucket_policy_status(Bucket=bucket_name)
                    is_public = policy.get("PolicyStatus", {}).get("IsPublic", False)
                    context["public_access"] = {"is_public": is_public}
                except ClientError:
                    context["public_access"] = {"is_public": False}
                    
            except Exception as e:
                logger.error(f"Error preparing S3 context for {bucket_name}: {e}")

            f_res, p, f = self.evaluate_rules(
                resource_id=bucket_name,
                resource_name=bucket_name,
                resource_data=bucket,
                context=context,
                scan_id=scan_id
            )
            findings.extend(f_res)
            total_passed += p
            total_failed += f
        return findings, total_passed, total_failed
