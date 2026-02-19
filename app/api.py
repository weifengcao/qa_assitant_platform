import os
import time
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.core.orchestrator import Orchestrator
from app.core.policy import PolicyEngine
from app.core.packs import PackRegistry
from app.core.audit import InMemoryAuditSink
from app.core.doc_index import InMemoryDocIndex
from app.core.tools import ToolRegistry, ToolRunner
from packs.sample_service.pack import SampleServicePack


app = FastAPI(title="Universal Q&A Assistant Platform (Baseline)")


def _default_path(docker_path: str, local_path: str) -> str:
    return docker_path if os.path.exists(docker_path) else local_path


def _parse_roles(value: str) -> list[str]:
    roles = [role.strip() for role in value.split(",") if role.strip()]
    return roles or ["Viewer"]


policy = PolicyEngine.from_yaml(
    os.getenv("POLICY_PATH", _default_path("/app/config/policy.yaml", "config/policy.yaml"))
)
audit = InMemoryAuditSink()

registry = PackRegistry()
registry.register(SampleServicePack())

doc_index = InMemoryDocIndex()
tools = ToolRegistry()
runner = ToolRunner(tool_registry=tools)

orch = Orchestrator(
    pack_registry=registry,
    policy_engine=policy,
    doc_index=doc_index,
    tool_runner=runner,
    audit_sink=audit,
    data_dir=os.getenv("DATA_DIR", _default_path("/app/data", "data")),
)


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=4000)
    session_id: Optional[str] = Field(default=None, max_length=128)
    pack_hint: Optional[str] = Field(default=None, max_length=128)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/packs")
def packs() -> dict[str, list[dict]]:
    return {"packs": registry.catalog()}


@app.get("/audit/{trace_id}")
def get_audit(trace_id: str) -> dict:
    trace = audit.get(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return {"trace_id": trace_id, "events": trace}


@app.post("/chat")
def chat(
    req: ChatRequest,
    x_org_id: str = Header(default="demo", alias="X-Org-Id"),
    x_user_id: str = Header(default="u1", alias="X-User-Id"),
    x_roles: str = Header(default="Viewer", alias="X-Roles"),
) -> dict:
    user = {
        "org_id": x_org_id,
        "user_id": x_user_id,
        "roles": _parse_roles(x_roles),
    }
    t0 = time.time()
    out = orch.handle_chat(
        user=user,
        message=req.message,
        session_id=req.session_id,
        pack_hint=req.pack_hint,
    )
    out["meta"]["latency_ms"] = int((time.time() - t0) * 1000)
    return out
