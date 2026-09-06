from typing import Any, Optional
from app.rules.base import SecurityRule
from app.rules.registry import RuleRegistry
from app.findings.schemas import Severity

@RuleRegistry.register
class IAMMFADisabledRule(SecurityRule):
    rule_id = "IAM_MFA_DISABLED"
    title = "IAM user does not have MFA enabled"
    service = "iam"
    resource_type = "iam_user"
    severity = Severity.HIGH
    category = "identity"
    description = "Detects IAM users with console access where MFA is not enabled."
    recommendation = "Enable MFA for the IAM user."

    def evaluate(self, resource: Any, context: dict) -> Optional[dict]:
        mfa_config = context.get("mfa", {})
        
        # Only evaluate console users
        if not context.get("has_console_access", False):
            return None
            
        mfa_enabled = mfa_config.get("mfa_enabled", False)
        
        if not mfa_enabled:
            return {
                "mfa_enabled": False
            }
        return None
