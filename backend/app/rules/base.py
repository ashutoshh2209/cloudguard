from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from app.findings.schemas import Severity

class SecurityRule(ABC):
    """
    Base class for all security rules.
    """
    rule_id: str
    title: str
    service: str
    resource_type: str
    severity: Severity
    category: str
    description: str
    recommendation: str

    @abstractmethod
    def evaluate(self, resource: Any, context: dict) -> Optional[dict]:
        """
        Evaluates a resource against the security rule.
        Returns evidence (dict) if the rule is violated, or None if the resource is secure.
        """
        pass
