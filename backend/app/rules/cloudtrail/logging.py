from typing import Any, Optional, Dict
from app.rules.base import SecurityRule, RuleEvaluationResult
from app.rules.registry import RuleRegistry
from app.rules.helpers import extract_resource_metadata
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

    def evaluate(self, resource: Any, context: Optional[dict] = None) -> RuleEvaluationResult:
        meta = extract_resource_metadata(resource, context)
        
        raw_val = meta.get("is_logging")
        if raw_val is not None and not isinstance(raw_val, bool):
            return RuleEvaluationResult.error_result("Malformed is_logging value in CloudTrail metadata.")

        is_logging = bool(raw_val) if raw_val is not None else True
        
        if not is_logging:
            return RuleEvaluationResult.fail_result(
                message="CloudTrail logging is not enabled or actively logging.",
                evidence={"logging_enabled": False},
                recommendation=self.recommendation,
            )
            
        return RuleEvaluationResult.pass_result("CloudTrail is actively logging.")
