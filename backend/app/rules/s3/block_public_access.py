from typing import Any, Optional
from app.rules.base import SecurityRule
from app.rules.registry import RuleRegistry
from app.findings.schemas import Severity

@RuleRegistry.register
class S3BlockPublicAccessDisabledRule(SecurityRule):
    rule_id = "S3_BLOCK_PUBLIC_ACCESS_DISABLED"
    title = "S3 Block Public Access protections are disabled"
    service = "s3"
    resource_type = "s3_bucket"
    severity = Severity.HIGH
    category = "storage"
    description = "Detects when S3 Block Public Access is disabled or insufficient."
    recommendation = "Enable all Block Public Access settings for the bucket."

    def evaluate(self, resource: Any, context: dict) -> Optional[dict]:
        bpa_config = context.get("block_public_access", {})
        
        # If any of the 4 block public access boolean settings are False, it's a violation.
        # If missing entirely, assume disabled (or scanner says it's disabled).
        is_enabled = bpa_config.get("is_fully_enabled", False)
        
        if not is_enabled:
            return {
                "block_public_access_enabled": False,
                "missing_protections": bpa_config.get("missing_protections", ["all"])
            }
        return None
