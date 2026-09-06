from typing import Any, Optional
from app.rules.base import SecurityRule
from app.rules.registry import RuleRegistry
from app.findings.schemas import Severity

@RuleRegistry.register
class S3PublicAccessRule(SecurityRule):
    rule_id = "S3_PUBLIC_ACCESS"
    title = "S3 bucket is publicly accessible"
    service = "s3"
    resource_type = "s3_bucket"
    severity = Severity.CRITICAL
    category = "storage"
    description = "Detects whether an S3 bucket is publicly accessible based on its configuration."
    recommendation = "Enable S3 Block Public Access and review the bucket policy."

    def evaluate(self, resource: Any, context: dict) -> Optional[dict]:
        # Context will be enriched by the scanner
        # The S3Scanner will prepare public access metadata
        public_access_config = context.get("public_access", {})
        
        # We define "public" here if ACLs or Policy allow it explicitly (simulated via scanner enrichment)
        # For this part, we check if the scanner explicitly flagged it.
        is_public = public_access_config.get("is_public", False)
        
        if is_public:
            return {
                "public_access": True,
                "reason": public_access_config.get("reason", "Unknown")
            }
        return None
