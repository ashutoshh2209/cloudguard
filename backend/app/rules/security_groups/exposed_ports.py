from typing import Any, Optional, List, Dict
from app.rules.base import SecurityRule, RuleEvaluationResult
from app.rules.registry import RuleRegistry
from app.rules.helpers import extract_resource_metadata
from app.findings.schemas import Severity

def check_open_port(ip_permissions: List[dict], target_ports: List[int]) -> Optional[dict]:
    """Helper to check if specific ports are exposed to 0.0.0.0/0 or ::/0."""
    if not isinstance(ip_permissions, (list, tuple)):
        return None
    for permission in ip_permissions:
        if not isinstance(permission, dict):
            continue
        ip_protocol = str(permission.get("IpProtocol", "")).lower()
        # -1 or "all" means all protocols
        if ip_protocol != "tcp" and ip_protocol != "-1" and ip_protocol != "all":
            continue
            
        from_port = permission.get("FromPort", 0)
        to_port = permission.get("ToPort", 65535)
        if ip_protocol in ("-1", "all"):
            from_port = 0
            to_port = 65535
        
        # Check if any of the target ports fall in the range
        exposed_ports = []
        for port in target_ports:
            if from_port <= port <= to_port:
                # Check for 0.0.0.0/0 in IpRanges
                for ip_range in permission.get("IpRanges", []):
                    if isinstance(ip_range, dict) and ip_range.get("CidrIp") == "0.0.0.0/0":
                        exposed_ports.append(port)
                        break
                # Check for ::/0 in Ipv6Ranges
                for ipv6_range in permission.get("Ipv6Ranges", []):
                    if isinstance(ipv6_range, dict) and ipv6_range.get("CidrIpv6") == "::/0":
                        if port not in exposed_ports:
                            exposed_ports.append(port)
                        break
                        
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

    def evaluate(self, resource: Any, context: Optional[dict] = None) -> RuleEvaluationResult:
        meta = extract_resource_metadata(resource, context)
        raw_perms = meta.get("ip_permissions", [])
        if raw_perms and not isinstance(raw_perms, (list, tuple)):
            return RuleEvaluationResult.error_result("Malformed ip_permissions data in security group metadata.")
        
        evidence = check_open_port(raw_perms, [22])
        if evidence:
            return RuleEvaluationResult.fail_result(
                message="Security group allows unrestricted SSH access (port 22) from 0.0.0.0/0.",
                evidence=evidence,
                recommendation=self.recommendation,
            )
        return RuleEvaluationResult.pass_result("Security group does not allow unrestricted SSH access.")

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

    def evaluate(self, resource: Any, context: Optional[dict] = None) -> RuleEvaluationResult:
        meta = extract_resource_metadata(resource, context)
        raw_perms = meta.get("ip_permissions", [])
        if raw_perms and not isinstance(raw_perms, (list, tuple)):
            return RuleEvaluationResult.error_result("Malformed ip_permissions data in security group metadata.")

        evidence = check_open_port(raw_perms, [3389])
        if evidence:
            return RuleEvaluationResult.fail_result(
                message="Security group allows unrestricted RDP access (port 3389) from 0.0.0.0/0.",
                evidence=evidence,
                recommendation=self.recommendation,
            )
        return RuleEvaluationResult.pass_result("Security group does not allow unrestricted RDP access.")

@RuleRegistry.register
class DatabasePortOpenToWorldRule(SecurityRule):
    rule_id = "DATABASE_PORT_OPEN_TO_WORLD"
    title = "Security group allows unrestricted access to database ports"
    service = "ec2"
    resource_type = "security_group"
    severity = Severity.CRITICAL
    category = "network"
    description = "Detects common database ports (3306, 5432, 1433, 1521, 27017, 6379) exposed to 0.0.0.0/0."
    recommendation = "Restrict database ports to internal VPC CIDRs or specific trusted IP ranges. Publicly exposed databases significantly increase attack surface."

    def evaluate(self, resource: Any, context: Optional[dict] = None) -> RuleEvaluationResult:
        meta = extract_resource_metadata(resource, context)
        raw_perms = meta.get("ip_permissions", [])
        if raw_perms and not isinstance(raw_perms, (list, tuple)):
            return RuleEvaluationResult.error_result("Malformed ip_permissions data in security group metadata.")

        db_ports = [3306, 5432, 1433, 1521, 27017, 6379]
        evidence = check_open_port(raw_perms, db_ports)
        if evidence:
            return RuleEvaluationResult.fail_result(
                message=f"Security group exposes database port(s) {evidence.get('ports')} to 0.0.0.0/0.",
                evidence=evidence,
                recommendation=self.recommendation,
            )
        return RuleEvaluationResult.pass_result("Security group does not expose sensitive database ports.")
