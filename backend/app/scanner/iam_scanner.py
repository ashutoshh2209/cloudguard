from typing import List, Tuple
from app.scanner.base import ServiceScanner
from app.schemas.inventory import IAMUser
from app.findings.schemas import Finding
from botocore.exceptions import ClientError
from app.core.logging import logger

class IAMScanner(ServiceScanner):
    service = "iam"

    def scan(self, resources: List[IAMUser], scan_id: str) -> Tuple[List[Finding], int, int]:
        findings = []
        total_passed = 0
        total_failed = 0
        for user in resources:
            user_name = user.user_name
            context = {}

            try:
                # Check for console access (Login Profile)
                try:
                    self.client.get_login_profile(UserName=user_name)
                    context["has_console_access"] = True
                except ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchEntity':
                        context["has_console_access"] = False
                    else:
                        context["has_console_access"] = False

                if context["has_console_access"]:
                    # Check MFA
                    try:
                        mfa_devices = self.client.list_mfa_devices(UserName=user_name)
                        if mfa_devices.get('MFADevices'):
                            context["mfa"] = {"mfa_enabled": True}
                        else:
                            context["mfa"] = {"mfa_enabled": False}
                    except ClientError:
                        context["mfa"] = {"mfa_enabled": False}

            except Exception as e:
                logger.error(f"Error preparing IAM context for {user_name}: {e}")

            f_res, p, f = self.evaluate_rules(
                resource_id=user.arn,
                resource_name=user_name,
                resource_data=user,
                context=context,
                scan_id=scan_id
            )
            findings.extend(f_res)
            total_passed += p
            total_failed += f
        return findings, total_passed, total_failed
