from app.core.tool_args import (
    _detect_environment,
    _detect_metric,
    _detect_service,
    _detect_timeframe,
    extract_tool_args,
)

# ── Timeframe detection ────────────────────────────────────────────────────────


def test_detect_24h_short() -> None:
    assert _detect_timeframe("request volume 24h") == "24h"


def test_detect_24h_spaced() -> None:
    assert _detect_timeframe("usage over 24 h") == "24h"


def test_detect_7d_short() -> None:
    assert _detect_timeframe("last 7d") == "7d"


def test_detect_7_days_spelled() -> None:
    assert _detect_timeframe("over the last 7 days") == "7d"


def test_detect_last_N_hours() -> None:
    assert _detect_timeframe("last 48 hours") == "48h"


def test_detect_N_days() -> None:
    assert _detect_timeframe("past 3 days") == "3d"


def test_detect_timeframe_none_when_absent() -> None:
    assert _detect_timeframe("show me request volume") is None


# ── Metric detection ───────────────────────────────────────────────────────────


def test_detect_metric_p95_latency() -> None:
    assert _detect_metric("p95 latency for auth service") == "p95_latency"


def test_detect_metric_latency_only() -> None:
    assert _detect_metric("what's the latency") == "latency"


def test_detect_metric_errors() -> None:
    assert _detect_metric("how many errors today") == "errors"


def test_detect_metric_volume() -> None:
    assert _detect_metric("request volume last 24h") == "request_volume"


def test_detect_metric_none() -> None:
    assert _detect_metric("how do I reset my password") is None


# ── Service detection ──────────────────────────────────────────────────────────


def test_detect_service_pattern() -> None:
    assert _detect_service("service auth in prod") == "auth"


def test_detect_service_hyphen_name() -> None:
    assert _detect_service("service api-gateway metrics") == "api-gateway"


def test_detect_service_none() -> None:
    assert _detect_service("show me request volume") is None


# ── Environment detection ──────────────────────────────────────────────────────


def test_detect_environment_prod_keyword() -> None:
    assert _detect_environment("errors in prod last 24h") == "prod"


def test_detect_environment_staging() -> None:
    assert _detect_environment("latency in staging") == "staging"


def test_detect_environment_sandbox_prefix() -> None:
    result = _detect_environment("sandbox environment metrics")
    assert result in ("sandbox", "environment")  # sandbox appears first


def test_detect_environment_none() -> None:
    assert _detect_environment("how do I rotate an API key") is None


# ── extract_tool_args ─────────────────────────────────────────────────────────


def test_extract_args_with_empty_schema() -> None:
    args, warnings = extract_tool_args(
        message="request volume last 24h service auth in prod",
        schema={},
    )
    assert args == {}


def test_extract_args_fills_known_fields() -> None:
    schema = {
        "type": "object",
        "properties": {
            "timeframe": {"type": "string"},
            "service": {"type": "string"},
        },
    }
    args, _ = extract_tool_args(
        message="request volume last 24h service auth",
        schema=schema,
    )
    assert args.get("timeframe") == "24h"
    assert args.get("service") == "auth"


def test_extract_args_uses_defaults_when_no_match() -> None:
    schema = {
        "type": "object",
        "properties": {"timeframe": {"type": "string"}},
    }
    args, warnings = extract_tool_args(
        message="show me the data",
        schema=schema,
        defaults={"timeframe": "24h"},
    )
    assert args.get("timeframe") == "24h"
    assert any("default" in w.lower() for w in warnings)


def test_extract_args_does_not_inject_extra_keys() -> None:
    schema = {
        "type": "object",
        "properties": {"timeframe": {"type": "string"}},
    }
    args, _ = extract_tool_args(
        message="service auth in prod last 7d",
        schema=schema,
    )
    # Only schema property keys should be present.
    assert set(args.keys()).issubset({"timeframe"})
