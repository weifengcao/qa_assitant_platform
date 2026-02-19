from typing import Dict, Any
from datetime import datetime, timezone

def stats_request_volume_24h(args: Dict[str, Any]) -> Dict[str, Any]:
    # Mocked metric
    now = datetime.now(timezone.utc).isoformat()
    volume = 128734
    return {"rendered": f"- Request volume (last 24h): **{volume:,}** (as of {now})"}

def stats_p95_latency_24h(args: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    p95_ms = 82.4
    return {"rendered": f"- p95 latency (last 24h): **{p95_ms} ms** (as of {now})"}
