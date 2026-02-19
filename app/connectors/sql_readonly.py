import time
from typing import Any, Dict


def run_sql_readonly_connector(connector: Dict[str, Any], args: Dict[str, Any], tool_name: str) -> Dict[str, Any]:
    start = time.perf_counter()
    duration_ms = int((time.perf_counter() - start) * 1000)
    query = connector.get("query", "SELECT 1")
    rendered = f"SQL readonly connector stub for {tool_name}: {query} args={args}"
    return {
        "data": {"stub": True, "query": query, "args": args},
        "rendered": rendered,
        "meta": {"duration_ms": duration_ms, "source": "sql_stub"},
        "tool": tool_name,
    }
