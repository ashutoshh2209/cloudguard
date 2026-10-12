from typing import List, Dict, Any, Tuple, Optional, Union
from app.findings.schemas import CheckSummary
from app.risk.schemas import Priority, CategoryScore
from app.risk.categories import map_category, CATEGORY_MAPPINGS

# Base severity scores for individual findings
SEVERITY_BASE_SCORES = {
    "CRITICAL": 90,
    "HIGH": 70,
    "MEDIUM": 45,
    "LOW": 20,
    "INFO": 5,
}

# Penalty weights per finding in overall/category calculations
PENALTY_WEIGHTS = {
    "CRITICAL": 10,
    "HIGH": 6,
    "MEDIUM": 3,
    "LOW": 1,
    "INFO": 0,
}

# Maximum penalty allowed per severity category to prevent score dropping to 0 from low-severity findings alone
PENALTY_CAPS = {
    "CRITICAL": 40,
    "HIGH": 30,
    "MEDIUM": 20,
    "LOW": 10,
    "INFO": 0,
}


def normalize_severity(severity_raw: Any) -> str:
    """Safely normalizes severity values from strings, enums, or dict keys."""
    if hasattr(severity_raw, "value"):
        severity_raw = severity_raw.value
    return str(severity_raw or "INFO").upper()


def get_rating_label(score: Optional[int]) -> str:
    """
    Returns the human-readable rating label for an overall score.
    Returns 'Not Scored' if score is None.
    """
    if score is None:
        return "Not Scored"
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


