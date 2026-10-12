from typing import List, Dict, Tuple, Optional, Any, Union
from app.findings.schemas import Finding, CheckSummary
from app.risk.schemas import CategoryScore
from app.risk.categories import map_category
from app.risk.service import (
    PENALTY_WEIGHTS,
    PENALTY_CAPS,
    get_rating_label,
    RiskEngineService,
    risk_engine,
)

def calculate_security_score(
    findings: List[Any],
    checks_summary: Union[CheckSummary, Dict[str, Any], Any]
) -> Tuple[Optional[int], str]:
    """
    Calculates the overall security score from 0-100.
    Returns (score, rating).
    Returns (None, 'Not Scored') if there is insufficient data.
    """
    return RiskEngineService.calculate_security_score(findings, checks_summary)

def calculate_category_scores(findings: List[Any]) -> Dict[str, dict]:
    """
    Groups findings into high-level categories and calculates their individual scores.
    """
    return RiskEngineService.calculate_category_scores(findings)
