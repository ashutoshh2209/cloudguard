from typing import List, Dict
import uuid
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.services.aws_connection_service import aws_connection_service
from app.services.discovery_service import discovery_service
from app.findings.schemas import Finding as FindingSchema, ScanResult, ScanSummary, ScanStatusInfo, CheckSummary
from app.scanner.s3_scanner import S3Scanner
from app.scanner.iam_scanner import IAMScanner
from app.scanner.ec2_scanner import EC2Scanner
from app.scanner.rds_scanner import RDSScanner
from app.scanner.cloudtrail_scanner import CloudTrailScanner
from app.core.logging import logger
import app.rules
from app.risk.scoring import calculate_finding_risk
from app.risk.engine import calculate_security_score, calculate_category_scores
from app.repositories.scan import scan_repo
from app.repositories.resource import resource_repo
from app.repositories.finding import finding_repo
from app.models.category_score import CategoryScore
from app.models.check_result import CheckResult

class ScanManager:
    def __init__(self):
        pass

    def start_scan(self, account_id: str, db: Session) -> ScanResult:
        """
        Orchestrates the entire scanning process synchronously and persists to DB.
        """
        # 1. Fetch AWS Connection via existing service (for credentials)
        status = aws_connection_service.get_status()
        if not status.connected or status.account_id != account_id:
            raise HTTPException(status_code=404, detail="AWS connection not found or inactive")

        factory = aws_connection_service.get_client_factory()
        if not factory:
            raise HTTPException(status_code=400, detail="Cannot connect to AWS. Verify credentials.")
        
        connection = status # For compatibility in the method
        
        # In a real system, the AWSConnection record must exist in DB. 
        # For simplicity in this project, we assume the DB ID matches the account_id or use a dummy.
        db_conn_id = account_id # Since we didn't fully replace the aws_connection_service storage yet, we use account_id as reference.

        # 2. Create Scan Record
        scan = scan_repo.create(db, aws_connection_id=db_conn_id)
        scan_id = scan.id
        
        try:
            # 3. Discover Resources
            logger.info(f"Starting discovery for scan {scan_id}...")
            region = connection.region
            inventory = discovery_service.run_discovery()

            total_resources = (
                len(inventory.s3_buckets) +
                len(inventory.iam_users) +
                len(inventory.ec2_instances) +
                len(inventory.security_groups) +
                len(inventory.rds_instances) +
                len(inventory.cloudtrails)
            )

            # Persist Resources
            resources_data = []
            for b in inventory.s3_buckets:
                resources_data.append({"resource_id": b.name, "resource_type": "AWS::S3::Bucket", "service": "s3", "region": region})
            for u in inventory.iam_users:
                resources_data.append({"resource_id": u.arn, "resource_type": "AWS::IAM::User", "service": "iam", "region": "global", "name": u.user_name})
            for e in inventory.ec2_instances:
                resources_data.append({"resource_id": e.instance_id, "resource_type": "AWS::EC2::Instance", "service": "ec2", "region": region})
            for sg in inventory.security_groups:
                resources_data.append({"resource_id": sg.group_id, "resource_type": "AWS::EC2::SecurityGroup", "service": "ec2", "region": region, "name": sg.group_name})
            for r in inventory.rds_instances:
                resources_data.append({"resource_id": r.db_instance_identifier, "resource_type": "AWS::RDS::DBInstance", "service": "rds", "region": region})
            for c in inventory.cloudtrails:
                resources_data.append({"resource_id": c.name, "resource_type": "AWS::CloudTrail::Trail", "service": "cloudtrail", "region": region})

            resource_repo.bulk_create(db, scan_id, db_conn_id, resources_data)

            # 4. Execute Scanners
            logger.info(f"Starting rules evaluation for scan {scan_id}...")
            s3_scanner = S3Scanner(factory, region)
            iam_scanner = IAMScanner(factory, "global")
            ec2_scanner = EC2Scanner(factory, region)
            rds_scanner = RDSScanner(factory, region)
            cloudtrail_scanner = CloudTrailScanner(factory, region)

            findings: List[FindingSchema] = []
            total_passed = 0
            total_failed = 0

            def safe_scan(scanner_func, res):
                try:
                    return scanner_func(res, scan_id)
                except Exception as e:
                    logger.error(f"Error executing scanner {scanner_func.__name__}: {e}")
                    return [], 0, 0

            for scan_func, res in [
                (s3_scanner.scan, inventory.s3_buckets),
                (iam_scanner.scan, inventory.iam_users),
                (ec2_scanner.scan_instances, inventory.ec2_instances),
                (ec2_scanner.scan_security_groups, inventory.security_groups),
                (rds_scanner.scan, inventory.rds_instances),
                (cloudtrail_scanner.scan, inventory.cloudtrails)
            ]:
                f_res, p, f = safe_scan(scan_func, res)
                findings.extend(f_res)
                total_passed += p
                total_failed += f

            # 5. Deduplicate Findings
            unique_findings = {}
            for finding in findings:
                key = f"{finding.rule_id}_{finding.resource_id}"
                if key not in unique_findings:
                    unique_findings[key] = finding
            final_findings = list(unique_findings.values())
            
            # Enrich findings with risk scores
            for finding in final_findings:
                calculate_finding_risk(finding)
                
            final_findings.sort(key=lambda x: (x.risk_score or 0), reverse=True)

            # Persist findings
            findings_data = [f.model_dump() for f in final_findings]
            # Rename finding_id to id for db
            for fd in findings_data:
                fd["id"] = fd.pop("finding_id")
            finding_repo.bulk_create(db, scan_id, findings_data)

            # 6. Build Summary & Risk Engine
            checks_summary = CheckSummary(
                passed=total_passed,
                failed=total_failed,
                errors=0,
                skipped=0
            )
            
            security_score, rating = calculate_security_score(final_findings, checks_summary)
            category_scores = calculate_category_scores(final_findings)

            # Persist category scores
            cat_score_records = []
            for cat, data in category_scores.items():
                cat_score_records.append(CategoryScore(
                    scan_id=scan_id,
                    category=cat,
                    score=data["score"],
                    status=data["status"],
                    finding_count=data["findings"],
                    critical_count=data.get("critical", 0),
                    high_count=data.get("high", 0)
                ))
            if cat_score_records:
                db.bulk_save_objects(cat_score_records)

            # Update scan record
            scan_repo.update_scan_metrics(
                db=db,
                scan_id=scan_id,
                resources_scanned=total_resources,
                checks_attempted=total_passed + total_failed,
                checks_completed=total_passed + total_failed,
                checks_failed=total_failed,
                security_score=security_score,
                security_rating=rating
            )
            scan_repo.complete_scan(db, scan_id, status="COMPLETED")
            db.commit()

            logger.info(f"Scan {scan_id} completed successfully.")
            
            # Reconstruct the schema response (or return the raw DB object and let FastAPI serialize)
            # For compatibility with existing API tests/schema, we rebuild the response.
            summary = ScanSummary(
                resources_scanned=total_resources,
                findings=len(final_findings),
                critical=sum(1 for f in final_findings if f.severity == "CRITICAL"),
                high=sum(1 for f in final_findings if f.severity == "HIGH"),
                medium=sum(1 for f in final_findings if f.severity == "MEDIUM"),
                low=sum(1 for f in final_findings if f.severity == "LOW"),
                info=sum(1 for f in final_findings if f.severity == "INFO"),
                checks_attempted=total_passed + total_failed,
                checks_completed=total_passed + total_failed,
                checks_failed=total_failed
            )

            return ScanResult(
                scan_id=scan_id,
                status="COMPLETED",
                account_id=account_id,
                security_score=security_score,
                rating=rating,
                summary=summary,
                checks_summary=checks_summary,
                category_scores=category_scores,
                findings=final_findings
            )
            
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            scan_repo.complete_scan(db, scan_id, status="FAILED")
            db.commit()
            raise HTTPException(status_code=500, detail=str(e))

    def run_workspace_scan(self, db: Session, workspace_id: str, aws_connection_id: str = None, scan_id: str = None):
        from app.scanner.deterministic_scanner import deterministic_scanner
        return deterministic_scanner.run_workspace_scan(db, workspace_id, aws_connection_id, scan_id)

scan_manager = ScanManager()
