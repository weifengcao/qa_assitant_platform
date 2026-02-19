import yaml
import re
from typing import Dict, Any, List

class PolicyEngine:
    def __init__(self, raw: Dict[str, Any]):
        self.raw = raw

    @staticmethod
    def from_yaml(path: str) -> "PolicyEngine":
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        return PolicyEngine(raw=raw)

    def deny_patterns(self) -> List[str]:
        return self.raw.get("deny_patterns", []) or []

    def role_rules(self, role: str) -> Dict[str, Any]:
        return (self.raw.get("roles") or {}).get(role, {})

    def allowed_packs(self, roles: List[str]) -> List[str]:
        allowed = set()
        for r in roles:
            for p in self.role_rules(r).get("allowed_packs", []):
                allowed.add(p)
        return sorted(list(allowed))

    def allowed_tools(self, roles: List[str]) -> List[str]:
        allowed = set()
        for r in roles:
            for t in self.role_rules(r).get("allowed_tools", []):
                allowed.add(t)
        return sorted(list(allowed))

    def is_denied(self, message: str) -> bool:
        m = message.lower()
        return any(pat in m for pat in self.deny_patterns())

    def redaction(self) -> Dict[str, Any]:
        return self.raw.get("redaction", {}) or {}

    @staticmethod
    def match_pattern(name: str, patterns: List[str]) -> bool:
        for pat in patterns:
            if pat == "*":
                return True
            if pat.endswith(".*") and name.startswith(pat[:-2]):
                return True
            if name == pat:
                return True
        return False
