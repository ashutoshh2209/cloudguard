from typing import Any, Optional, Dict
from app.rules.base import SecurityRule, RuleEvaluationResult
from app.rules.registry import RuleRegistry
from app.rules.helpers import extract_resource_metadata
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

    def evaluate(self, resource: Any, context: Optional[dict] = None) -> RuleEvaluationResult:
        meta = extract_resource_metadata(resource, context)
        
        # Check for malformed BPA configuration
        if "block_public_access" in meta and not isinstance(meta["block_public_access"], (dict, bool)):
            return RuleEvaluationResult.error_result("Malformed block_public_access configuration in metadata.")
        
        bpa_config = meta.get("block_public_access", {})
        if isinstance(bpa_config, bool):
            is_enabled = bpa_config
            missing = [] if is_enabled else ["all"]
        elif isinstance(bpa_config, dict):
            if "is_fully_enabled" in bpa_config:
                is_enabled = bool(bpa_config["is_fully_enabled"])
                missing = bpa_config.get("missing_protections", [] if is_enabled else ["all"])
            else:
                checks = {
                    "BlockPublicAcls": bpa_config.get("BlockPublicAcls", False),
                    "IgnorePublicAcls": bpa_config.get("IgnorePublicAcls", False),
                    "BlockPublicPolicy": bpa_config.get("BlockPublicPolicy", False),
                    "RestrictPublicBuckets": bpa_config.get("RestrictPublicBuckets", False),
                }
                missing = [k for k, v in checks.items() if not v]
                is_enabled = len(missing) == 0
        elif "block_public_access_enabled" in meta:
            is_enabled = bool(meta["block_public_access_enabled"])
            missing = [] if is_enabled else ["all"]
        else:
            is_enabled = False
            missing = ["all"]

        if not is_enabled:
            return RuleEvaluationResult.fail_result(
                message="S3 Block Public Access is disabled or insufficient.",
                evidence={
                    "block_public_access_enabled": False,
                    "missing_protections": missing,
                },
                recommendation=self.recommendation,
            )
        
        return RuleEvaluationResult.pass_result("All S3 Block Public Access protections are fully enabled.")
