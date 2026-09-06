from app.findings.schemas import Finding
from app.risk.schemas import Priority
from typing import List

# Base severity scores
SEVERITY_BASE_SCORES = {
    "CRITICAL": 90,
    "HIGH": 70,
    "MEDIUM": 45,
    "LOW": 20,
    "INFO": 5
}

def calculate_finding_risk(finding: Finding) -> None:
    """
    Calculates the risk score and priority for a single finding.
    Mutates the finding in place.
    """
    base_score = SEVERITY_BASE_SCORES.get(finding.severity.value, 0)
    modifiers = 0
    factors = []

    # Contextual Modifiers based on rule_id or evidence
    # Internet exposed
    if "OPEN_TO_WORLD" in finding.rule_id or finding.rule_id == "EC2_PUBLIC_IP":
        modifiers += 5
        factors.append("Internet exposed")

    # Identity related
    if finding.category == "identity" or "IAM" in finding.rule_id:
        modifiers += 5
        factors.append("Identity-related finding")

    # Database exposed
    if finding.category == "database":
        modifiers += 5
        factors.append("Database exposed")

    # Storage public access
    if finding.rule_id == "S3_PUBLIC_ACCESS":
        modifiers += 5
        factors.append("Publicly accessible storage")

    # Logging missing
    if finding.rule_id == "CLOUDTRAIL_DISABLED":
        modifiers += 3
        factors.append("No logging / monitoring")

    factors.insert(0, f"{finding.severity.value.capitalize()} severity")

    # Cap at 100, Min at 0
    final_score = max(0, min(100, base_score + modifiers))
    
    finding.risk_score = final_score
    finding.risk_factors = factors
    
    # Map to priority
    if final_score >= 90:
        finding.priority = Priority.P1.value
    elif final_score >= 70:
        finding.priority = Priority.P2.value
    elif final_score >= 40:
        finding.priority = Priority.P3.value
    else:
        finding.priority = Priority.P4.value
