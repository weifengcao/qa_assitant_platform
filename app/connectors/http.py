import time
from typing import Any, Dict


def run_http_connector(connector: Dict[str, Any], args: Dict[str, Any], tool_name: str) -> Dict[str, Any]:
    start = time.perf_counter()
    duration_ms = int((time.perf_counter() - start) * 1000)
    endpoint = connector.get("endpoint", "http://example.invalid")
    rendered = f"HTTP connector stub for {tool_name} at {endpoint} with args={args}"
    return {
        "data": {"stub": True, "endpoint": endpoint, "args": args},
        "rendered": rendered,
        "meta": {"duration_ms": duration_ms, "source": "http_stub"},
        "tool": tool_name,
    }
