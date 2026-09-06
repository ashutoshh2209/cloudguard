from typing import List, Tuple
from app.scanner.base import ServiceScanner
from app.schemas.inventory import RDSInstance
from app.findings.schemas import Finding
from botocore.exceptions import ClientError
from app.core.logging import logger

class RDSScanner(ServiceScanner):
    service = "rds"

    def scan(self, resources: List[RDSInstance], scan_id: str) -> Tuple[List[Finding], int, int]:
        findings = []
        total_passed = 0
        total_failed = 0
        for instance in resources:
            identifier = instance.db_instance_identifier
            context = {}

            try:
                response = self.client.describe_db_instances(DBInstanceIdentifier=identifier)
                if response.get("DBInstances"):
                    db_details = response["DBInstances"][0]
                    context["publicly_accessible"] = db_details.get("PubliclyAccessible", False)
                    context["storage_encrypted"] = db_details.get("StorageEncrypted", False)
            except Exception as e:
                logger.error(f"Error preparing RDS context for {identifier}: {e}")

            f_res, p, f = self.evaluate_rules(
                resource_id=identifier,
                resource_name=identifier,
                resource_data=instance,
                context=context,
                scan_id=scan_id
            )
            findings.extend(f_res)
            total_passed += p
            total_failed += f
        return findings, total_passed, total_failed
