from typing import Any, Optional, Dict
from app.rules.base import SecurityRule, RuleEvaluationResult
from app.rules.registry import RuleRegistry
from app.rules.helpers import extract_resource_metadata
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

    def evaluate(self, resource: Any, context: Optional[dict] = None) -> RuleEvaluationResult:
        meta = extract_resource_metadata(resource, context)
        
        # Check for malformed encryption data
        if "encryption" in meta and not isinstance(meta["encryption"], (dict, bool)):
            return RuleEvaluationResult.error_result("Malformed encryption configuration in metadata.")
        
        encryption_config = meta.get("encryption")
        if isinstance(encryption_config, dict):
            is_encrypted = encryption_config.get("is_encrypted", True)
        elif isinstance(encryption_config, bool):
            is_encrypted = encryption_config
        elif "is_encrypted" in meta:
            is_encrypted = bool(meta["is_encrypted"])
        elif "server_side_encryption" in meta:
            is_encrypted = bool(meta["server_side_encryption"])
        else:
            # If not configured/specified in test or discovery context
            is_encrypted = True

        if not is_encrypted:
            return RuleEvaluationResult.fail_result(
                message="S3 bucket does not have server-side encryption enabled.",
                evidence={"encrypted": False},
                recommendation=self.recommendation,
            )
        
        return RuleEvaluationResult.pass_result("S3 bucket has default server-side encryption enabled.")
