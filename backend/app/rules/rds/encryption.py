from typing import Any, Optional
from app.rules.base import SecurityRule
from app.rules.registry import RuleRegistry
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

    def evaluate(self, resource: Any, context: dict) -> Optional[dict]:
        storage_encrypted = context.get("storage_encrypted", True) # Assume secure if missing
        
        if not storage_encrypted:
            return {
                "encrypted": False
            }
        return None
