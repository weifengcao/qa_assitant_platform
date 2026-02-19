from typing import Any, Dict

import pytest

from app.core.tools import ToolDef, ToolExecutionError, ToolRegistry, ToolRunner


def _mock_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "data": {"echo": args},
        "rendered": f"echo={args}",
        "source": "unit_test",
    }


def test_tool_runner_extracts_args_from_query() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolDef(
            name="sample.stats.request_volume_24h",
            description="test tool",
            schema={
                "type": "object",
                "properties": {
                    "timeframe": {"type": "string"},
                    "metric": {"type": "string"},
                    "service": {"type": "string"},
                    "environment": {"type": "string"},
                },
                "additionalProperties": False,
            },
            default_args={"timeframe": "24h", "metric": "request_volume"},
            connector={"type": "mock", "handler": _mock_handler},
        )
    )
    runner = ToolRunner(registry)

    result = runner.call(
        tool_name="sample.stats.request_volume_24h",
        args={},
        query="request volume last 24h for service billing in prod",
    )

    assert result["args"]["timeframe"] == "24h"
    assert result["args"]["service"] == "billing"
    assert result["args"]["environment"] in {"prod", "production"}


def test_tool_runner_rejects_invalid_args() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolDef(
            name="sample.stats.strict",
            description="strict schema",
            schema={
                "type": "object",
                "properties": {"timeframe": {"type": "string"}},
                "additionalProperties": False,
            },
            connector={"type": "mock", "handler": _mock_handler},
        )
    )
    runner = ToolRunner(registry)

    with pytest.raises(ToolExecutionError, match="Invalid arguments"):
        runner.call("sample.stats.strict", args={"unknown": "x"})


def test_http_connector_stub_executes() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolDef(
            name="sample.stats.http_stub",
            description="http tool",
            schema={"type": "object", "properties": {}, "additionalProperties": False},
            connector={"type": "http", "endpoint": "https://example.invalid"},
        )
    )
    runner = ToolRunner(registry)

    result = runner.call("sample.stats.http_stub", args={})

    assert result["meta"]["source"] == "http_stub"
    assert "HTTP connector stub" in result["rendered"]
