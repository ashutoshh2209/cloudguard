from typing import Any, Optional, List
from app.rules.base import SecurityRule
from app.rules.registry import RuleRegistry
from app.findings.schemas import Severity

def check_open_port(ip_permissions: List[dict], target_ports: List[int]) -> Optional[dict]:
    """Helper to check if specific ports are exposed to 0.0.0.0/0."""
    for permission in ip_permissions:
        ip_protocol = permission.get("IpProtocol", "")
        # -1 means all protocols
        if ip_protocol != "tcp" and ip_protocol != "-1":
            continue
            
        from_port = permission.get("FromPort", 0)
        to_port = permission.get("ToPort", 65535)
        
        # Check if any of the target ports fall in the range
        exposed_ports = []
        for port in target_ports:
            if from_port <= port <= to_port or ip_protocol == "-1":
                # Check for 0.0.0.0/0
                for ip_range in permission.get("IpRanges", []):
                    if ip_range.get("CidrIp") == "0.0.0.0/0":
                        exposed_ports.append(port)
                        
        if exposed_ports:
            return {
                "ports": exposed_ports,
                "protocol": ip_protocol,
                "source": "0.0.0.0/0"
            }
    return None

@RuleRegistry.register
class SSHOpenToWorldRule(SecurityRule):
    rule_id = "SSH_OPEN_TO_WORLD"
    title = "Security group allows unrestricted SSH access"
    service = "ec2"
    resource_type = "security_group"
    severity = Severity.CRITICAL
    category = "network"
    description = "Detects inbound TCP port 22 exposed to 0.0.0.0/0."
    recommendation = "Restrict SSH access to trusted IP ranges or use a safer access mechanism like AWS Systems Manager."

    def evaluate(self, resource: Any, context: dict) -> Optional[dict]:
        ip_permissions = context.get("ip_permissions", [])
        evidence = check_open_port(ip_permissions, [22])
        if evidence:
            return evidence
        return None

@RuleRegistry.register
class RDPOpenToWorldRule(SecurityRule):
    rule_id = "RDP_OPEN_TO_WORLD"
    title = "Security group allows unrestricted RDP access"
    service = "ec2"
    resource_type = "security_group"
    severity = Severity.CRITICAL
    category = "network"
    description = "Detects inbound TCP port 3389 exposed to 0.0.0.0/0."
    recommendation = "Restrict RDP access to trusted networks."

    def evaluate(self, resource: Any, context: dict) -> Optional[dict]:
        ip_permissions = context.get("ip_permissions", [])
        evidence = check_open_port(ip_permissions, [3389])
        if evidence:
            return evidence
        return None

@RuleRegistry.register
class DatabasePortOpenToWorldRule(SecurityRule):
    rule_id = "DATABASE_PORT_OPEN_TO_WORLD"
    title = "Security group allows unrestricted access to database ports"
    service = "ec2"
    resource_type = "security_group"
    severity = Severity.CRITICAL
    category = "network"
    description = "Detects common database ports (3306, 5432, 1433, 1521, 27017) exposed to 0.0.0.0/0."
    recommendation = "Restrict database ports to internal VPC CIDRs or specific trusted IP ranges. Publicly exposed databases significantly increase attack surface."

    def evaluate(self, resource: Any, context: dict) -> Optional[dict]:
        ip_permissions = context.get("ip_permissions", [])
        db_ports = [3306, 5432, 1433, 1521, 27017]
        evidence = check_open_port(ip_permissions, db_ports)
        if evidence:
            return evidence
        return None
