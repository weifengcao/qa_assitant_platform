import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import yaml


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


@dataclass(frozen=True)
class RoleRule:
    allowed_packs: List[str] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class RedactionPolicy:
    mask_emails: bool = True
    mask_long_ids: bool = True
    suppress_small_counts: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mask_emails": self.mask_emails,
            "mask_long_ids": self.mask_long_ids,
            "suppress_small_counts": self.suppress_small_counts,
        }


@dataclass(frozen=True)
class Policy:
    version: int = 1
    deny_patterns: List[str] = field(default_factory=list)
    roles: Dict[str, RoleRule] = field(default_factory=dict)
    redaction: RedactionPolicy = field(default_factory=RedactionPolicy)


class PolicyEngine:
    def __init__(self, raw: Dict[str, Any] | Policy):
        self.policy = raw if isinstance(raw, Policy) else self._build_policy(raw or {})
        self._deny_regexes, self._deny_substrings = self._compile_deny_patterns(self.policy.deny_patterns)

    @classmethod
    def from_yaml(cls, path: str) -> "PolicyEngine":
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        return cls(raw=raw)

    @staticmethod
    def _build_policy(raw: Dict[str, Any]) -> Policy:
        raw_roles = raw.get("roles") or {}
        roles: Dict[str, RoleRule] = {}
        for role_name, role_cfg in raw_roles.items():
            role_cfg = role_cfg or {}
            roles[role_name] = RoleRule(
                allowed_packs=[str(p) for p in (role_cfg.get("allowed_packs") or [])],
                allowed_tools=[str(t) for t in (role_cfg.get("allowed_tools") or [])],
            )

        redaction_cfg = raw.get("redaction") or {}
        suppress_small_counts = redaction_cfg.get("suppress_small_counts")
        if suppress_small_counts is None:
            suppress_small_counts = raw.get("suppress_small_counts")
        threshold: Optional[int]
        if isinstance(suppress_small_counts, int):
            threshold = suppress_small_counts
        else:
            threshold = None

        redaction = RedactionPolicy(
            mask_emails=bool(redaction_cfg.get("mask_emails", True)),
            mask_long_ids=bool(redaction_cfg.get("mask_long_ids", True)),
            suppress_small_counts=threshold,
        )

        version = raw.get("version")
        return Policy(
            version=version if isinstance(version, int) else 1,
            deny_patterns=[str(v) for v in (raw.get("deny_patterns") or [])],
            roles=roles,
            redaction=redaction,
        )

    def deny_patterns(self) -> List[str]:
        return list(self.policy.deny_patterns)

    def role_rules(self, role: str) -> RoleRule:
        return self.policy.roles.get(role, RoleRule())

    def allowed_packs(self, roles: List[str]) -> List[str]:
        allowed = set()
        for role in roles:
            allowed.update(self.role_rules(role).allowed_packs)
        return sorted(allowed)

    def allowed_tools(self, roles: List[str]) -> List[str]:
        allowed = set()
        for role in roles:
            allowed.update(self.role_rules(role).allowed_tools)
        return sorted(allowed)

    def filter_allowed_tools(self, tool_names: List[str], roles: List[str]) -> List[str]:
        patterns = self.allowed_tools(roles)
        return [name for name in tool_names if self.match_pattern(name, patterns)]

    def filter_allowed_packs(self, pack_ids: List[str], roles: List[str]) -> List[str]:
        patterns = self.allowed_packs(roles)
        return [name for name in pack_ids if self.match_pattern(name, patterns)]

    def is_denied(self, message: str) -> bool:
        if any(rx.search(message) for rx in self._deny_regexes):
            return True
        normalized_message = _normalize_space(message)
        return any(phrase in normalized_message for phrase in self._deny_substrings)

    def redaction(self) -> Dict[str, Any]:
        return self.policy.redaction.to_dict()

    @staticmethod
    def match_pattern(name: str, patterns: List[str]) -> bool:
        for pat in patterns:
            if pat == "*":
                return True
            if pat.endswith(".*"):
                prefix = pat[:-2]
                if (
                    name == prefix
                    or name.startswith(prefix + ".")
                    or name.startswith(prefix + "_")
                    or name.startswith(prefix + "-")
                ):
                    return True
            elif name == pat:
                return True
        return False

    @staticmethod
    def _compile_deny_patterns(patterns: List[str]) -> Tuple[List[re.Pattern], List[str]]:
        compiled_regexes: List[re.Pattern] = []
        compiled_substrings: List[str] = []
        for pattern in patterns:
            cleaned = pattern.strip()
            if not cleaned:
                continue
            if cleaned.startswith("re:"):
                try:
                    compiled_regexes.append(re.compile(cleaned[3:], flags=re.IGNORECASE))
                    continue
                except re.error:
                    pass
            compiled_substrings.append(_normalize_space(cleaned))
        return compiled_regexes, compiled_substrings
