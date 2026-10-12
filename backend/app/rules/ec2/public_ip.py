from typing import Any, Optional, Dict
from app.rules.base import SecurityRule, RuleEvaluationResult
from app.rules.registry import RuleRegistry
from app.rules.helpers import extract_resource_metadata
from app.findings.schemas import Severity

@RuleRegistry.register
class EC2PublicIPRule(SecurityRule):
    rule_id = "EC2_PUBLIC_IP"
    title = "EC2 instance has a public IP address"
    service = "ec2"
    resource_type = "ec2_instance"
    severity = Severity.MEDIUM
    category = "network"
    description = "Detects EC2 instances with public IP addresses. This implies the instance is publicly reachable if security groups allow it."
    recommendation = "Review if the instance legitimately needs a public IP. Prefer using a load balancer or bastion host instead."

    def evaluate(self, resource: Any, context: Optional[dict] = None) -> RuleEvaluationResult:
        meta = extract_resource_metadata(resource, context)
        
        # Check instance state
        state = str(meta.get("state", "")).lower()
        if state in ("terminated", "shutting-down"):
            return RuleEvaluationResult.not_applicable_result(f"Instance is in '{state}' state.")

        # Check for malformed public_ip data
        raw_ip = meta.get("public_ip") or meta.get("PublicIpAddress")
        if raw_ip is not None and not isinstance(raw_ip, (str, bool)):
            return RuleEvaluationResult.error_result("Malformed public_ip configuration in metadata.")

        public_ip = str(raw_ip).strip() if raw_ip else None
        
        if public_ip and public_ip != "None" and public_ip != "False":
            return RuleEvaluationResult.fail_result(
                message=f"EC2 instance has an assigned public IP address ({public_ip}).",
                evidence={"public_ip": public_ip},
                recommendation=self.recommendation,
            )
        
        return RuleEvaluationResult.pass_result("EC2 instance does not have a public IP address.")
