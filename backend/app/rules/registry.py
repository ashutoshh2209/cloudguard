from typing import List, Type, Dict, Optional
from app.rules.base import SecurityRule

class RuleRegistry:
    """
    Registry for all security rules.
    Provides lookup by service and rule_id.
    """
    _rules: Dict[str, List[SecurityRule]] = {}
    _rules_by_id: Dict[str, SecurityRule] = {}

    @classmethod
    def register(cls, rule_class: Type[SecurityRule]):
        rule_instance = rule_class()
        service = rule_instance.service.lower()
        rule_id = rule_instance.rule_id

        # Update service mapping
        if service not in cls._rules:
            cls._rules[service] = []
        
        # Replace if existing with same rule_id to avoid duplicate on re-import
        existing_idx = next(
            (idx for idx, r in enumerate(cls._rules[service]) if r.rule_id == rule_id),
            None
        )
        if existing_idx is not None:
            cls._rules[service][existing_idx] = rule_instance
        else:
            cls._rules[service].append(rule_instance)

        cls._rules_by_id[rule_id] = rule_instance
        return rule_class

    @classmethod
    def get_rules_for_service(cls, service: str) -> List[SecurityRule]:
        service_key = service.lower()
        # Also handle aliases like 'security_group' -> 'ec2' or 'security_groups'
        rules = list(cls._rules.get(service_key, []))
        if service_key in ("security_group", "security_groups"):
            for r in cls._rules.get("ec2", []):
                if getattr(r, "resource_type", "") in ("security_group", "ec2:security-group") and r not in rules:
                    rules.append(r)
        return rules

    @classmethod
    def get_rule(cls, rule_id: str) -> Optional[SecurityRule]:
        return cls._rules_by_id.get(rule_id)

    @classmethod
    def get_all_rules(cls) -> List[SecurityRule]:
        return list(cls._rules_by_id.values())

    @classmethod
    def clear(cls):
        """For testing purposes."""
        cls._rules = {}
        cls._rules_by_id = {}
