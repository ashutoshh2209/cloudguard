from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any

from app.database.dependencies import get_db
from app.ai.schemas import FindingExplanation, ScanAISummary, CopilotRequest, CopilotResponse
from app.ai.service import explain_finding, summarize_scan, ask_copilot
from app.ai.exceptions import AIError

router = APIRouter()

@router.post("/findings/{finding_id}/explain", response_model=FindingExplanation)
async def explain_finding_endpoint(finding_id: str, db: Session = Depends(get_db)) -> Any:
    """
    Generate an AI explanation for a specific security finding.
    """
    try:
        explanation = await explain_finding(db, finding_id)
        return explanation
    except AIError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.post("/scans/{scan_id}/summary", response_model=ScanAISummary)
async def summarize_scan_endpoint(scan_id: str, db: Session = Depends(get_db)) -> Any:
    """
    Generate an AI summary of a complete scan.
    """
    try:
        summary = await summarize_scan(db, scan_id)
        return summary
    except AIError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.post("/chat", response_model=CopilotResponse)
async def chat_endpoint(request: CopilotRequest, db: Session = Depends(get_db)) -> Any:
    """
    Ask the Security Copilot a question.
    """
    try:
        response_text = await ask_copilot(db, request.message, request.scan_id, request.history)
        return CopilotResponse(answer=response_text)
    except AIError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
