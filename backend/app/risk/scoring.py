from typing import Any
from app.risk.service import (
    SEVERITY_BASE_SCORES,
    RiskEngineService,
)

def calculate_finding_risk(finding: Any) -> None:
    """
    Calculates the risk score and priority for a single finding.
    Mutates the finding in place.
    """
    RiskEngineService.calculate_finding_risk(finding)
