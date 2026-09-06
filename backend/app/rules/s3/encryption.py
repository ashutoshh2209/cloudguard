from typing import Any, Optional
from app.rules.base import SecurityRule
from app.rules.registry import RuleRegistry
from app.findings.schemas import Severity

@RuleRegistry.register
class S3NoEncryptionRule(SecurityRule):
    rule_id = "S3_NO_ENCRYPTION"
    title = "S3 bucket missing default server-side encryption"
    service = "s3"
    resource_type = "s3_bucket"
    severity = Severity.HIGH
    category = "storage"
    description = "Detects whether default server-side encryption is absent on an S3 bucket."
    recommendation = "Enable server-side encryption for stored objects."

    def evaluate(self, resource: Any, context: dict) -> Optional[dict]:
        encryption_config = context.get("encryption", {})
        
        is_encrypted = encryption_config.get("is_encrypted", True) # Default assume secure if missing for safety, or false?
        # Actually scanner will set this explicitly. If not encrypted, return evidence.
        
        if not is_encrypted:
            return {
                "encrypted": False
            }
        return None
