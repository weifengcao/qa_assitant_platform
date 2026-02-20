import pytest
from app.core.audit_sinks import InMemoryAuditSink
from app.core.doc_index import HybridDocIndex
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
    # ToolRegistry is passed to ToolRunner here; Orchestrator.__init__ calls
    # _register_tools() which registers pack tools into this same registry.
    tool_reg = ToolRegistry()
    runner = ToolRunner(tool_registry=tool_reg)
    return Orchestrator(
        pack_registry=registry,
        policy_engine=policy,
        doc_index=HybridDocIndex(alpha=0.75),
        tool_runner=runner,
        audit_sink=audit,
        data_dir="data",
    )


@pytest.fixture()
def viewer_user() -> dict:
    return {"org_id": "demo", "user_id": "u1", "roles": ["Viewer"]}


@pytest.fixture()
def admin_user() -> dict:
    return {"org_id": "demo", "user_id": "admin1", "roles": ["Admin"]}
