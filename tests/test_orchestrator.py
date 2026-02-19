import pytest


def test_stats_query_emits_action(orchestrator, viewer_user) -> None:
    out = orchestrator.handle_chat(
        user=viewer_user,
        message="What is the request volume in the last 24h?",
        session_id="s1",
        pack_hint=None,
    )

    assert out["meta"]["intent"] in {"stats", "mixed"}
    assert out["actions"]
    assert out["actions"][0]["tool"] == "sample.stats.request_volume_24h"
    assert "retrieval" in out["meta"]
    assert "tool_calls" in out["meta"]


def test_deny_pattern_blocks_export_like_requests(orchestrator, viewer_user) -> None:
    out = orchestrator.handle_chat(
        user=viewer_user,
        message="Please export all raw ids",
        session_id="s1",
        pack_hint=None,
    )

    assert out["meta"]["intent"] == "security"
    assert any("deny_patterns" in warning for warning in out["warnings"])
    assert not out["actions"]


def test_pack_hint_not_found_warns(orchestrator, viewer_user) -> None:
    out = orchestrator.handle_chat(
        user=viewer_user,
        message="How do I rotate an API key?",
        session_id="s1",
        pack_hint="does_not_exist",
    )

    assert any("was not found" in warning for warning in out["warnings"])


def test_reindex_pack_reloads_docs(orchestrator, viewer_user) -> None:
    orchestrator.handle_chat(
        user=viewer_user,
        message="How do I rotate an API key?",
        session_id="s1",
        pack_hint="sample_service",
    )

    before = orchestrator.doc_index.count(filters={"org_id": "demo", "pack_id": "sample_service"})
    result = orchestrator.reindex(org_id="demo", pack_id="sample_service")
    after = orchestrator.doc_index.count(filters={"org_id": "demo", "pack_id": "sample_service"})

    assert before > 0
    assert result["packs"] == ["sample_service"]
    assert result["indexed_docs"] > 0
    assert after > 0


def test_reindex_unknown_pack_raises(orchestrator) -> None:
    with pytest.raises(ValueError, match="Unknown pack_id"):
        orchestrator.reindex(org_id="demo", pack_id="missing")


def test_audit_events_cover_request_lifecycle(orchestrator, viewer_user) -> None:
    out = orchestrator.handle_chat(
        user=viewer_user,
        message="What is the request volume in the last 24h?",
        session_id="s1",
        pack_hint="sample_service",
    )
    events = orchestrator.audit.get(out["meta"]["trace_id"]) or []
    kinds = [event["kind"] for event in events]

    assert "request_received" in kinds
    assert "intent_classified" in kinds
    assert "packs_selected" in kinds
    assert "tool_called" in kinds
    assert "response_returned" in kinds
