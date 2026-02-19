from typing import Dict, Any, List, Optional
import jsonschema

class ToolExecutionError(RuntimeError):
    pass


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
            raise ToolExecutionError(f"Unknown tool: {tool_name}")

        schema = tool.get("schema")
        if schema:
            try:
                jsonschema.validate(instance=args, schema=schema)
            except jsonschema.ValidationError as exc:
                raise ToolExecutionError(f"Invalid arguments for {tool_name}: {exc.message}") from exc

        connector = tool.get("connector", {"type": "mock"})
        ctype = connector.get("type", "mock")

        # Mock connector executes a python callable name stored in connector["handler"]
        if ctype == "mock":
            handler = connector.get("handler")
            if not handler or not callable(handler):
                raise ToolExecutionError(f"Mock tool {tool_name} missing callable handler")
            try:
                return handler(args)
            except Exception as exc:
                raise ToolExecutionError(f"Tool {tool_name} failed: {exc}") from exc

        # Future stubs:
        if ctype == "http":
            raise ToolExecutionError("HTTP connector stub (implement later).")
        if ctype == "sql":
            raise ToolExecutionError("SQL connector stub (implement later).")

        raise ToolExecutionError(f"Unknown connector type for {tool_name}: {ctype}")
