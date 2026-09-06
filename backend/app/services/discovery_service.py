from fastapi import HTTPException
from app.services.aws_connection_service import aws_connection_service
from app.schemas.inventory import ResourceInventory
from app.discovery.s3_discovery import discover_s3_buckets
from app.discovery.ec2_discovery import discover_ec2_instances, discover_security_groups
from app.discovery.iam_discovery import discover_iam_users, discover_iam_roles
from app.discovery.rds_discovery import discover_rds_instances
from app.discovery.cloudtrail_discovery import discover_cloudtrails
from app.core.logging import logger

class DiscoveryService:
    def run_discovery(self) -> ResourceInventory:
        """
        Executes discovery modules using the established AWS connection to gather resource inventory.
        """
        factory = aws_connection_service.get_client_factory()
        if not factory:
            raise HTTPException(status_code=400, detail="No active AWS connection. Please connect first.")

        logger.info("Starting AWS resource discovery...")

        # Initialize clients
        s3_client = factory.create_client('s3')
        ec2_client = factory.create_client('ec2')
        iam_client = factory.create_client('iam')
        rds_client = factory.create_client('rds')
        cloudtrail_client = factory.create_client('cloudtrail')

        # Run discovery
        inventory = ResourceInventory(
            s3_buckets=discover_s3_buckets(s3_client),
            ec2_instances=discover_ec2_instances(ec2_client),
            security_groups=discover_security_groups(ec2_client),
            iam_users=discover_iam_users(iam_client),
            iam_roles=discover_iam_roles(iam_client),
            rds_instances=discover_rds_instances(rds_client),
            cloudtrails=discover_cloudtrails(cloudtrail_client)
        )
        
        logger.info(f"Discovery complete. Found {len(inventory.s3_buckets)} S3 buckets, "
                    f"{len(inventory.ec2_instances)} EC2 instances, "
                    f"{len(inventory.iam_users)} IAM users.")
                    
        return inventory

discovery_service = DiscoveryService()
