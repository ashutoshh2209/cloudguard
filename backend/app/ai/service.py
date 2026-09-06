import json
import logging
from sqlalchemy.orm import Session
from app.ai.provider import get_ai_provider
from app.ai.prompts import FINDING_EXPLANATION_PROMPT_V1, SCAN_SUMMARY_PROMPT_V1, COPILOT_PROMPT_V1
from app.ai.schemas import FindingExplanation, ScanAISummary, CopilotMessage
from app.repositories.finding import finding_repo
from app.repositories.scan import scan_repo
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Very basic sanitization
def sanitize_aws_string(value: str | None) -> str:
    if not value:
        return ""
    # In a real system, you'd redact AWS access keys (AKIA...), secrets, IPs, etc.
    # For now, we trust the deterministic scanner hasn't stored raw secrets in the DB.
    return str(value)

async def explain_finding(db: Session, finding_id: str) -> FindingExplanation:
    finding = finding_repo.get(db, finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    prompt = FINDING_EXPLANATION_PROMPT_V1.format(
        title=sanitize_aws_string(finding.title),
        severity=sanitize_aws_string(finding.severity),
        risk_score=str(finding.risk_score),
        category=sanitize_aws_string(finding.category),
        resource_id=sanitize_aws_string(finding.resource_id),
        description=sanitize_aws_string(finding.description),
        recommendation=sanitize_aws_string(finding.recommendation)
    )

    provider = get_ai_provider()
    explanation = await provider.generate_structured(prompt, FindingExplanation)
    return explanation


async def summarize_scan(db: Session, scan_id: str) -> ScanAISummary:
    scan = scan_repo.get(db, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
        
    findings = finding_repo.list_findings(db, scan_id=scan_id, limit=1000)
    
    # Calculate finding counts
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    top_finding_strs = []
    
    # Sort findings by risk_score desc
    findings_sorted = sorted(findings, key=lambda x: x.risk_score or 0, reverse=True)
    
    for idx, f in enumerate(findings_sorted):
        if f.severity in counts:
            counts[f.severity] += 1
        if idx < 10:  # Include top 10 for AI context
            top_finding_strs.append(f"- {f.severity} ({f.risk_score}): {f.title} on {f.resource_id}")

    counts_str = json.dumps(counts, indent=2)
    cat_scores_str = json.dumps([{"category": cs.category, "score": cs.score} for cs in scan.category_scores], indent=2)
    top_findings_str = "\n".join(top_finding_strs) if top_finding_strs else "No findings."

    prompt = SCAN_SUMMARY_PROMPT_V1.format(
        status=sanitize_aws_string(scan.status),
        security_score=str(scan.security_score),
        security_rating=sanitize_aws_string(scan.security_rating),
        resources_scanned=str(scan.resources_scanned),
        coverage_percentage=str(scan.coverage_percentage),
        finding_counts=counts_str,
        category_scores=cat_scores_str,
        top_findings=top_findings_str
    )

    provider = get_ai_provider()
    summary = await provider.generate_structured(prompt, ScanAISummary)
    return summary


async def ask_copilot(db: Session, message: str, scan_id: str | None, history: list[CopilotMessage]) -> str:
    scan_context = "No specific scan selected."
    if scan_id:
        scan = scan_repo.get(db, scan_id)
        if scan:
            scan_context = f"Scan ID: {scan_id}\nScore: {scan.security_score}\nRating: {scan.security_rating}\nStatus: {scan.status}"
            
            # Fetch summary finding counts
            findings = finding_repo.list_findings(db, scan_id=scan_id, limit=500)
            counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
            top_5 = []
            findings_sorted = sorted(findings, key=lambda x: x.risk_score or 0, reverse=True)
            for i, f in enumerate(findings_sorted):
                if f.severity in counts:
                    counts[f.severity] += 1
                if i < 5:
                    top_5.append(f"{f.severity}: {f.title} (Resource: {f.resource_id})")
                    
            scan_context += f"\nFindings Summary: {json.dumps(counts)}"
            scan_context += "\nTop 5 Risks:\n" + "\n".join(top_5)

    system_prompt = COPILOT_PROMPT_V1.format(scan_context=scan_context)
    
    # Prepare messages
    api_messages = [{"role": msg.role, "content": msg.content} for msg in history[-10:]] # Keep last 10 messages
    api_messages.append({"role": "user", "content": message})
    
    provider = get_ai_provider()
    response_text = await provider.chat(system_prompt, api_messages)
    return response_text
