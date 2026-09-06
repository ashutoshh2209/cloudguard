from typing import List, Type, Dict
from app.rules.base import SecurityRule

class RuleRegistry:
    """
    Registry for all security rules.
    Maps service names to a list of instantiated rules.
    """
    _rules: Dict[str, List[SecurityRule]] = {}

    @classmethod
    def register(cls, rule_class: Type[SecurityRule]):
        rule_instance = rule_class()
        service = rule_instance.service
        if service not in cls._rules:
            cls._rules[service] = []
        cls._rules[service].append(rule_instance)
        return rule_class

    @classmethod
    def get_rules_for_service(cls, service: str) -> List[SecurityRule]:
        return cls._rules.get(service, [])

    @classmethod
    def clear(cls):
        """For testing purposes."""
        cls._rules = {}
