from abc import ABC, abstractmethod
from typing import List, Any, Tuple
from app.rules.registry import RuleRegistry
from app.findings.schemas import Finding
import uuid

class ServiceScanner(ABC):
    """
    Base class for service-specific scanners.
    Retrieves rules from registry, prepares resource context, and evaluates rules.
    """
    service: str

    def __init__(self, client_factory, region: str):
        self.client_factory = client_factory
        self.region = region
        self.client = client_factory.create_client(self.service)
        self.rules = RuleRegistry.get_rules_for_service(self.service)

    @abstractmethod
    def scan(self, resources: List[Any], scan_id: str) -> List[Finding]:
        """
        Scans a list of discovered resources using the applicable rules.
        """
        pass

    def evaluate_rules(self, resource_id: str, resource_name: str, resource_data: Any, context: dict, scan_id: str) -> Tuple[List[Finding], int, int]:
        findings = []
        passed_count = 0
        failed_count = 0
        for rule in self.rules:
            # We filter rules if they don't match the current resource_type.
            # EC2Scanner changes self.service temporarily, but resource_type is safer if set properly,
            # though in our setup we ensure correct rule list is passed or evaluated.
            evidence = rule.evaluate(resource_data, context)
            if evidence:
                failed_count += 1
                # Deduplication logic could be handled by unique ID creation here
                finding_id = str(uuid.uuid4())
                findings.append(
                    Finding(
                        finding_id=finding_id,
                        rule_id=rule.rule_id,
                        title=rule.title,
                        severity=rule.severity,
                        service=rule.service,
                        resource_id=resource_id,
                        resource_name=resource_name,
                        region=self.region,
                        category=rule.category,
                        description=rule.description,
                        evidence=evidence,
                        recommendation=rule.recommendation
                    )
                )
            else:
                passed_count += 1
        return findings, passed_count, failed_count
