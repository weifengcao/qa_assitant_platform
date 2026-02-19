from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass(frozen=True)
class AuditEvent:
    timestamp: str
    trace_id: str
    kind: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "kind": self.kind,
            "data": self.data,
        }


def new_audit_event(trace_id: str, kind: str, data: Dict[str, Any]) -> AuditEvent:
    return AuditEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        trace_id=trace_id,
        kind=kind,
        data=data,
    )
