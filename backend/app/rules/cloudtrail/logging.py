from typing import Any, Optional
from app.rules.base import SecurityRule
from app.rules.registry import RuleRegistry
from app.findings.schemas import Severity

@RuleRegistry.register
class CloudTrailDisabledRule(SecurityRule):
    rule_id = "CLOUDTRAIL_DISABLED"
    title = "CloudTrail logging is not enabled"
    service = "cloudtrail"
    resource_type = "cloudtrail_trail"
    severity = Severity.HIGH
    category = "logging"
    description = "Detects when CloudTrail logging is not enabled or actively logging."
    recommendation = "Enable CloudTrail logging to improve auditability and incident investigation."

    def evaluate(self, resource: Any, context: dict) -> Optional[dict]:
        is_logging = context.get("is_logging", True)
        
        if not is_logging:
            return {
                "logging_enabled": False
            }
        return None
