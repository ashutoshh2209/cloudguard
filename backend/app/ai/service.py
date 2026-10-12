import json
import logging
import re
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.ai.provider import get_ai_provider
from app.ai.prompts import (
    FINDING_EXPLANATION_PROMPT_V1,
    SCAN_SUMMARY_PROMPT_V1,
    COPILOT_PROMPT_V1,
)
from app.ai.schemas import FindingExplanation, ScanAISummary, CopilotMessage, CopilotResponse
from app.ai.exceptions import (
    AIError,
    AIProviderUnavailableError,
    AIRateLimitError,
    AIAnalysisTimeoutError,
    AIResponseFormatError,
)
from app.repositories.finding import finding_repo
from app.repositories.scan import scan_repo
from app.models.finding import Finding
from app.models.scan import Scan

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. CREDENTIAL SANITIZER & PROMPT INJECTION SHIELD
# ==============================================================================

SENSITIVE_PATTERNS = [
    (re.compile(r'(?i)(aws_secret_access_key|secret_key|secretkey|secret|password|passwd|pwd|token|jwt|session_token)\s*[:=]\s*["\']?([^"\'\s]+)["\']?'), r'\1=***REDACTED***'),
    (re.compile(r'eyJ[a-zA-Z0-9_\-]{15,}\.[a-zA-Z0-9_\-]{15,}\.[a-zA-Z0-9_\-]+'), r'***REDACTED_JWT***'),
    (re.compile(r'(?i)(aws_session_token)\s*[:=]\s*["\']?([^"\'\s]+)["\']?'), r'\1=***REDACTED***'),
    (re.compile(r'(?i)(access_key_id|accesskey|access_key)\s*[:=]\s*["\']?([A-Z0-9]{20})["\']?'), r'\1=***REDACTED***'),
]

def sanitize_untrusted_input(val: Any) -> str:
    """
    Sanitize input by stripping credentials, tokens, secrets,
    and neutralizing prompt-injection patterns before forwarding to AI models.
    """
    if val is None:
        return ""
    text = str(val)
    for pattern, repl in SENSITIVE_PATTERNS:
        text = pattern.sub(repl, text)
    # Neutralize prompt injection delimiter breaks
    text = text.replace("```", "'''").replace("</UNTRUSTED_RESOURCE_DATA>", "")
    return text.strip()


# ==============================================================================
# 2. AI SERVICE IMPLEMENTATION
# ==============================================================================

