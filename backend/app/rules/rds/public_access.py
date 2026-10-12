from typing import Any, Optional, Dict
from app.rules.base import SecurityRule, RuleEvaluationResult
from app.rules.registry import RuleRegistry
from app.rules.helpers import extract_resource_metadata
from app.findings.schemas import Severity

@RuleRegistry.register
class RDSPublicAccessRule(SecurityRule):
    rule_id = "RDS_PUBLIC_ACCESS"
    title = "RDS instance is publicly accessible"
    service = "rds"
    resource_type = "rds_instance"
    severity = Severity.HIGH
    category = "database"
    description = "Detects RDS instances configured as publicly accessible."
    recommendation = "Disable public accessibility unless there is a justified requirement. Use private subnets instead."

    def evaluate(self, resource: Any, context: Optional[dict] = None) -> RuleEvaluationResult:
        meta = extract_resource_metadata(resource, context)
        
        raw_val = meta.get("publicly_accessible")
        if raw_val is not None and not isinstance(raw_val, bool):
            return RuleEvaluationResult.error_result("Malformed publicly_accessible value in RDS metadata.")
        
        publicly_accessible = bool(raw_val) if raw_val is not None else False
        
        if publicly_accessible:
            return RuleEvaluationResult.fail_result(
                message="RDS database instance is configured as publicly accessible.",
                evidence={"publicly_accessible": True},
                recommendation=self.recommendation,
            )
            
        return RuleEvaluationResult.pass_result("RDS instance is private and not publicly accessible.")
