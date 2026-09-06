from typing import Any, Optional
from app.rules.base import SecurityRule
from app.rules.registry import RuleRegistry
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

    def evaluate(self, resource: Any, context: dict) -> Optional[dict]:
        public_ip = context.get("public_ip")
        
        if public_ip:
            return {
                "public_ip": public_ip
            }
        return None
