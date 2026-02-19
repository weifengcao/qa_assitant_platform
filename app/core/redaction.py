import re
from typing import Dict, Any

_EMAIL = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
_LONG_ID = re.compile(r"\b([A-Fa-f0-9]{16,}|[A-Za-z0-9_-]{24,})\b")

def apply_redaction(text: str, rules: Dict[str, Any]) -> str:
    out = text
    if rules.get("mask_emails", True):
        out = _EMAIL.sub(lambda m: m.group(1)[:2] + "***@" + m.group(2), out)
    if rules.get("mask_long_ids", True):
        out = _LONG_ID.sub(lambda m: m.group(1)[:4] + "…" + m.group(1)[-4:], out)
    return out
