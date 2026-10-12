from typing import List, Tuple
from botocore.exceptions import ClientError
from app.schemas.inventory import EC2Instance, SecurityGroup
from app.schemas.resource import DiscoveredResourceData
from app.aws.connection import handle_boto3_errors
from app.core.logging import logger

@handle_boto3_errors
def discover_ec2_instances(ec2_client) -> List[EC2Instance]:
    """
    Discovers EC2 instances in the region (legacy Part 1 support).
    """
    instances = []
    paginator = ec2_client.get_paginator('describe_instances')
    for page in paginator.paginate():
        for reservation in page.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                instances.append(
                    EC2Instance(
                        instance_id=instance["InstanceId"],
                        instance_type=instance["InstanceType"],
                        state=instance["State"]["Name"],
                        public_ip=instance.get("PublicIpAddress")
                    )
                )
    return instances

@handle_boto3_errors
def discover_security_groups(ec2_client) -> List[SecurityGroup]:
    """
    Discovers Security Groups in the region (legacy Part 1 support).
    """
    groups = []
    paginator = ec2_client.get_paginator('describe_security_groups')
    for page in paginator.paginate():
        for sg in page.get("SecurityGroups", []):
            groups.append(
                SecurityGroup(
                    group_id=sg["GroupId"],
                    group_name=sg["GroupName"],
                    description=sg.get("Description", "")
                )
            )
    return groups

def discover_ec2_resources(
    ec2_client,
    region: str = "us-east-1",
    account_id: str = ""
) -> List[DiscoveredResourceData]:
    """
    Discovers EC2 instances and returns normalized DiscoveredResourceData objects.
    Paginates through describe_instances.
    """
    resources = []
    try:
        paginator = ec2_client.get_paginator('describe_instances')
        for page in paginator.paginate():
            for reservation in page.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instance_id = instance["InstanceId"]
                    state_name = instance.get("State", {}).get("Name", "unknown")
                    
                    # Extract Name tag if present
                    name = instance_id
                    tags_dict = {}
                    for tag in instance.get("Tags", []):
                        k = tag.get("Key")
                        v = tag.get("Value")
                        if k:
                            tags_dict[k] = v
                            if k.lower() == "name" and v:
                                name = v

                    arn = f"arn:aws:ec2:{region}:{account_id}:instance/{instance_id}" if account_id else f"arn:aws:ec2:{region}::instance/{instance_id}"

                    sg_list = [
                        {"id": sg.get("GroupId"), "name": sg.get("GroupName")}
                        for sg in instance.get("SecurityGroups", [])
                    ]

                    metadata = {
                        "instance_type": instance.get("InstanceType"),
                        "state": state_name,
                        "public_ip": instance.get("PublicIpAddress"),
                        "private_ip": instance.get("PrivateIpAddress"),
                        "vpc_id": instance.get("VpcId"),
                        "subnet_id": instance.get("SubnetId"),
                        "security_groups": sg_list,
                        "tags": tags_dict,
                    }

                    resources.append(
                        DiscoveredResourceData(
                            service="ec2",
                            resource_type="ec2:instance",
                            resource_id=instance_id,
                            resource_name=name,
                            region=region,
                            arn=arn,
                            status=state_name,
                            metadata=metadata,
                        )
                    )
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        logger.warning(f"EC2 discovery encountered AWS ClientError ({error_code}): {error_msg}")
        raise
    except Exception as e:
        logger.warning(f"Unexpected error discovering EC2 instances: {e}")
        raise

    return resources

def discover_security_group_resources(
    ec2_client,
    region: str = "us-east-1",
    account_id: str = ""
) -> List[DiscoveredResourceData]:
    """
    Discovers Security Groups and returns normalized DiscoveredResourceData objects.
    Paginates through describe_security_groups.
    """
    resources = []
    try:
        paginator = ec2_client.get_paginator('describe_security_groups')
        for page in paginator.paginate():
            for sg in page.get("SecurityGroups", []):
                group_id = sg["GroupId"]
                group_name = sg.get("GroupName", group_id)
                arn = f"arn:aws:ec2:{region}:{account_id}:security-group/{group_id}" if account_id else f"arn:aws:ec2:{region}::security-group/{group_id}"

                tags_dict = {
                    tag.get("Key"): tag.get("Value")
                    for tag in sg.get("Tags", [])
                    if tag.get("Key")
                }

                metadata = {
                    "group_name": group_name,
                    "description": sg.get("Description", ""),
                    "vpc_id": sg.get("VpcId"),
                    "inbound_rules_count": len(sg.get("IpPermissions", [])),
                    "outbound_rules_count": len(sg.get("IpPermissionsEgress", [])),
                    "ip_permissions": sg.get("IpPermissions", []),
                    "ip_permissions_egress": sg.get("IpPermissionsEgress", []),
                    "tags": tags_dict,
                }

                resources.append(
                    DiscoveredResourceData(
                        service="ec2",
                        resource_type="ec2:security-group",
                        resource_id=group_id,
                        resource_name=group_name,
                        region=region,
                        arn=arn,
                        status="active",
                        metadata=metadata,
                    )
                )
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        logger.warning(f"Security Group discovery encountered AWS ClientError ({error_code}): {error_msg}")
        raise
    except Exception as e:
        logger.warning(f"Unexpected error discovering Security Groups: {e}")
        raise

    return resources
