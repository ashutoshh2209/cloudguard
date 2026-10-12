from typing import Optional, List, Dict, Any, Tuple
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.logging import logger
from app.models.scan import Scan
from app.models.check_result import CheckResult
from app.models.finding import Finding
from app.models.category_score import CategoryScore
from app.models.resource import CloudResource
from app.models.workspace import Workspace
from app.models.aws_connection import AWSConnection
from app.rules.base import SecurityRule, RuleEvaluationResult, CheckStatus
from app.rules.registry import RuleRegistry
from app.risk.service import calculate_finding_risk, calculate_security_score, calculate_category_scores
import app.rules # Trigger all rule registrations

class DeterministicScannerService:
    """
    Deterministic Security Scanner Engine.
    Evaluates security rules strictly deterministically against discovered cloud resources.
    Generates structured check results (PASS, FAIL, ERROR, NOT_APPLICABLE) and findings.
    Zero AI - 100% deterministic rule logic.
    """

    def get_applicable_rules_for_resource(self, resource: CloudResource) -> List[SecurityRule]:
        """
        Determines applicable registered rules for a given discovered resource.
        """
        service = (resource.service or "").lower()
        res_type = (resource.resource_type or "").lower()

        candidate_rules = RuleRegistry.get_rules_for_service(service)
        applicable: List[SecurityRule] = []

        for rule in candidate_rules:
            rule_res_type = getattr(rule, "resource_type", "").lower()
            
            # Service and type matching
            if service == "s3":
                applicable.append(rule)
            elif service in ("ec2", "security_group", "security_groups"):
                # Distinguish security groups from instances
                is_sg_resource = any(t in res_type for t in ("security-group", "security_group"))
                is_sg_rule = any(t in rule_res_type for t in ("security-group", "security_group"))
                
                if is_sg_resource and is_sg_rule:
                    applicable.append(rule)
                elif not is_sg_resource and not is_sg_rule:
                    applicable.append(rule)
            elif service == "iam":
                applicable.append(rule)
            elif service == "rds":
                applicable.append(rule)
            elif service == "cloudtrail":
                applicable.append(rule)
            else:
                applicable.append(rule)

        return applicable

    def run_workspace_scan(
        self,
        db: Session,
        workspace_id: str,
        aws_connection_id: Optional[str] = None,
        scan_id: Optional[str] = None,
    ) -> Scan:
        """
        Executes a deterministic security assessment for all discovered resources in a workspace.
        Creates and persists structured CheckResult records and Findings.
        """
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

        # Resolve AWS connection
        conn_query = db.query(AWSConnection).filter(AWSConnection.workspace_id == workspace_id)
        if aws_connection_id:
            connection = conn_query.filter(AWSConnection.id == aws_connection_id).first()
        else:
            connection = conn_query.order_by(AWSConnection.created_at.desc()).first()

        resolved_conn_id = connection.id if connection else None

        # 1. Initialize Scan record
        now = datetime.now(timezone.utc)
        if scan_id:
            scan = db.query(Scan).filter(Scan.id == scan_id).first()
            if not scan:
                scan = Scan(
                    id=scan_id,
                    workspace_id=workspace_id,
                    aws_connection_id=resolved_conn_id,
                    status="RUNNING",
                    started_at=now,
                )
                db.add(scan)
            else:
                scan.status = "RUNNING"
                scan.started_at = now
        else:
            scan = Scan(
                workspace_id=workspace_id,
                aws_connection_id=resolved_conn_id,
                status="RUNNING",
                started_at=now,
            )
            db.add(scan)
        
        db.commit()
        db.refresh(scan)

        try:
            logger.info(f"Starting deterministic scan {scan.id} for workspace {workspace_id}...")

            # 2. Query discovered resources
            resource_query = db.query(CloudResource).filter(CloudResource.workspace_id == workspace_id)
            if resolved_conn_id:
                resource_query = resource_query.filter(CloudResource.aws_connection_id == resolved_conn_id)
            
            resources = resource_query.all()

            # If no resources found for workspace, check if there are legacy resources associated with connection
            if not resources and resolved_conn_id:
                resources = db.query(CloudResource).filter(CloudResource.aws_connection_id == resolved_conn_id).all()

            resources_count = len(resources)
            checks_attempted = 0
            checks_completed = 0
            checks_passed = 0
            checks_failed = 0
            checks_errored = 0

            check_records: List[CheckResult] = []
            finding_records: List[Finding] = []

            # 3. Deterministically evaluate rules on every resource
            for resource in resources:
                applicable_rules = self.get_applicable_rules_for_resource(resource)

                for rule in applicable_rules:
                    checks_attempted += 1
                    evaluation_now = datetime.now(timezone.utc)

                    # Evaluate rule deterministically
                    eval_result: RuleEvaluationResult = rule.evaluate_check(resource)

                    check_record = CheckResult(
                        scan_id=scan.id,
                        resource_id=resource.resource_id,
                        rule_id=rule.rule_id,
                        status=eval_result.status.value,
                        message=eval_result.message,
                        error_message=eval_result.message if eval_result.status == CheckStatus.ERROR else None,
                        recommendation=eval_result.recommendation or rule.recommendation,
                        evidence=eval_result.evidence,
                        checked_at=evaluation_now,
                    )
                    check_records.append(check_record)

                    if eval_result.status == CheckStatus.PASS:
                        checks_passed += 1
                        checks_completed += 1
                    elif eval_result.status == CheckStatus.FAIL:
                        checks_failed += 1
                        checks_completed += 1

                        # Generate finding for failed check
                        finding = Finding(
                            scan_id=scan.id,
                            workspace_id=workspace_id,
                            resource_id=resource.resource_id,
                            rule_id=rule.rule_id,
                            title=rule.title,
                            description=rule.description,
                            severity=str(getattr(rule.severity, "value", rule.severity)),
                            category=rule.category,
                            service=resource.service,
                            region=resource.region,
                            status="OPEN",
                            recommendation=eval_result.recommendation or rule.recommendation,
                            evidence=eval_result.evidence,
                            created_at=evaluation_now,
                            detected_at=evaluation_now,
                        )
                        calculate_finding_risk(finding)
                        finding_records.append(finding)
                    elif eval_result.status == CheckStatus.ERROR:
                        checks_errored += 1
                        # Strictly do NOT treat ERROR as PASS
                        logger.warning(
                            f"Check error on rule {rule.rule_id} for resource {resource.resource_id}: {eval_result.message}"
                        )
                    elif eval_result.status == CheckStatus.NOT_APPLICABLE:
                        pass

            # 4. Deduplicate findings by (rule_id, resource_id) and sort by risk
            seen_finding_keys = set()
            unique_findings: List[Finding] = []
            for f in finding_records:
                key = (f.rule_id, f.resource_id)
                if key not in seen_finding_keys:
                    seen_finding_keys.add(key)
                    unique_findings.append(f)
            finding_records = unique_findings
            finding_records.sort(key=lambda x: (x.risk_score or 0), reverse=True)

            # 5. Calculate overall score and category breakdown using Risk Engine
            checks_summary = {
                "passed": checks_passed,
                "failed": checks_failed,
                "errors": checks_errored,
            }
            security_score, security_rating = calculate_security_score(finding_records, checks_summary)
            category_scores = calculate_category_scores(finding_records)

            cat_score_records: List[CategoryScore] = []
            for cat, data in category_scores.items():
                cat_score_records.append(CategoryScore(
                    scan_id=scan.id,
                    category=cat,
                    score=data["score"],
                    status=data["status"],
                    finding_count=data["findings"],
                    critical_count=data.get("critical", 0),
                    high_count=data.get("high", 0),
                ))

            # 6. Persist check results, findings, and category scores
            if check_records:
                db.bulk_save_objects(check_records)
            if finding_records:
                db.bulk_save_objects(finding_records)
            if cat_score_records:
                db.bulk_save_objects(cat_score_records)

            # 7. Determine scan completion status
            completion_time = datetime.now(timezone.utc)
            if checks_errored > 0 and (checks_passed + checks_failed) > 0:
                final_status = "PARTIAL"
            elif checks_errored > 0 and (checks_passed + checks_failed) == 0:
                final_status = "FAILED"
            else:
                final_status = "COMPLETED"

            # 8. Update scan metrics
            scan.status = final_status
            scan.completed_at = completion_time
            scan.resources_scanned = resources_count
            scan.checks_attempted = checks_attempted
            scan.checks_completed = checks_completed
            scan.checks_passed = checks_passed
            scan.checks_failed = checks_failed
            scan.checks_errored = checks_errored
            scan.coverage_percentage = 100 if checks_attempted > 0 else 0
            scan.security_score = security_score
            scan.security_rating = security_rating

            db.commit()
            db.refresh(scan)

            logger.info(
                f"Scan {scan.id} finished with status {final_status}. "
                f"Scanned: {resources_count}, Attempted: {checks_attempted}, "
                f"Passed: {checks_passed}, Failed: {checks_failed}, Errored: {checks_errored}."
            )
            return scan

        except Exception as e:
            logger.error(f"Scan {scan.id} failed with unhandled exception: {e}")
            scan.status = "FAILED"
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(scan)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Scan execution failed: {str(e)}")

deterministic_scanner = DeterministicScannerService()
