from typing import List

from app.core.packs import ProductPack
from app.core.tools import ToolDef

from packs.sample_service.tools import stats_p95_latency_24h, stats_request_volume_24h


class SampleServicePack(ProductPack):
    pack_id = "sample_service"
    display_name = "Sample Service Pack"

    def keywords(self) -> List[str]:
        return ["api key", "rate limit", "request volume", "latency", "sample service"]

    def doc_globs(self) -> List[str]:
        return ["howto/**/*.md", "howto/**/*.txt"]

    def tools(self) -> List[ToolDef]:
        return [
            ToolDef(
                name="sample.stats.request_volume_24h",
                description="Return request volume over a timeframe.",
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
                keywords=["request volume", "volume", "traffic", "requests"],
                default_args={"timeframe": "24h", "metric": "request_volume"},
                connector={"type": "mock", "handler": stats_request_volume_24h},
            ),
            ToolDef(
                name="sample.stats.p95_latency_24h",
                description="Return p95 latency over a timeframe.",
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
                keywords=["latency", "p95", "response time"],
                default_args={"timeframe": "24h", "metric": "p95_latency"},
                connector={"type": "mock", "handler": stats_p95_latency_24h},
            ),
        ]
