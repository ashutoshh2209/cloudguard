from typing import Any, Optional, Dict
from app.rules.base import SecurityRule, RuleEvaluationResult, CheckStatus
from app.rules.registry import RuleRegistry
from app.rules.helpers import extract_resource_metadata
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

    def evaluate(self, resource: Any, context: Optional[dict] = None) -> RuleEvaluationResult:
        meta = extract_resource_metadata(resource, context)
        
        # Check for malformed data
        if "public_access" in meta and not isinstance(meta["public_access"], (dict, bool)):
            return RuleEvaluationResult.error_result("Malformed public_access configuration in metadata.")
        
        public_access_config = meta.get("public_access", {})
        if isinstance(public_access_config, bool):
            is_public = public_access_config
            reason = "Bucket flagged as public"
        elif isinstance(public_access_config, dict):
            is_public = public_access_config.get("is_public", False)
            reason = public_access_config.get("reason", "Public access enabled via policy or ACL")
        else:
            is_public = False
            reason = "Unknown"

        # Also inspect direct flags like acl or is_public on metadata
        if not is_public:
            if meta.get("is_public") is True:
                is_public = True
                reason = "is_public attribute set to True"
            elif meta.get("public") is True:
                is_public = True
                reason = "public attribute set to True"
            elif str(meta.get("acl", "")).lower() in ("public-read", "public-read-write", "authenticated-read"):
                is_public = True
                reason = f"Public ACL configured: {meta.get('acl')}"

        if is_public:
            return RuleEvaluationResult.fail_result(
                message=f"S3 bucket allows public access ({reason}).",
                evidence={"public_access": True, "reason": reason},
                recommendation=self.recommendation,
            )
        
        return RuleEvaluationResult.pass_result("S3 bucket is not publicly accessible.")
