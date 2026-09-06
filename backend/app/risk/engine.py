from typing import List, Dict, Tuple, Optional
from app.findings.schemas import Finding, CheckSummary
from app.risk.schemas import CategoryScore
from app.risk.categories import map_category

# Penalty weights per finding
PENALTY_WEIGHTS = {
    "CRITICAL": 10,
    "HIGH": 6,
    "MEDIUM": 3,
    "LOW": 1,
    "INFO": 0
}

# Maximum penalty allowed per severity category to prevent a score hitting 0 just from 30 low findings
PENALTY_CAPS = {
    "CRITICAL": 40,
    "HIGH": 30,
    "MEDIUM": 20,
    "LOW": 10,
    "INFO": 0
}

def get_rating_label(score: int) -> str:
    if score >= 90:
        return "Excellent"
    elif score >= 75:
        return "Good"
    elif score >= 60:
        return "Needs Attention"
    elif score >= 40:
        return "High Risk"
    else:
        return "Critical Risk"

def calculate_security_score(findings: List[Finding], checks_summary: CheckSummary) -> Tuple[Optional[int], str]:
    """
    Calculates the overall security score from 0-100.
    Returns (score, rating).
    Returns (None, "Not Scored") if there is insufficient data.
    """
    total_checks = checks_summary.passed + checks_summary.failed + checks_summary.errors
    if total_checks == 0:
        return None, "Not Scored"

    # Sum raw penalties
    raw_penalties = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for finding in findings:
        sev = finding.severity.value
        raw_penalties[sev] += PENALTY_WEIGHTS.get(sev, 0)
        
    # Apply caps
    total_penalty = 0
    for sev, raw_penalty in raw_penalties.items():
        capped_penalty = min(raw_penalty, PENALTY_CAPS.get(sev, 0))
        total_penalty += capped_penalty
        
    score = 100 - total_penalty
    score = max(0, min(100, score))
    
    return score, get_rating_label(score)

def calculate_category_scores(findings: List[Finding]) -> Dict[str, dict]:
    """
    Groups findings into high-level categories and calculates their individual scores.
    """
    grouped: Dict[str, List[Finding]] = {}
    for finding in findings:
        cat = map_category(finding.category)
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(finding)
        
    category_scores = {}
    # If a category has no findings, it implies perfect score for that category *if* checks ran.
    # To keep simple for Part 5, we only score categories that have findings, or we assume 100 if none.
    # We will score based on the findings present.
    
    for cat, cat_findings in grouped.items():
        raw_penalties = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for f in cat_findings:
            sev = f.severity.value
            raw_penalties[sev] += PENALTY_WEIGHTS.get(sev, 0)
            
        total_penalty = 0
        for sev, raw_penalty in raw_penalties.items():
            total_penalty += min(raw_penalty, PENALTY_CAPS.get(sev, 0))
            
        score = max(0, min(100, 100 - total_penalty))
        
        status = "SECURE"
        if score < 40:
            status = "CRITICAL"
        elif score < 60:
            status = "HIGH_RISK"
        elif score < 75:
            status = "NEEDS_ATTENTION"
        elif score < 90:
            status = "GOOD"
            
        category_scores[cat] = CategoryScore(
            score=score,
            findings=len(cat_findings),
            critical=sum(1 for f in cat_findings if f.severity.value == "CRITICAL"),
            high=sum(1 for f in cat_findings if f.severity.value == "HIGH"),
            status=status
        ).dict()
        
    return category_scores
