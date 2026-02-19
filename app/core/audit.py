from dataclasses import dataclass
from typing import Dict, Any, List, Optional

@dataclass
class AuditEvent:
    kind: str
    data: Dict[str, Any]

class InMemoryAuditSink:
    def __init__(self):
        self._traces: Dict[str, List[Dict[str, Any]]] = {}

    def log(self, trace_id: str, event: AuditEvent) -> None:
        self._traces.setdefault(trace_id, []).append({"kind": event.kind, "data": event.data})

    def get(self, trace_id: str) -> Optional[List[Dict[str, Any]]]:
        return self._traces.get(trace_id)
