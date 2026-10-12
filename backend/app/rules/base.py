from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional, Union
from app.findings.schemas import Severity

class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RuleEvaluationResult(dict):
    """
    Structured check result produced by deterministic rule evaluation.
    Guarantees strict evaluation status (PASS, FAIL, ERROR, NOT_APPLICABLE).
    Inherits from dict for seamless Pydantic and JSON serialization compatibility.
    """
    def __init__(
        self,
        status: CheckStatus,
        message: str,
        evidence: Optional[Dict[str, Any]] = None,
        recommendation: Optional[str] = None,
    ):
        raw_evidence = evidence or {}
        super().__init__(raw_evidence)
        self.status = status if isinstance(status, CheckStatus) else CheckStatus(status)
        self.message = message
        self.evidence = raw_evidence
        self.recommendation = recommendation

    @classmethod
    def pass_result(cls, message: str = "Resource complies with security check.") -> "RuleEvaluationResult":
        return cls(status=CheckStatus.PASS, message=message, evidence=None, recommendation=None)

    @classmethod
    def fail_result(
        cls,
        message: str,
        evidence: Optional[Dict[str, Any]] = None,
        recommendation: Optional[str] = None,
    ) -> "RuleEvaluationResult":
        return cls(
            status=CheckStatus.FAIL,
            message=message,
            evidence=evidence or {},
            recommendation=recommendation,
        )

    @classmethod
    def error_result(
        cls,
        message: str,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> "RuleEvaluationResult":
        return cls(
            status=CheckStatus.ERROR,
            message=message,
            evidence=evidence or {},
            recommendation=None,
        )

    @classmethod
    def not_applicable_result(
        cls,
        message: str = "Rule does not apply to this resource type.",
    ) -> "RuleEvaluationResult":
        return cls(
            status=CheckStatus.NOT_APPLICABLE,
            message=message,
            evidence=None,
            recommendation=None,
        )

    def __bool__(self) -> bool:
        # Legacy compat: in Part 1 scanner, `evidence = rule.evaluate(...)` checked `if evidence:`
        return self.status == CheckStatus.FAIL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "message": self.message,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
        }


class SecurityRule(ABC):
    """
    Base class for all deterministic security rules.
    """
    rule_id: str
    title: str
    service: str
    resource_type: str
    severity: Union[Severity, str]
    category: str
    description: str
    recommendation: str

    @property
    def name(self) -> str:
        return getattr(self, "title", self.rule_id)

    def evaluate_check(self, resource: Any, context: Optional[dict] = None) -> RuleEvaluationResult:
        """
        Deterministic evaluation wrapper that guarantees a structured RuleEvaluationResult
        (PASS, FAIL, ERROR, or NOT_APPLICABLE).
        Catches evaluation exceptions and never treats ERROR as PASS.
        """
        try:
            raw_res = self.evaluate(resource, context or {})
            if isinstance(raw_res, RuleEvaluationResult):
                return raw_res
            if raw_res is None:
                return RuleEvaluationResult.pass_result(f"Resource complies with {self.rule_id}.")
            if isinstance(raw_res, dict):
                return RuleEvaluationResult.fail_result(
                    message=f"Rule {self.rule_id} detected a security violation.",
                    evidence=raw_res,
                    recommendation=self.recommendation,
                )
            if isinstance(raw_res, bool):
                if raw_res:
                    return RuleEvaluationResult.pass_result(f"Resource complies with {self.rule_id}.")
                else:
                    return RuleEvaluationResult.fail_result(
                        message=f"Rule {self.rule_id} check failed.",
                        evidence={"violation": True},
                        recommendation=self.recommendation,
                    )
            return RuleEvaluationResult.pass_result(f"Resource complies with {self.rule_id}.")
        except Exception as e:
            return RuleEvaluationResult.error_result(
                message=f"Evaluation error for rule {self.rule_id}: {str(e)}",
                evidence={"error": str(e), "error_type": type(e).__name__},
            )

    @abstractmethod
    def evaluate(self, resource: Any, context: dict) -> Union[Optional[dict], RuleEvaluationResult]:
        """
        Evaluates a resource against the security rule.
        Returns RuleEvaluationResult or evidence dict if violated, or None if compliant.
        """
        pass
