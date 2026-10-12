from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.workspace import Workspace
from app.models.aws_connection import AWSConnection
from app.models.resource import CloudResource
from app.schemas.inventory import ResourceInventory
from app.schemas.resource import (
    DiscoveredResourceData,
    DiscoveryResultResponse,
)
from app.services.aws_connection_service import aws_connection_service
from app.aws.sts_service import aws_sts_service
from app.aws.client_factory import AWSClientFactory

from app.discovery.s3_discovery import discover_s3_buckets, discover_s3_resources
from app.discovery.ec2_discovery import (
    discover_ec2_instances,
    discover_security_groups,
    discover_ec2_resources,
    discover_security_group_resources,
)
from app.discovery.iam_discovery import (
    discover_iam_users,
    discover_iam_roles,
    discover_iam_resources,
)
from app.discovery.rds_discovery import discover_rds_instances, discover_rds_resources
from app.discovery.cloudtrail_discovery import (
    discover_cloudtrails,
    discover_cloudtrail_resources,
)

class DiscoveryService:
    """
    Orchestrates AWS resource discovery across EC2, S3, IAM, Security Groups, RDS, and CloudTrail.
    Normalizes resource inventory, gracefully isolates per-service failures, and persists
    discovered assets into the database scoped by workspace.
    """

    def run_discovery(self) -> ResourceInventory:
        """
        Executes legacy discovery modules using the established active connection (Part 1 compatibility).
        """
        factory = aws_connection_service.get_client_factory()
        if not factory:
            raise HTTPException(status_code=400, detail="No active AWS connection. Please connect first.")

        logger.info("Starting legacy AWS resource discovery...")

        s3_client = factory.create_client('s3')
        ec2_client = factory.create_client('ec2')
        iam_client = factory.create_client('iam')
        rds_client = factory.create_client('rds')
        cloudtrail_client = factory.create_client('cloudtrail')

        inventory = ResourceInventory(
            s3_buckets=discover_s3_buckets(s3_client),
            ec2_instances=discover_ec2_instances(ec2_client),
            security_groups=discover_security_groups(ec2_client),
            iam_users=discover_iam_users(iam_client),
            iam_roles=discover_iam_roles(iam_client),
            rds_instances=discover_rds_instances(rds_client),
            cloudtrails=discover_cloudtrails(cloudtrail_client)
        )
        
        logger.info(f"Legacy discovery complete. Found {len(inventory.s3_buckets)} S3 buckets, "
                    f"{len(inventory.ec2_instances)} EC2 instances.")
        return inventory

    def discover_workspace_resources(
        self,
        db: Session,
        workspace_id: str,
        connection_id: Optional[str] = None,
    ) -> DiscoveryResultResponse:
        """
        Runs full multi-service resource discovery for a workspace using its connected AWS account.
        Discovers EC2, S3, IAM, Security Groups, RDS, and CloudTrail resources without mutating AWS.
        Normalizes resource structures and persists them to the PostgreSQL / SQLite database.
        """
        # 1. Resolve workspace and connection
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        connection_query = db.query(AWSConnection).filter(AWSConnection.workspace_id == workspace_id)
        if connection_id:
            connection = connection_query.filter(AWSConnection.id == connection_id).first()
        else:
            connection = connection_query.order_by(AWSConnection.created_at.desc()).first()

        if not connection:
            raise HTTPException(
                status_code=400,
                detail="No AWS connection found for this workspace. Please connect an AWS account first."
            )

        logger.info(f"Starting workspace resource discovery for workspace {workspace_id} (Connection: {connection.id}, Account: {connection.account_id})")

        # 2. Obtain client factory from memory, or re-assume role via STS if needed
        factory = aws_connection_service.get_client_factory_for_connection(connection.id)
        if not factory:
            # Re-assume role via STS to obtain fresh temporary credentials
            credentials = aws_sts_service.assume_role(
                role_arn=connection.role_arn,
                region=connection.region,
                external_id=connection.external_id,
            )
            factory = AWSClientFactory(credentials, connection.region)
            aws_connection_service._credentials_store[connection.id] = credentials
            aws_connection_service._factories[connection.id] = factory

        # 3. Instantiate service clients
        s3_client = factory.create_client('s3')
        ec2_client = factory.create_client('ec2', region_name=connection.region)
        iam_client = factory.create_client('iam')
        rds_client = factory.create_client('rds', region_name=connection.region)
        cloudtrail_client = factory.create_client('cloudtrail', region_name=connection.region)

        all_discovered: List[DiscoveredResourceData] = []
        service_summary: Dict[str, int] = {
            "s3": 0,
            "ec2": 0,
            "security_group": 0,
            "iam": 0,
            "rds": 0,
            "cloudtrail": 0,
        }
        service_errors: Dict[str, str] = {}

        # 4. Service Discovery with graceful per-service error isolation

        # S3 Discovery
        try:
            s3_res = discover_s3_resources(s3_client, account_id=connection.account_id, default_region=connection.region)
            all_discovered.extend(s3_res)
            service_summary["s3"] = len(s3_res)
        except Exception as e:
            logger.warning(f"S3 discovery failed gracefully: {e}")
            service_errors["s3"] = str(e)

        # EC2 Instances Discovery
        try:
            ec2_res = discover_ec2_resources(ec2_client, region=connection.region, account_id=connection.account_id)
            all_discovered.extend(ec2_res)
            service_summary["ec2"] = len(ec2_res)
        except Exception as e:
            logger.warning(f"EC2 discovery failed gracefully: {e}")
            service_errors["ec2"] = str(e)

        # Security Groups Discovery
        try:
            sg_res = discover_security_group_resources(ec2_client, region=connection.region, account_id=connection.account_id)
            all_discovered.extend(sg_res)
            service_summary["security_group"] = len(sg_res)
        except Exception as e:
            logger.warning(f"Security Group discovery failed gracefully: {e}")
            service_errors["security_group"] = str(e)

        # IAM Users & Roles Discovery
        try:
            iam_res = discover_iam_resources(iam_client, account_id=connection.account_id)
            all_discovered.extend(iam_res)
            service_summary["iam"] = len(iam_res)
        except Exception as e:
            logger.warning(f"IAM discovery failed gracefully: {e}")
            service_errors["iam"] = str(e)

        # RDS Database Instances Discovery
        try:
            rds_res = discover_rds_resources(rds_client, region=connection.region, account_id=connection.account_id)
            all_discovered.extend(rds_res)
            service_summary["rds"] = len(rds_res)
        except Exception as e:
            logger.warning(f"RDS discovery failed gracefully: {e}")
            service_errors["rds"] = str(e)

        # CloudTrail Trails Discovery
        try:
            ct_res = discover_cloudtrail_resources(cloudtrail_client, region=connection.region, account_id=connection.account_id)
            all_discovered.extend(ct_res)
            service_summary["cloudtrail"] = len(ct_res)
        except Exception as e:
            logger.warning(f"CloudTrail discovery failed gracefully: {e}")
            service_errors["cloudtrail"] = str(e)

        # 5. Persist normalized resources into database
        now = datetime.now(timezone.utc)
        for r_data in all_discovered:
            existing = (
                db.query(CloudResource)
                .filter(
                    CloudResource.workspace_id == workspace_id,
                    CloudResource.aws_connection_id == connection.id,
                    CloudResource.service == r_data.service,
                    CloudResource.resource_id == r_data.resource_id,
                )
                .first()
            )

            if existing:
                existing.resource_name = r_data.resource_name
                existing.name = r_data.resource_name
                existing.arn = r_data.arn
                existing.region = r_data.region
                existing.status = r_data.status
                existing.metadata_json = r_data.metadata
                existing.updated_at = now
            else:
                db_resource = CloudResource(
                    workspace_id=workspace_id,
                    aws_connection_id=connection.id,
                    service=r_data.service,
                    resource_type=r_data.resource_type,
                    resource_id=r_data.resource_id,
                    resource_name=r_data.resource_name,
                    name=r_data.resource_name,
                    region=r_data.region,
                    arn=r_data.arn,
                    status=r_data.status,
                    metadata_json=r_data.metadata,
                    discovered_at=now,
                    updated_at=now,
                )
                db.add(db_resource)

        db.commit()

        logger.info(
            f"Resource discovery complete for workspace {workspace_id}. "
            f"Total assets saved: {len(all_discovered)}. Service summary: {service_summary}"
        )

        return DiscoveryResultResponse(
            workspace_id=workspace_id,
            aws_connection_id=connection.id,
            account_id=connection.account_id,
            resources_count=len(all_discovered),
            service_summary=service_summary,
            service_errors=service_errors,
            discovered_at=now,
        )

discovery_service = DiscoveryService()
