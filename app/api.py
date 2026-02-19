import os
import time
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from packs.sample_service.pack import SampleServicePack
from pydantic import BaseModel, ConfigDict, Field

from app.core.audit_sinks import FileAuditSink, InMemoryAuditSink
from app.core.doc_index import HybridDocIndex, InMemoryDocIndex
from app.core.embeddings import HashEmbedder, SentenceTransformerEmbedder
from app.core.orchestrator import Orchestrator
from app.core.packs import PackRegistry
from app.core.policy import PolicyEngine
from app.core.schemas import ChatRequest, ChatResponse
from app.core.tools import ToolRegistry, ToolRunner

app = FastAPI(title="Universal Q&A Assistant Platform (Baseline)")


def _default_path(docker_path: str, local_path: str) -> str:
    return docker_path if os.path.exists(docker_path) else local_path


def _parse_roles(value: str) -> list[str]:
    roles = [role.strip() for role in value.split(",") if role.strip()]
    return roles or ["Viewer"]


def _build_audit_sink() -> InMemoryAuditSink | FileAuditSink:
    sink = os.getenv("AUDIT_SINK", "memory").strip().lower()
    if sink == "file":
        path = os.getenv("AUDIT_FILE_PATH", _default_path("/app/data/audit.jsonl", "data/audit.jsonl"))
        return FileAuditSink(path=path)
    return InMemoryAuditSink()


def _build_embedder():
    backend = os.getenv("EMBEDDING_BACKEND", "hash").strip().lower()
    if backend == "st":
        try:
            return SentenceTransformerEmbedder()
        except RuntimeError:
            return HashEmbedder()
    return HashEmbedder()


def _build_doc_index():
    backend = os.getenv("DOC_INDEX_BACKEND", "hybrid").strip().lower()
    embedder = _build_embedder()
    if backend == "vector_only":
        return InMemoryDocIndex(embedder=embedder), "vector_only"
    alpha = float(os.getenv("DOC_INDEX_ALPHA", "0.75"))
    return HybridDocIndex(alpha=alpha, embedder=embedder), "hybrid"


policy = PolicyEngine.from_yaml(
    os.getenv("POLICY_PATH", _default_path("/app/config/policy.yaml", "config/policy.yaml"))
)
audit: InMemoryAuditSink | FileAuditSink = _build_audit_sink()

registry = PackRegistry()
registry.register(SampleServicePack())

tools = ToolRegistry()
runner = ToolRunner(tool_registry=tools)
doc_index, retrieval_backend = _build_doc_index()

orch = Orchestrator(
    pack_registry=registry,
    policy_engine=policy,
    doc_index=doc_index,
    tool_runner=runner,
    audit_sink=audit,
    data_dir=os.getenv("DATA_DIR", _default_path("/app/data", "data")),
    retrieval_backend=retrieval_backend,
)


class ReindexRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    pack_id: Optional[str] = Field(default=None, max_length=128)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "ok": True,
        "version": os.getenv("APP_VERSION", "0.1.0"),
        "build_sha": os.getenv("BUILD_SHA", "dev"),
    }


@app.get("/packs")
def packs() -> dict[str, list[dict]]:
    return {"packs": registry.catalog()}


@app.get("/audit/{trace_id}")
def get_audit(trace_id: str) -> dict:
    trace = audit.get(trace_id)
    if trace is None:
        if isinstance(audit, FileAuditSink):
            raise HTTPException(status_code=501, detail="Audit lookup not supported by file sink")
        raise HTTPException(status_code=404, detail="Trace not found")
    return {"trace_id": trace_id, "events": trace}


@app.post("/admin/reindex")
def admin_reindex(
    req: ReindexRequest,
    x_org_id: str = Header(default="demo", alias="X-Org-Id"),
    x_roles: str = Header(default="Viewer", alias="X-Roles"),
) -> dict:
    roles = _parse_roles(x_roles)
    if "Admin" not in roles:
        raise HTTPException(status_code=403, detail="Admin role required")
    try:
        return orch.reindex(org_id=x_org_id, pack_id=req.pack_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    x_org_id: str = Header(default="demo", alias="X-Org-Id"),
    x_user_id: str = Header(default="u1", alias="X-User-Id"),
    x_roles: str = Header(default="Viewer", alias="X-Roles"),
) -> ChatResponse:
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
        metadata=req.metadata,
    )
    out["meta"]["latency_ms"] = int((time.time() - t0) * 1000)
    return ChatResponse.model_validate(out)
