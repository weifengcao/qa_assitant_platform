import re
from typing import Any, Dict, List, Optional, Tuple


_TIMEFRAME_RE = re.compile(r"\b(?:last|past)?\s*(\d+)\s*(h|hr|hrs|hour|hours|d|day|days)\b", re.IGNORECASE)
_SERVICE_RE = re.compile(r"\bservice\s+([a-zA-Z0-9_-]+)\b", re.IGNORECASE)
_ENV_RE = re.compile(r"\b(?:sandbox|env|environment)\s+([a-zA-Z0-9_-]+)\b", re.IGNORECASE)
_KNOWN_ENVS = ("prod", "production", "staging", "stage", "dev", "sandbox", "test")


def _detect_timeframe(message: str) -> Optional[str]:
    lower = message.lower()
    if "24h" in lower or "24 h" in lower:
        return "24h"
    if "7d" in lower or "7 d" in lower or "7 days" in lower:
        return "7d"
    match = _TIMEFRAME_RE.search(message)
    if not match:
        return None
    number = int(match.group(1))
    unit = match.group(2).lower()
    if unit.startswith("h"):
        return f"{number}h"
    return f"{number}d"


def _detect_metric(message: str) -> Optional[str]:
    lower = message.lower()
    if "p95" in lower and "latency" in lower:
        return "p95_latency"
    if "latency" in lower:
        return "latency"
    if "error" in lower:
        return "errors"
    if any(term in lower for term in ("volume", "traffic", "request", "requests", "count")):
        return "request_volume"
    return None


def _detect_service(message: str) -> Optional[str]:
    match = _SERVICE_RE.search(message)
    if match:
        return match.group(1)
    return None


def _detect_environment(message: str) -> Optional[str]:
    match = _ENV_RE.search(message)
    if match:
        return match.group(1)
    lower = message.lower()
    for env in _KNOWN_ENVS:
        if re.search(rf"\b{re.escape(env)}\b", lower):
            return env
    return None


def extract_tool_args(
    message: str,
    schema: Dict[str, Any],
    defaults: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], List[str]]:
    defaults = defaults or {}
    props = schema.get("properties", {}) if isinstance(schema, dict) else {}

    extracted: Dict[str, Any] = {}
    warnings: List[str] = []

    timeframe = _detect_timeframe(message)
    metric = _detect_metric(message)
    service = _detect_service(message)
    environment = _detect_environment(message)

    candidates: Dict[str, Any] = {
        "timeframe": timeframe,
        "metric": metric,
        "service": service,
        "environment": environment,
    }
    for key, value in defaults.items():
        candidates.setdefault(key, value)

    for key, value in candidates.items():
        if value is None:
            continue
        if key in props:
            extracted[key] = value

    if not extracted and defaults:
        # Defaults are allowed when parsing cannot infer arguments.
        for key, value in defaults.items():
            if key in props:
                extracted[key] = value
        if extracted:
            warnings.append("Could not infer tool arguments from query; using defaults.")

    return extracted, warnings
