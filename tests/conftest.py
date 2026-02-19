import pytest

from app.core.audit_sinks import InMemoryAuditSink
from app.core.doc_index import InMemoryDocIndex
from app.core.orchestrator import Orchestrator
from app.core.packs import PackRegistry
from app.core.policy import PolicyEngine
from app.core.tools import ToolRegistry, ToolRunner
from packs.sample_service.pack import SampleServicePack


@pytest.fixture()
def orchestrator() -> Orchestrator:
    policy = PolicyEngine.from_yaml("config/policy.yaml")
    audit = InMemoryAuditSink()
    registry = PackRegistry()
    registry.register(SampleServicePack())
    runner = ToolRunner(tool_registry=ToolRegistry())
    return Orchestrator(
        pack_registry=registry,
        policy_engine=policy,
        doc_index=InMemoryDocIndex(),
        tool_runner=runner,
        audit_sink=audit,
        data_dir="data",
    )


@pytest.fixture()
def viewer_user() -> dict:
    return {"org_id": "demo", "user_id": "u1", "roles": ["Viewer"]}
