from typing import Dict, Any, List, Optional
import jsonschema

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(self, tool: Dict[str, Any]) -> None:
        self._tools[tool["name"]] = tool

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        return self._tools.get(name)

    def list(self) -> List[Dict[str, Any]]:
        return list(self._tools.values())

class ToolRunner:
    def __init__(self, tool_registry: ToolRegistry):
        self.registry = tool_registry

    def call(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        tool = self.registry.get(tool_name)
        if not tool:
            raise KeyError(f"Unknown tool: {tool_name}")

        schema = tool.get("schema")
        if schema:
            jsonschema.validate(instance=args, schema=schema)

        connector = tool.get("connector", {"type": "mock"})
        ctype = connector.get("type", "mock")

        # Mock connector executes a python callable name stored in connector["handler"]
        if ctype == "mock":
            handler = connector.get("handler")
            if not handler or not callable(handler):
                raise RuntimeError("Mock tool missing callable handler")
            return handler(args)

        # Future stubs:
        if ctype == "http":
            raise NotImplementedError("HTTP connector stub (implement later).")
        if ctype == "sql":
            raise NotImplementedError("SQL connector stub (implement later).")

        raise NotImplementedError(f"Unknown connector type: {ctype}")
