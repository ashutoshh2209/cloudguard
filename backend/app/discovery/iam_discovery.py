from typing import List, Tuple
from botocore.exceptions import ClientError
from app.schemas.inventory import IAMUser, IAMRole
from app.schemas.resource import DiscoveredResourceData
from app.aws.connection import handle_boto3_errors
from app.core.logging import logger

@handle_boto3_errors
def discover_iam_users(iam_client) -> List[IAMUser]:
    """
    Discovers IAM users globally (legacy Part 1 support).
    """
    users = []
    paginator = iam_client.get_paginator('list_users')
    for page in paginator.paginate():
        for user in page.get("Users", []):
            users.append(
                IAMUser(
                    user_name=user["UserName"],
                    arn=user["Arn"],
                    create_date=str(user["CreateDate"]) if "CreateDate" in user else None
                )
            )
    return users

@handle_boto3_errors
def discover_iam_roles(iam_client) -> List[IAMRole]:
    """
    Discovers IAM roles globally (legacy Part 1 support).
    """
    roles = []
    paginator = iam_client.get_paginator('list_roles')
    for page in paginator.paginate():
        for role in page.get("Roles", []):
            roles.append(
                IAMRole(
                    role_name=role["RoleName"],
                    arn=role["Arn"]
                )
            )
    return roles

def discover_iam_resources(
    iam_client,
    account_id: str = ""
) -> List[DiscoveredResourceData]:
    """
    Discovers IAM Users and Roles, returning normalized DiscoveredResourceData objects.
    Paginates through list_users and list_roles.
    """
    resources = []
    try:
        # 1. Discover Users
        user_paginator = iam_client.get_paginator('list_users')
        for page in user_paginator.paginate():
            for user in page.get("Users", []):
                user_name = user["UserName"]
                arn = user.get("Arn", f"arn:aws:iam::{account_id}:user/{user_name}")

                metadata = {
                    "user_name": user_name,
                    "user_id": user.get("UserId"),
                    "create_date": str(user.get("CreateDate")) if "CreateDate" in user else None,
                    "path": user.get("Path"),
                }
                if "PasswordLastUsed" in user:
                    metadata["password_last_used"] = str(user["PasswordLastUsed"])

                resources.append(
                    DiscoveredResourceData(
                        service="iam",
                        resource_type="iam:user",
                        resource_id=user_name,
                        resource_name=user_name,
                        region="global",
                        arn=arn,
                        status="active",
                        metadata=metadata,
                    )
                )

        # 2. Discover Roles
        role_paginator = iam_client.get_paginator('list_roles')
        for page in role_paginator.paginate():
            for role in page.get("Roles", []):
                role_name = role["RoleName"]
                arn = role.get("Arn", f"arn:aws:iam::{account_id}:role/{role_name}")

                metadata = {
                    "role_name": role_name,
                    "role_id": role.get("RoleId"),
                    "create_date": str(role.get("CreateDate")) if "CreateDate" in role else None,
                    "path": role.get("Path"),
                    "description": role.get("Description", ""),
                }

                resources.append(
                    DiscoveredResourceData(
                        service="iam",
                        resource_type="iam:role",
                        resource_id=role_name,
                        resource_name=role_name,
                        region="global",
                        arn=arn,
                        status="active",
                        metadata=metadata,
                    )
                )
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        logger.warning(f"IAM discovery encountered AWS ClientError ({error_code}): {error_msg}")
        raise
    except Exception as e:
        logger.warning(f"Unexpected error discovering IAM resources: {e}")
        raise

    return resources
