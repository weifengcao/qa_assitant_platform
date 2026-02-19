from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


IntentValue = Literal["how_to", "stats", "security", "mixed"]


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=4000)
    session_id: Optional[str] = Field(default=None, max_length=128)
    pack_hint: Optional[str] = Field(default=None, max_length=128)
    metadata: Optional[Dict[str, Any]] = Field(default=None)


class Citation(BaseModel):
    title: str
    url: str
    source: str
    score: Optional[float] = None


class ActionRecord(BaseModel):
    tool: str
    args: Dict[str, Any] = Field(default_factory=dict)
    result_meta: Optional[Dict[str, Any]] = None


class ChatMeta(BaseModel):
    trace_id: str
    intent: IntentValue
    packs_used: List[str] = Field(default_factory=list)
    latency_ms: int = 0
    retrieval: Dict[str, Any] = Field(default_factory=dict)
    tool_calls: int = 0


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    actions: List[ActionRecord] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    meta: ChatMeta
