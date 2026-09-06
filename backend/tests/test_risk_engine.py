from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.findings.schemas import Finding, CheckSummary, FindingStatus
from app.risk.schemas import Priority
from app.risk.scoring import calculate_finding_risk
from app.risk.engine import calculate_security_score, calculate_category_scores
import uuid

client = TestClient(app)

def create_mock_finding(rule_id, severity, category="network"):
    # Need to pass an enum for severity in the schema
    from app.findings.schemas import Severity
    
    # helper map to get enum value
    sev_enum = getattr(Severity, severity)

    finding = Finding(
        finding_id=str(uuid.uuid4()),
        rule_id=rule_id,
        title="Mock Finding",
        severity=sev_enum,
        service="mock",
        resource_id="mock-1",
        resource_name="mock-resource",
        region="us-east-1",
        category=category,
        description="...",
        evidence={},
        recommendation="..."
    )
    return finding

def test_finding_risk_score():
    f1 = create_mock_finding("SSH_OPEN_TO_WORLD", "CRITICAL")
    calculate_finding_risk(f1)
    # Base 90 + 5 (Internet exposed) = 95
    assert f1.risk_score == 95
    assert f1.priority == "P1"
    assert "Internet exposed" in f1.risk_factors

    f2 = create_mock_finding("EC2_PUBLIC_IP", "MEDIUM")
    calculate_finding_risk(f2)
    # Base 45 + 5 (Internet exposed) = 50
    assert f2.risk_score == 50
    assert f2.priority == "P3"

def test_overall_security_score():
    checks = CheckSummary(passed=10, failed=2, errors=0, skipped=0)
    
    # Two critical findings
    f1 = create_mock_finding("SSH", "CRITICAL")
    f2 = create_mock_finding("RDP", "CRITICAL")
    
    score, rating = calculate_security_score([f1, f2], checks)
    # 2 CRITICAL = 20 penalty. 100 - 20 = 80
    assert score == 80
    assert rating == "Good"
    
    # Test Caps
    # 5 Criticals = 50 penalty. But cap is 40.
    findings = [create_mock_finding("MOCK", "CRITICAL") for _ in range(5)]
    score_cap, rating_cap = calculate_security_score(findings, checks)
    # 100 - 40 = 60
    assert score_cap == 60
    assert rating_cap == "Needs Attention"

def test_empty_account_score():
    checks = CheckSummary(passed=0, failed=0, errors=0, skipped=0)
    score, rating = calculate_security_score([], checks)
    assert score is None
    assert rating == "Not Scored"

def test_category_scores():
    f1 = create_mock_finding("MOCK", "CRITICAL", category="identity")
    f2 = create_mock_finding("MOCK", "HIGH", category="identity")
    
    scores = calculate_category_scores([f1, f2])
    assert "IDENTITY" in scores
    # 10 + 6 penalty = 16. 100 - 16 = 84
    assert scores["IDENTITY"]["score"] == 84
    assert scores["IDENTITY"]["findings"] == 2
    assert scores["IDENTITY"]["status"] == "GOOD"
