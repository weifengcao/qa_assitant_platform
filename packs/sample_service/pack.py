from typing import Dict, Any, List
from app.core.packs import ProductPack
from packs.sample_service.tools import stats_request_volume_24h, stats_p95_latency_24h

class SampleServicePack(ProductPack):
    pack_id = "sample_service"
    display_name = "Sample Service Pack"

    def keywords(self) -> List[str]:
        return ["api key", "rate limit", "request volume", "latency", "sample service"]

    def doc_globs(self) -> List[str]:
        return ["howto/**/*.md", "howto/**/*.txt"]

    def tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "sample.stats.request_volume_24h",
                "schema": {"type": "object", "properties": {}, "additionalProperties": False},
                "connector": {"type": "mock", "handler": stats_request_volume_24h},
            },
            {
                "name": "sample.stats.p95_latency_24h",
                "schema": {"type": "object", "properties": {}, "additionalProperties": False},
                "connector": {"type": "mock", "handler": stats_p95_latency_24h},
            },
        ]