class RiskEngineService:
    """
    Dedicated, strictly deterministic Risk Engine service.
    Single source of truth for:
    - Finding risk score and priority
    - Overall security score and rating
    - Category breakdown scores and status
    Zero AI - strictly reproducible scoring.
    """

    @staticmethod
    def calculate_finding_risk(finding: Any) -> None:
        """
        Calculates the risk score and priority for a single finding.
        Mutates finding in place (supports Pydantic schemas, SQLAlchemy models, and dicts).
        """
        # Read severity safely
        if isinstance(finding, dict):
            sev_raw = finding.get("severity")
            rule_id = str(finding.get("rule_id", ""))
            category = str(finding.get("category", "")).lower()
        else:
            sev_raw = getattr(finding, "severity", "INFO")
            rule_id = str(getattr(finding, "rule_id", ""))
            category = str(getattr(finding, "category", "")).lower()

        sev = normalize_severity(sev_raw)
        base_score = SEVERITY_BASE_SCORES.get(sev, 5)
        modifiers = 0
        factors: List[str] = []

        # Contextual Modifiers based on rule_id or evidence
        # Internet exposed
        if "OPEN_TO_WORLD" in rule_id or rule_id == "EC2_PUBLIC_IP":
            modifiers += 5
            factors.append("Internet exposed")

        # Identity related
        if category == "identity" or "IAM" in rule_id:
            modifiers += 5
            factors.append("Identity-related finding")

        # Database exposed
        if category == "database":
            modifiers += 5
            factors.append("Database exposed")

        # Storage public access
        if rule_id == "S3_PUBLIC_ACCESS":
            modifiers += 5
            factors.append("Publicly accessible storage")

        # Logging missing
        if rule_id == "CLOUDTRAIL_DISABLED":
            modifiers += 3
            factors.append("No logging / monitoring")

        factors.insert(0, f"{sev.capitalize()} severity")

        final_score = max(0, min(100, base_score + modifiers))

        # Map to priority
        if final_score >= 90:
            priority = Priority.P1.value
        elif final_score >= 70:
            priority = Priority.P2.value
        elif final_score >= 40:
            priority = Priority.P3.value
        else:
            priority = Priority.P4.value

        # Apply to finding
        if isinstance(finding, dict):
            finding["risk_score"] = final_score
            finding["risk_factors"] = factors
            finding["priority"] = priority
        else:
            finding.risk_score = final_score
            finding.risk_factors = factors
            finding.priority = priority

    @staticmethod
    def calculate_security_score(
        findings: List[Any],
        checks_summary: Union[CheckSummary, Dict[str, Any], Any],
    ) -> Tuple[Optional[int], str]:
        """
        Calculates the overall security score from 0-100.
        Returns (score, rating).
        Returns (None, 'Not Scored') if there are zero checks or scannable data.
        Never returns 0 or 100 arbitrarily when unscored.
        """
        if checks_summary is None:
            return None, "Not Scored"

        if isinstance(checks_summary, dict):
            passed = checks_summary.get("passed", 0)
            failed = checks_summary.get("failed", 0)
            errors = checks_summary.get("errors", 0)
        else:
            passed = getattr(checks_summary, "passed", 0)
            failed = getattr(checks_summary, "failed", 0)
            errors = getattr(checks_summary, "errors", 0)

        total_checks = passed + failed + errors
        if total_checks == 0:
            return None, "Not Scored"

        # Sum raw penalties
        raw_penalties = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for finding in findings:
            if isinstance(finding, dict):
                sev_raw = finding.get("severity")
                status = str(finding.get("status", "OPEN")).upper()
            else:
                sev_raw = getattr(finding, "severity", "INFO")
                status = str(getattr(finding, "status", "OPEN")).upper()

            # Only count active/open findings towards penalty
            if status == "RESOLVED":
                continue

            sev = normalize_severity(sev_raw)
            raw_penalties[sev] = raw_penalties.get(sev, 0) + PENALTY_WEIGHTS.get(sev, 0)

        # Apply caps per severity bucket
        total_penalty = 0
        for sev, raw_penalty in raw_penalties.items():
            capped_penalty = min(raw_penalty, PENALTY_CAPS.get(sev, 0))
            total_penalty += capped_penalty

        score = 100 - total_penalty
        score = max(0, min(100, score))

        return score, get_rating_label(score)

    @staticmethod
    def calculate_category_scores(findings: List[Any]) -> Dict[str, dict]:
        """
        Groups findings into high-level categories (IDENTITY, STORAGE, NETWORK, COMPUTE, DATABASE, MONITORING)
        and calculates their individual scores and status.
        """
        grouped: Dict[str, List[Any]] = {}
        for finding in findings:
            if isinstance(finding, dict):
                cat_raw = str(finding.get("category", "") or "")
                status = str(finding.get("status", "OPEN")).upper()
            else:
                cat_raw = str(getattr(finding, "category", "") or "")
                status = str(getattr(finding, "status", "OPEN")).upper()

            if status == "RESOLVED":
                continue

            cat = map_category(cat_raw)
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(finding)

        category_scores: Dict[str, dict] = {}

        for cat, cat_findings in grouped.items():
            raw_penalties = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
            for f in cat_findings:
                if isinstance(f, dict):
                    sev_raw = f.get("severity")
                else:
                    sev_raw = getattr(f, "severity", "INFO")
                sev = normalize_severity(sev_raw)
                raw_penalties[sev] = raw_penalties.get(sev, 0) + PENALTY_WEIGHTS.get(sev, 0)

            total_penalty = 0
            for sev, raw_penalty in raw_penalties.items():
                total_penalty += min(raw_penalty, PENALTY_CAPS.get(sev, 0))

            score = max(0, min(100, 100 - total_penalty))

            if score < 40:
                cat_status = "CRITICAL"
            elif score < 60:
                cat_status = "HIGH_RISK"
            elif score < 75:
                cat_status = "NEEDS_ATTENTION"
            elif score < 90:
                cat_status = "GOOD"
            else:
                cat_status = "SECURE"

            crit_count = 0
            high_count = 0
            for f in cat_findings:
                s = normalize_severity(f.get("severity") if isinstance(f, dict) else getattr(f, "severity", "INFO"))
                if s == "CRITICAL":
                    crit_count += 1
                elif s == "HIGH":
                    high_count += 1

            category_scores[cat] = CategoryScore(
                score=score,
                findings=len(cat_findings),
                critical=crit_count,
                high=high_count,
                status=cat_status,
            ).model_dump()

        return category_scores


risk_engine = RiskEngineService()
calculate_finding_risk = RiskEngineService.calculate_finding_risk
calculate_security_score = RiskEngineService.calculate_security_score
calculate_category_scores = RiskEngineService.calculate_category_scores
