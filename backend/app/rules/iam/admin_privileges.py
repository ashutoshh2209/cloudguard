from typing import Any, Optional, Dict
from app.rules.base import SecurityRule, RuleEvaluationResult
from app.rules.registry import RuleRegistry
from app.rules.helpers import extract_resource_metadata
from app.findings.schemas import Severity

@RuleRegistry.register
class IAMAdminPrivilegesRule(SecurityRule):
    rule_id = "IAM_ADMIN_PRIVILEGES"
    title = "IAM identity possesses unrestricted administrative privileges"
    service = "iam"
    resource_type = "iam_identity"
    severity = Severity.HIGH
    category = "identity"
    description = "Detects IAM users or roles assigned full administrator permissions (e.g. AdministratorAccess or wildcard actions)."
    recommendation = "Enforce the principle of least privilege by scoping down permissions to only necessary actions."

    def evaluate(self, resource: Any, context: Optional[dict] = None) -> RuleEvaluationResult:
        meta = extract_resource_metadata(resource, context)
        
        # Check for malformed policies data
        policies = meta.get("policies") or meta.get("attached_policies", [])
        if policies and not isinstance(policies, (list, tuple)):
            return RuleEvaluationResult.error_result("Malformed policies data in IAM metadata.")
        
        policies_list = [str(p) for p in policies] if isinstance(policies, (list, tuple)) else []
        
        has_admin = (
            meta.get("is_admin", False) is True or
            meta.get("has_admin_privileges", False) is True or
            any("AdministratorAccess" in p for p in policies_list) or
            any("*:*" in p for p in policies_list)
        )
        
        if has_admin:
            return RuleEvaluationResult.fail_result(
                message="IAM identity has unrestricted administrator permissions.",
                evidence={
                    "admin_privileges": True,
                    "policies": policies_list or ["AdministratorAccess"]
                },
                recommendation=self.recommendation,
            )
            
        return RuleEvaluationResult.pass_result("IAM identity does not have unrestricted administrator permissions.")
