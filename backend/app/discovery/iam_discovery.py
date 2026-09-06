from typing import List, Tuple
from app.schemas.inventory import IAMUser, IAMRole
from app.aws.connection import handle_boto3_errors

@handle_boto3_errors
def discover_iam_users(iam_client) -> List[IAMUser]:
    """
    Discovers IAM users globally.
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
    Discovers IAM roles globally.
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
