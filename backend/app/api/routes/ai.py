from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, Optional

from app.core.database import get_db
from app.api.deps import get_current_user_optional
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.finding import Finding
from app.models.scan import Scan
from app.ai.schemas import FindingExplanation, ScanAISummary, CopilotRequest, CopilotResponse
from app.ai.service import ai_service
from app.ai.exceptions import (
    AIError,
    AIProviderUnavailableError,
    AIRateLimitError,
    AIAnalysisTimeoutError,
    AIResponseFormatError,
)
from app.repositories.finding import finding_repo
from app.repositories.scan import scan_repo

router = APIRouter()


def _check_workspace_access(db: Session, workspace_id: str, user: User) -> bool:
    """Verify if user is the workspace owner or an authorized member."""
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        return False
    if ws.owner_id == user.id:
        return True
    membership = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user.id)
        .first()
    )
    return membership is not None


@router.post("/findings/{finding_id}/explain", response_model=FindingExplanation)
async def explain_finding_endpoint(
    finding_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> Any:
    """
    Generate an advisory AI explanation for a specific deterministic finding.
    Guarantees no modifications to security score, finding severity, or risk priority.
    """
    finding = finding_repo.get(db, finding_id)
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    # Anti-IDOR enforcement
    if current_user and finding.workspace_id:
        if not _check_workspace_access(db, finding.workspace_id, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to view this finding",
            )

    try:
        explanation = await ai_service.explain_finding(db, finding_id)
        return explanation
    except AIRateLimitError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except AIAnalysisTimeoutError as e:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(e))
    except AIResponseFormatError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except (AIProviderUnavailableError, AIError) as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.post("/scans/{scan_id}/summary", response_model=ScanAISummary)
async def summarize_scan_endpoint(
    scan_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> Any:
    """
    Generate an AI executive summary and recommended action plan for a completed scan.
    """
    scan = scan_repo.get(db, scan_id)
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    # Anti-IDOR enforcement
    if current_user and scan.workspace_id:
        if not _check_workspace_access(db, scan.workspace_id, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to view this scan",
            )

    try:
        summary = await ai_service.summarize_scan(db, scan_id)
        return summary
    except AIRateLimitError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except AIAnalysisTimeoutError as e:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(e))
    except AIResponseFormatError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except (AIProviderUnavailableError, AIError) as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.post("/chat", response_model=CopilotResponse)
async def chat_endpoint(
    request: CopilotRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> Any:
    """
    Interact with CloudGuard Copilot to explore scan results, ask security questions,
    and prioritize remediations grounded in real CloudGuard data.
    """
    if request.scan_id:
        scan = scan_repo.get(db, request.scan_id)
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
        if current_user and scan.workspace_id:
            if not _check_workspace_access(db, scan.workspace_id, current_user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: You do not have permission to access this scan context",
                )

    if request.workspace_id and current_user:
        if not _check_workspace_access(db, request.workspace_id, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to access this workspace context",
            )

    try:
        response = await ai_service.ask_copilot(
            db=db,
            message=request.message,
            scan_id=request.scan_id,
            history=request.history,
        )
        return response
    except AIRateLimitError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except AIAnalysisTimeoutError as e:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(e))
    except AIResponseFormatError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except (AIProviderUnavailableError, AIError) as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
