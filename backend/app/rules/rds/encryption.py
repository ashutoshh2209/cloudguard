from typing import Any, Optional, Dict
from app.rules.base import SecurityRule, RuleEvaluationResult
from app.rules.registry import RuleRegistry
from app.rules.helpers import extract_resource_metadata
from app.findings.schemas import Severity

@RuleRegistry.register
class RDSNoEncryptionRule(SecurityRule):
    rule_id = "RDS_NO_ENCRYPTION"
    title = "RDS instance storage is not encrypted"
    service = "rds"
    resource_type = "rds_instance"
    severity = Severity.HIGH
    category = "database"
    description = "Detects RDS instances without storage encryption."
    recommendation = "Enable encryption for database storage."

    def evaluate(self, resource: Any, context: Optional[dict] = None) -> RuleEvaluationResult:
        meta = extract_resource_metadata(resource, context)
        
        raw_val = meta.get("storage_encrypted")
        if raw_val is not None and not isinstance(raw_val, bool):
            return RuleEvaluationResult.error_result("Malformed storage_encrypted value in RDS metadata.")

        storage_encrypted = bool(raw_val) if raw_val is not None else True
        
        if not storage_encrypted:
            return RuleEvaluationResult.fail_result(
                message="RDS database instance storage is not encrypted at rest.",
                evidence={"encrypted": False},
                recommendation=self.recommendation,
            )
            
        return RuleEvaluationResult.pass_result("RDS database instance storage is encrypted.")
