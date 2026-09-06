from typing import Any, Optional
from app.rules.base import SecurityRule
from app.rules.registry import RuleRegistry
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

    def evaluate(self, resource: Any, context: dict) -> Optional[dict]:
        publicly_accessible = context.get("publicly_accessible", False)
        
        if publicly_accessible:
            return {
                "publicly_accessible": True
            }
        return None
