from enum import Enum


class Intent(str, Enum):
    HOW_TO = "how_to"
    STATS = "stats"
    SECURITY = "security"
    MIXED = "mixed"

def classify_intent(message: str) -> Intent:
    m = message.lower()
    how = any(k in m for k in ["how do i", "how to", "configure", "set up", "setup", "guide", "steps"])
    stats = any(k in m for k in ["how many", "count", "stats", "latency", "volume", "requests", "traffic", "errors", "rate"])
    sec = any(k in m for k in ["what can i access", "permission", "rbac", "roles", "access", "scope"])
    if sum([how, stats, sec]) >= 2:
        return Intent.MIXED
    if how:
        return Intent.HOW_TO
    if stats:
        return Intent.STATS
    if sec:
        return Intent.SECURITY
    # default to how-to (most common)
    return Intent.HOW_TO