class AIService:
    @staticmethod
    async def explain_finding(db: Session, finding_id: str) -> FindingExplanation:
        """
        Explain a deterministic finding without altering its severity or scores.
        """
        finding = finding_repo.get(db, finding_id)
        if not finding:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

        prompt = FINDING_EXPLANATION_PROMPT_V1.format(
            title=sanitize_untrusted_input(finding.title),
            severity=sanitize_untrusted_input(finding.severity),
            risk_score=sanitize_untrusted_input(finding.risk_score),
            category=sanitize_untrusted_input(finding.category),
            resource_id=sanitize_untrusted_input(finding.resource_id),
            description=sanitize_untrusted_input(finding.description),
            recommendation=sanitize_untrusted_input(finding.recommendation),
        )

        provider = get_ai_provider()
        explanation = await provider.generate_structured(prompt, FindingExplanation)
        return explanation

    @staticmethod
    async def summarize_scan(db: Session, scan_id: str) -> ScanAISummary:
        """
        Provide an executive summary of a completed scan using real persisted metrics.
        """
        scan = scan_repo.get(db, scan_id)
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
            
        findings = finding_repo.list_findings(db, scan_id=scan_id, limit=1000)
        
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        top_finding_lines = []
        
        findings_sorted = sorted(findings, key=lambda x: x.risk_score or 0, reverse=True)
        for idx, f in enumerate(findings_sorted):
            sev = (f.severity or "INFO").upper()
            if sev in counts:
                counts[sev] += 1
            if idx < 10:
                clean_title = sanitize_untrusted_input(f.title)
                clean_res = sanitize_untrusted_input(f.resource_id)
                top_finding_lines.append(f"- [{sev}] (Risk {f.risk_score}): {clean_title} on {clean_res}")

        cat_scores_list = []
        for cs in (scan.category_scores or []):
            cat_scores_list.append({
                "category": sanitize_untrusted_input(cs.category),
                "score": cs.score,
                "status": cs.status,
            })

        prompt = SCAN_SUMMARY_PROMPT_V1.format(
            status=sanitize_untrusted_input(scan.status),
            security_score=str(scan.security_score) if scan.security_score is not None else "Not Scored",
            security_rating=sanitize_untrusted_input(scan.security_rating or "N/A"),
            resources_scanned=str(scan.resources_scanned or 0),
            coverage_percentage=str(scan.coverage_percentage or 0.0),
            finding_counts=json.dumps(counts, indent=2),
            category_scores=json.dumps(cat_scores_list, indent=2),
            top_findings="\n".join(top_finding_lines) if top_finding_lines else "No findings identified.",
        )

        provider = get_ai_provider()
        summary = await provider.generate_structured(prompt, ScanAISummary)
        return summary

    @staticmethod
    async def ask_copilot(
        db: Session,
        message: str,
        scan_id: Optional[str] = None,
        history: Optional[List[CopilotMessage]] = None,
    ) -> CopilotResponse:
        """
        Conversational Copilot grounded strictly in real CloudGuard scan metrics.
        """
        scan_context = "No specific scan selected."
        resolved_scan_id = None

        if scan_id:
            scan = scan_repo.get(db, scan_id)
            if scan:
                resolved_scan_id = scan.id
                scan_context = (
                    f"Scan ID: {scan.id}\n"
                    f"Security Score: {scan.security_score}/100\n"
                    f"Security Rating: {scan.security_rating}\n"
                    f"Scan Status: {scan.status}\n"
                    f"Resources Evaluated: {scan.resources_scanned}\n"
                )
                
                findings = finding_repo.list_findings(db, scan_id=scan.id, limit=500)
                counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
                top_5 = []
                findings_sorted = sorted(findings, key=lambda x: x.risk_score or 0, reverse=True)
                for i, f in enumerate(findings_sorted):
                    sev = (f.severity or "INFO").upper()
                    if sev in counts:
                        counts[sev] += 1
                    if i < 5:
                        top_5.append(f"- [{sev}] {sanitize_untrusted_input(f.title)} ({sanitize_untrusted_input(f.resource_id)})")
                        
                scan_context += f"Findings Distribution: {json.dumps(counts)}\n"
                scan_context += "Top Identified Risks:\n" + ("\n".join(top_5) if top_5 else "None")

        system_prompt = COPILOT_PROMPT_V1.format(scan_context=scan_context)
        
        api_messages = []
        if history:
            for msg in history[-10:]:
                api_messages.append({"role": msg.role, "content": sanitize_untrusted_input(msg.content)})
        api_messages.append({"role": "user", "content": sanitize_untrusted_input(message)})
        
        provider = get_ai_provider()
        response_text = await provider.chat(system_prompt, api_messages)
        
        return CopilotResponse(
            answer=response_text,
            provider=getattr(provider, 'name', 'mock'),
            scan_id=resolved_scan_id,
            status="success",
        )

ai_service = AIService()

# Backward-compatible convenience functions
async def explain_finding(db: Session, finding_id: str) -> FindingExplanation:
    return await ai_service.explain_finding(db, finding_id)

async def summarize_scan(db: Session, scan_id: str) -> ScanAISummary:
    return await ai_service.summarize_scan(db, scan_id)

async def ask_copilot(db: Session, message: str, scan_id: Optional[str] = None, history: Optional[List[CopilotMessage]] = None) -> str:
    res = await ai_service.ask_copilot(db, message, scan_id, history)
    return res.answer
