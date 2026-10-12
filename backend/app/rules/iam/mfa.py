from typing import Any, Optional, Dict
from app.rules.base import SecurityRule, RuleEvaluationResult, CheckStatus
from app.rules.registry import RuleRegistry
from app.rules.helpers import extract_resource_metadata
from app.findings.schemas import Severity

@RuleRegistry.register
class IAMMFADisabledRule(SecurityRule):
    rule_id = "IAM_MFA_DISABLED"
    title = "IAM user does not have MFA enabled"
    service = "iam"
    resource_type = "iam_user"
    severity = Severity.HIGH
    category = "identity"
    description = "Detects IAM users with console access where MFA is not enabled."
    recommendation = "Enable MFA for the IAM user."

    def evaluate(self, resource: Any, context: Optional[dict] = None) -> RuleEvaluationResult:
        meta = extract_resource_metadata(resource, context)
        
        # Check if user has console access
        has_console_access = (
            meta.get("has_console_access", False) or
            meta.get("console_access", False) or
            ("password_last_used" in meta and meta["password_last_used"] is not None)
        )
        
        # If user has no console access, MFA is not required (pass/not-applicable)
        if not has_console_access:
            return RuleEvaluationResult.pass_result("IAM user does not have console access (MFA check not applicable).")

        # Check for malformed MFA configuration
        if "mfa" in meta and not isinstance(meta["mfa"], (dict, bool)):
            return RuleEvaluationResult.error_result("Malformed mfa configuration in metadata.")

        mfa_config = meta.get("mfa", {})
        if isinstance(mfa_config, dict):
            mfa_enabled = mfa_config.get("mfa_enabled", False)
        elif isinstance(mfa_config, bool):
            mfa_enabled = mfa_config
        elif "mfa_enabled" in meta:
            mfa_enabled = bool(meta["mfa_enabled"])
        else:
            mfa_enabled = False

        if not mfa_enabled:
            return RuleEvaluationResult.fail_result(
                message="IAM user has console access but MFA is disabled.",
                evidence={"mfa_enabled": False, "has_console_access": True},
                recommendation=self.recommendation,
            )
            
        return RuleEvaluationResult.pass_result("IAM user has MFA enabled.")
