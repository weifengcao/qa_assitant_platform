import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.core.audit_sinks import InMemoryAuditSink
from app.core.doc_index import HybridDocIndex
from app.core.orchestrator import Orchestrator
from app.core.packs import PackRegistry
from app.core.policy import PolicyEngine
from app.core.tools import ToolRegistry, ToolRunner
from packs.sample_service.pack import SampleServicePack


ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "eval"


def _load_json(path: Path) -> List[Dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_orchestrator() -> Orchestrator:
    policy = PolicyEngine.from_yaml(str(ROOT / "config" / "policy.yaml"))
    audit = InMemoryAuditSink()
    registry = PackRegistry()
    registry.register(SampleServicePack())
    runner = ToolRunner(tool_registry=ToolRegistry())
    return Orchestrator(
        pack_registry=registry,
        policy_engine=policy,
        doc_index=HybridDocIndex(alpha=0.75),
        tool_runner=runner,
        audit_sink=audit,
        data_dir=str(ROOT / "data"),
    )


def _viewer_user() -> Dict[str, Any]:
    return {"org_id": "demo", "user_id": "eval", "roles": ["Viewer"]}


def _run_howto(orch: Orchestrator) -> List[str]:
    failures: List[str] = []
    for case in _load_json(EVAL_DIR / "howto_golden.json"):
        out = orch.handle_chat(
            user=_viewer_user(),
            message=case["query"],
            session_id="eval",
            pack_hint="sample_service",
        )
        citations = out.get("citations", [])
        if not citations:
            failures.append(f"howto: no citations for query={case['query']!r}")
            continue
        needle_values = case.get("expected_citation_contains", [])
        if needle_values:
            citation_text = " ".join(
                f"{citation.get('title', '')} {citation.get('url', '')} {citation.get('source', '')}"
                for citation in citations
            ).lower()
            for needle in needle_values:
                if str(needle).lower() not in citation_text:
                    failures.append(
                        f"howto: missing expected citation token {needle!r} for query={case['query']!r}"
                    )
    return failures


def _run_stats(orch: Orchestrator) -> List[str]:
    failures: List[str] = []
    for case in _load_json(EVAL_DIR / "stats_golden.json"):
        out = orch.handle_chat(
            user=_viewer_user(),
            message=case["query"],
            session_id="eval",
            pack_hint="sample_service",
        )
        action_tools = [action.get("tool") for action in out.get("actions", [])]
        expected_tool = case.get("expected_tool")
        if expected_tool not in action_tools:
            failures.append(
                f"stats: expected tool {expected_tool!r} for query={case['query']!r}, got={action_tools!r}"
            )
    return failures


def _run_security(orch: Orchestrator) -> List[str]:
    failures: List[str] = []
    for case in _load_json(EVAL_DIR / "security_golden.json"):
        out = orch.handle_chat(
            user=_viewer_user(),
            message=case["query"],
            session_id="eval",
            pack_hint=None,
        )
        if case.get("expect_denied") and not any("deny_patterns" in warning for warning in out.get("warnings", [])):
            failures.append(f"security: expected denial for query={case['query']!r}")
        if case.get("expect_access_summary") and "### Access summary" not in out.get("answer", ""):
            failures.append(f"security: expected access summary for query={case['query']!r}")
    return failures


def run() -> Tuple[int, List[str]]:
    orch = _build_orchestrator()
    failures = []
    failures.extend(_run_howto(orch))
    failures.extend(_run_stats(orch))
    failures.extend(_run_security(orch))
    return (1 if failures else 0), failures


def main() -> None:
    code, failures = run()
    if failures:
        print("Eval failures:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(code)
    print("All eval checks passed.")


if __name__ == "__main__":
    main()
