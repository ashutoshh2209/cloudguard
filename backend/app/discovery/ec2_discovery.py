from typing import List, Tuple
from app.schemas.inventory import EC2Instance, SecurityGroup
from app.aws.connection import handle_boto3_errors

@handle_boto3_errors
def discover_ec2_instances(ec2_client) -> List[EC2Instance]:
    """
    Discovers EC2 instances in the region.
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
    Discovers Security Groups in the region.
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
