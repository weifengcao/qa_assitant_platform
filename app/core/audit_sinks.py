import json
import os
from typing import Any, Dict, List, Optional, Protocol

from app.core.audit import AuditEvent


class AuditSink(Protocol):
    def log(self, event: AuditEvent) -> None:
        ...

    def get(self, trace_id: str) -> Optional[List[Dict[str, Any]]]:
        ...


class InMemoryAuditSink:
    def __init__(self):
        self._traces: Dict[str, List[Dict[str, Any]]] = {}

    def log(self, event: AuditEvent) -> None:
        self._traces.setdefault(event.trace_id, []).append(event.to_dict())

    def get(self, trace_id: str) -> Optional[List[Dict[str, Any]]]:
        return self._traces.get(trace_id)


class FileAuditSink:
    def __init__(self, path: str):
        self.path = path
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    def log(self, event: AuditEvent) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=True) + "\n")

    def get(self, trace_id: str) -> Optional[List[Dict[str, Any]]]:
        return None
