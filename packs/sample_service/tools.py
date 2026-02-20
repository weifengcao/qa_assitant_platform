from datetime import datetime, timezone
from typing import Any, Dict


def stats_request_volume_24h(args: Dict[str, Any]) -> Dict[str, Any]:
    # Mocked metric
    now = datetime.now(timezone.utc).isoformat()
    timeframe = args.get("timeframe", "24h")
    service = args.get("service")
    env = args.get("environment")
    volume = 128734
    parts = [f"- Tool `sample.stats.request_volume_24h` reported **{volume:,}** requests"]
    parts.append(f"(timeframe: {timeframe}")
    if service:
        parts.append(f", service: {service}")
    if env:
        parts.append(f", environment: {env}")
    parts.append(f"; as of {now})")
    rendered = "".join(parts)
    return {
        "data": {"value": volume, "timeframe": timeframe, "as_of": now, "service": service, "environment": env},
        "rendered": rendered,
        "source": "sample_service_metrics",
    }


def stats_p95_latency_24h(args: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    timeframe = args.get("timeframe", "24h")
    service = args.get("service")
    env = args.get("environment")
    p95_ms = 82.4
    parts = [f"- Tool `sample.stats.p95_latency_24h` reported **{p95_ms} ms** p95 latency"]
    parts.append(f"(timeframe: {timeframe}")
    if service:
        parts.append(f", service: {service}")
    if env:
        parts.append(f", environment: {env}")
    parts.append(f"; as of {now})")
    rendered = "".join(parts)
    return {
        "data": {"value": p95_ms, "unit": "ms", "timeframe": timeframe, "as_of": now, "service": service, "environment": env},
        "rendered": rendered,
        "source": "sample_service_metrics",
    }
