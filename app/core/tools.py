from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import jsonschema

from app.connectors.http import run_http_connector
from app.connectors.mock import run_mock_connector
from app.connectors.sql_readonly import run_sql_readonly_connector
from app.core.tool_args import extract_tool_args


class ToolExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ToolDef:
    name: str
    description: str
    schema: Dict[str, Any]
    connector: Dict[str, Any]
    read_only: bool = True
    keywords: List[str] = field(default_factory=list)
    default_args: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ToolDef":
        return cls(
            name=str(raw["name"]),
            description=str(raw.get("description", raw["name"])),
            schema=raw.get("schema", {"type": "object", "properties": {}, "additionalProperties": False}),
            connector=raw.get("connector", {"type": "mock"}),
            read_only=bool(raw.get("read_only", True)),
            keywords=[str(item) for item in raw.get("keywords", [])],
            default_args=dict(raw.get("default_args", {})),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "schema": self.schema,
            "connector": self.connector,
            "read_only": self.read_only,
            "keywords": self.keywords,
            "default_args": self.default_args,
        }

    def __repr__(self) -> str:
        return f"<ToolDef name='{self.name}' read_only={self.read_only}>"


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDef] = {}

    def register(self, tool: Union[ToolDef, Dict[str, Any]]) -> None:
        tool_def = tool if isinstance(tool, ToolDef) else ToolDef.from_dict(tool)
        self._tools[tool_def.name] = tool_def

    def get(self, name: str) -> Optional[ToolDef]:
        return self._tools.get(name)

    def list(self) -> List[ToolDef]:
        return list(self._tools.values())


class ToolRunner:
    def __init__(self, tool_registry: ToolRegistry):
        self.registry = tool_registry

    @staticmethod
    def _validate(schema: Dict[str, Any], args: Dict[str, Any], tool_name: str) -> None:
        try:
            jsonschema.validate(instance=args, schema=schema)
        except jsonschema.ValidationError as exc:
            raise ToolExecutionError(f"Invalid arguments for {tool_name}: {exc.message}") from exc

    def call(
        self,
        tool_name: str,
        args: Optional[Dict[str, Any]] = None,
        query: Optional[str] = None,
    ) -> Dict[str, Any]:
        tool = self.registry.get(tool_name)
        if not tool:
            raise ToolExecutionError(f"Unknown tool: {tool_name}")
        if not tool.read_only:
            raise ToolExecutionError(f"Tool {tool_name} is not read-only and is blocked in M1")

        input_args = dict(args or {})
        warnings: List[str] = []
        if query:
            extracted, extraction_warnings = extract_tool_args(
                message=query,
                schema=tool.schema,
                defaults=tool.default_args,
            )
            warnings.extend(extraction_warnings)
            for key, value in extracted.items():
                input_args.setdefault(key, value)

        self._validate(schema=tool.schema, args=input_args, tool_name=tool_name)

        connector = tool.connector or {"type": "mock"}
        connector_type = str(connector.get("type", "mock"))

        try:
            if connector_type == "mock":
                handler = connector.get("handler")
                if not handler or not callable(handler):
                    raise ToolExecutionError(f"Mock tool {tool_name} missing callable handler")
                result = run_mock_connector(handler=handler, args=input_args, tool_name=tool_name)
            elif connector_type == "http":
                result = run_http_connector(connector=connector, args=input_args, tool_name=tool_name)
            elif connector_type == "sql_readonly":
                result = run_sql_readonly_connector(connector=connector, args=input_args, tool_name=tool_name)
            elif connector_type == "sql":
                result = run_sql_readonly_connector(connector=connector, args=input_args, tool_name=tool_name)
            else:
                raise ToolExecutionError(f"Unknown connector type for {tool_name}: {connector_type}")
        except ToolExecutionError:
            raise
        except Exception as exc:
            raise ToolExecutionError(f"Tool {tool_name} failed: {exc}") from exc

        result.setdefault("data", {})
        result.setdefault("rendered", str(result["data"]))
        result.setdefault("meta", {"duration_ms": 0, "source": connector_type})
        result["args"] = input_args
        if warnings:
            result["warnings"] = warnings
        return result
