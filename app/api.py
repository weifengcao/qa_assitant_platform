import os
import time
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from app.core.orchestrator import Orchestrator
from app.core.policy import PolicyEngine
from app.core.packs import PackRegistry
from app.core.audit import InMemoryAuditSink
from app.core.doc_index import InMemoryDocIndex
from app.core.tools import ToolRegistry, ToolRunner
from packs.sample_service.pack import SampleServicePack

app = FastAPI(title="Universal Q&A Assistant Platform (Baseline)")

# Wiring
policy = PolicyEngine.from_yaml(os.getenv("POLICY_PATH", "/app/config/policy.yaml"))
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
    data_dir=os.getenv("DATA_DIR", "/app/data"),
)

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    pack_hint: Optional[str] = None

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/packs")
def packs():
    return {"packs": registry.catalog()}

@app.post("/chat")
def chat(
    req: ChatRequest,
    x_org_id: str = Header(default="demo", alias="X-Org-Id"),
    x_user_id: str = Header(default="u1", alias="X-User-Id"),
    x_roles: str = Header(default="Viewer", alias="X-Roles"),
):
    user = {"org_id": x_org_id, "user_id": x_user_id, "roles": [r.strip() for r in x_roles.split(",") if r.strip()]}
    t0 = time.time()
    out = orch.handle_chat(user=user, message=req.message, session_id=req.session_id, pack_hint=req.pack_hint)
    out["meta"]["latency_ms"] = int((time.time() - t0) * 1000)
    return out
