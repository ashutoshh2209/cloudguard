from typing import List, Tuple, Any
from app.scanner.base import ServiceScanner
from app.schemas.inventory import EC2Instance, SecurityGroup
from app.findings.schemas import Finding
from botocore.exceptions import ClientError
from app.core.logging import logger

class EC2Scanner(ServiceScanner):
    service = "ec2"

    def scan_instances(self, instances: List[EC2Instance], scan_id: str) -> Tuple[List[Finding], int, int]:
        findings = []
        total_passed = 0
        total_failed = 0
        for instance in instances:
            context = {
                "public_ip": instance.public_ip
            }
            f_res, p, f = self.evaluate_rules(
                resource_id=instance.instance_id,
                resource_name=instance.instance_id,
                resource_data=instance,
                context=context,
                scan_id=scan_id
            )
            findings.extend(f_res)
            total_passed += p
            total_failed += f
        return findings, total_passed, total_failed

    def scan_security_groups(self, security_groups: List[SecurityGroup], scan_id: str) -> Tuple[List[Finding], int, int]:
        findings = []
        total_passed = 0
        total_failed = 0
        for sg in security_groups:
            context = {}
            try:
                # Fetch full rules
                response = self.client.describe_security_groups(GroupIds=[sg.group_id])
                if response.get("SecurityGroups"):
                    sg_details = response["SecurityGroups"][0]
                    context["ip_permissions"] = sg_details.get("IpPermissions", [])
            except Exception as e:
                logger.error(f"Error preparing SG context for {sg.group_id}: {e}")

            # Overriding service to match rules mapping
            original_service = self.service
            self.service = "security_groups"
            self.rules = self.rules = __import__('app.rules.registry').rules.registry.RuleRegistry.get_rules_for_service("ec2") # wait, we mapped rules differently.
            
            # Let's fix this cleanly. 
            from app.rules.registry import RuleRegistry
            self.rules = RuleRegistry.get_rules_for_service(self.service) # Ensure service name matches the rule registration! wait, the sg rules registered as `ec2`
            # In exposed_ports.py, rule.service is "ec2" and resource_type is "security_group". Let's rely on that!
            self.service = original_service
            self.rules = RuleRegistry.get_rules_for_service(self.service)
            
            # We filter rules by resource_type in evaluate loop
            sg_rules = [r for r in self.rules if r.resource_type == "security_group"]
            
            for rule in sg_rules:
                evidence = rule.evaluate(sg, context)
                if evidence:
                    total_failed += 1
                    evidence_dict = evidence.evidence if hasattr(evidence, "evidence") and isinstance(evidence.evidence, dict) else (dict(evidence) if isinstance(evidence, dict) else {})
                    import uuid
                    finding_id = str(uuid.uuid4())
                    findings.append(
                        Finding(
                            finding_id=finding_id,
                            rule_id=rule.rule_id,
                            title=rule.title,
                            severity=rule.severity,
                            service=rule.service,
                            resource_id=sg.group_id,
                            resource_name=sg.group_name,
                            region=self.region,
                            category=rule.category,
                            description=rule.description,
                            evidence=evidence_dict,
                            recommendation=rule.recommendation
                        )
                    )
                else:
                    total_passed += 1

        return findings, total_passed, total_failed

    def scan(self, resources: Any, scan_id: str) -> Tuple[List[Finding], int, int]:
        return [], 0, 0
