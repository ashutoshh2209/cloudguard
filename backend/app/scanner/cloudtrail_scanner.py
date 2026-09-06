from typing import List, Tuple
from app.scanner.base import ServiceScanner
from app.schemas.inventory import CloudTrail
from app.findings.schemas import Finding
from botocore.exceptions import ClientError
from app.core.logging import logger

class CloudTrailScanner(ServiceScanner):
    service = "cloudtrail"

    def scan(self, resources: List[CloudTrail], scan_id: str) -> Tuple[List[Finding], int, int]:
        findings = []
        total_passed = 0
        total_failed = 0
        for trail in resources:
            name = trail.name
            context = {}

            try:
                response = self.client.get_trail_status(Name=name)
                context["is_logging"] = response.get("IsLogging", False)
            except Exception as e:
                logger.error(f"Error preparing CloudTrail context for {name}: {e}")
                context["is_logging"] = False

            f_res, p, f = self.evaluate_rules(
                resource_id=name,
                resource_name=name,
                resource_data=trail,
                context=context,
                scan_id=scan_id
            )
            findings.extend(f_res)
            total_passed += p
            total_failed += f
        return findings, total_passed, total_failed
