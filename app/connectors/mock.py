import time
from typing import Any, Callable, Dict


def run_mock_connector(
    handler: Callable[[Dict[str, Any]], Dict[str, Any]],
    args: Dict[str, Any],
    tool_name: str,
) -> Dict[str, Any]:
    start = time.perf_counter()
    result = handler(args)
    duration_ms = int((time.perf_counter() - start) * 1000)

    data = result.get("data", result)
    rendered = result.get("rendered", str(data))
    source = result.get("source", "mock")
    meta = {**result.get("meta", {}), "duration_ms": duration_ms, "source": source}
    return {"data": data, "rendered": rendered, "meta": meta, "tool": tool_name}
