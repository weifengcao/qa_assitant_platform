import re
import time
import uuid
from typing import Any, Dict, List, Optional, Set

from app.core.audit import new_audit_event
from app.core.audit_sinks import AuditSink
from app.core.doc_index import InMemoryDocIndex
from app.core.ingest import load_docs_from_globs
from app.core.intent import Intent, classify_intent
from app.core.packs import PackRegistry
from app.core.policy import PolicyEngine
from app.core.redaction import apply_redaction
from app.core.tools import ToolExecutionError, ToolRunner

_WORD_RE = re.compile(r"[a-z0-9_]+")


class Orchestrator:
    def __init__(
        self,
        pack_registry: PackRegistry,
        policy_engine: PolicyEngine,
        doc_index: InMemoryDocIndex,
        tool_runner: ToolRunner,
        audit_sink: AuditSink,
        data_dir: str,
        retrieval_backend: str = "hybrid",
    ):
        self.packs = pack_registry
        self.policy = policy_engine
        self.doc_index = doc_index
        self.tool_runner = tool_runner
        self.audit = audit_sink
        self.data_dir = data_dir
        self.retrieval_backend = retrieval_backend
        self._ingested: Dict[str, bool] = {}

        # Register pack tools into the shared registry once on startup.
        self._register_tools()

    def _register_tools(self) -> None:
        for pack in self.packs.list():
            for tool in pack.tools():
                self.tool_runner.registry.register(tool)

    def _audit(self, trace_id: str, kind: str, data: Dict[str, Any]) -> None:
        self.audit.log(new_audit_event(trace_id=trace_id, kind=kind, data=data))

    @staticmethod
    def _preview(text: str, max_chars: int = 180) -> str:
        compact = " ".join(text.split())
        if len(compact) <= max_chars:
            return compact
        return compact[: max_chars - 3] + "..."

    def _ensure_ingested(self, org_id: str, pack_id: str) -> None:
        key = f"{org_id}:{pack_id}"
        if self._ingested.get(key):
            return

        pack = self.packs.get(pack_id)
        if not pack:
            return

        docs = load_docs_from_globs(
            self.data_dir,
            org_id=org_id,
            pack_id=pack_id,
            globs=pack.doc_globs(),
        )
        if docs:
            self.doc_index.ingest(docs)
        self._ingested[key] = True

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return set(_WORD_RE.findall(text.lower()))

    @staticmethod
    def _dedupe_citations(citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        out: List[Dict[str, Any]] = []
        for citation in citations:
            key = (citation.get("title", ""), citation.get("url", ""), citation.get("source", ""))
            if key in seen:
                continue
            seen.add(key)
            out.append(citation)
        return out

    def _access_summary(self, roles: List[str]) -> List[str]:
        allowed_packs = self.policy.allowed_packs(roles)
        allowed_tools = self.policy.allowed_tools(roles)
        return [
            "### Access summary",
            f"- Roles: **{', '.join(roles) if roles else '(none)'}**",
            f"- Allowed packs: **{', '.join(allowed_packs) if allowed_packs else '(none)'}**",
            f"- Allowed tools: **{', '.join(allowed_tools) if allowed_tools else '(none)'}**",
        ]

    def _select_tool(self, message: str, routed_packs: List[Any], allowed_names: Set[str]) -> Optional[str]:
        msg = message.lower()
        tokens = self._tokenize(message)

        best_name: Optional[str] = None
        best_score = float("-inf")

        for pack in routed_packs:
            for tool in pack.tools():
                name = tool["name"]
                if name not in allowed_names:
                    continue

                score = 0.0
                if "stats" in name:
                    score += 0.2

                # Match explicit tool keywords first, then weaker token matches.
                for kw in tool.get("keywords", []):
                    keyword = str(kw).lower()
                    if keyword in msg:
                        score += 3.0
                    elif keyword in tokens:
                        score += 1.0

                score += sum(1.0 for tok in tokens if tok and tok in name)

                if ("how many" in msg or "count" in tokens) and any(k in name for k in ("count", "volume", "total")):
                    score += 2.0
                if "volume" in tokens and "volume" in name:
                    score += 2.5
                if "latency" in tokens and "latency" in name:
                    score += 2.5
                if "request" in tokens and "request" in name:
                    score += 1.5

                if score > best_score:
                    best_score = score
                    best_name = name

        return best_name

    def _build_meta(self, trace_id: str, intent: Intent, packs_used: List[str], tool_calls: int) -> Dict[str, Any]:
        alpha = 0.75 if self.retrieval_backend == "hybrid" else 1.0
        return {
            "trace_id": trace_id,
            "intent": intent.value,
            "packs_used": packs_used,
            "latency_ms": 0,
            "retrieval": {"backend": self.retrieval_backend, "alpha": alpha, "top_k": 5},
            "tool_calls": tool_calls,
        }

    def reindex(self, org_id: str, pack_id: Optional[str] = None) -> Dict[str, Any]:
        if pack_id:
            pack = self.packs.get(pack_id)
            if not pack:
                raise ValueError(f"Unknown pack_id: {pack_id}")
            target_pack_ids = [pack_id]
        else:
            target_pack_ids = [pack.pack_id for pack in self.packs.list()]

        removed_docs = 0
        for target_pack_id in target_pack_ids:
            self._ingested.pop(f"{org_id}:{target_pack_id}", None)
            removed_docs += self.doc_index.clear(filters={"org_id": org_id, "pack_id": target_pack_id})

        indexed_docs = 0
        for target_pack_id in target_pack_ids:
            self._ensure_ingested(org_id=org_id, pack_id=target_pack_id)
            indexed_docs += self.doc_index.count(filters={"org_id": org_id, "pack_id": target_pack_id})

        return {
            "org_id": org_id,
            "packs": target_pack_ids,
            "removed_docs": removed_docs,
            "indexed_docs": indexed_docs,
        }

    def handle_chat(
        self,
        user: Dict[str, Any],
        message: str,
        session_id: Optional[str],
        pack_hint: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        trace_id = str(uuid.uuid4())
        org_id = user["org_id"]
        user_id = user.get("user_id", "")
        roles = user.get("roles", [])
        redaction_rules = self.policy.redaction()
        message_preview = apply_redaction(self._preview(message), redaction_rules)

        self._audit(
            trace_id,
            "request_received",
            {
                "org_id": org_id,
                "user_id": user_id,
                "roles": roles,
                "session_id": session_id,
                "pack_hint": pack_hint,
                "message_preview": message_preview,
                "metadata": metadata or {},
            },
        )

        if self.policy.is_denied(message):
            answer = (
                "I cannot help with exporting or listing raw identifiers. "
                "I can provide aggregate stats and how-to guidance instead."
            )
            answer = apply_redaction(answer, redaction_rules)
            warnings = ["Request blocked by policy (deny_patterns)."]
            meta = self._build_meta(trace_id=trace_id, intent=Intent.SECURITY, packs_used=[], tool_calls=0)
            self._audit(trace_id, "denied", {"reason": "deny_patterns", "message_preview": message_preview})
            self._audit(
                trace_id,
                "response_returned",
                {"intent": Intent.SECURITY.value, "citations": 0, "tool_calls": 0, "warnings": warnings},
            )
            return {
                "answer": answer,
                "citations": [],
                "actions": [],
                "warnings": warnings,
                "meta": meta,
            }

        intent = classify_intent(message)
        self._audit(trace_id, "intent_classified", {"intent": intent.value})

        routed = self.packs.route(message, pack_hint=pack_hint)
        allowed_pack_ids = set(self.policy.filter_allowed_packs([pack.pack_id for pack in routed], roles))
        routed = [pack for pack in routed if pack.pack_id in allowed_pack_ids]
        packs_used = [pack.pack_id for pack in routed]
        self._audit(trace_id, "packs_selected", {"packs_used": packs_used, "pack_hint": pack_hint})

        for pack in routed:
            self._ensure_ingested(org_id, pack.pack_id)

        citations: List[Dict[str, Any]] = []
        actions: List[Dict[str, Any]] = []
        warnings: List[str] = []
        answer_parts: List[str] = []

        if pack_hint and not self.packs.get(pack_hint):
            warnings.append(f"Pack hint '{pack_hint}' was not found.")
        elif pack_hint and pack_hint not in packs_used and intent != Intent.SECURITY:
            warnings.append(f"Pack hint '{pack_hint}' is not accessible with your current roles.")

        if intent == Intent.SECURITY:
            answer_parts.extend(self._access_summary(roles))
        else:
            if not routed:
                warnings.append("No packs are accessible for your current roles.")
                answer_parts.extend(self._access_summary(roles))

            if intent in (Intent.HOW_TO, Intent.MIXED) and routed:
                hits: List[Dict[str, Any]] = []
                for pack in routed[:3]:
                    hits.extend(
                        self.doc_index.search(
                            message,
                            k=4,
                            filters={"org_id": org_id, "pack_id": pack.pack_id},
                        )
                    )

                hits.sort(key=lambda h: h["score"], reverse=True)
                top = [
                    hit
                    for hit in hits
                    if hit.get("lexical_score", 0.0) > 0.0 or hit["score"] > 0.2
                ][:5]

                top_sources = [
                    {
                        "title": hit.get("title", ""),
                        "url": hit.get("url", ""),
                        "source": hit.get("source", ""),
                        "score": round(float(hit.get("score", 0.0)), 4),
                    }
                    for hit in top
                ]
                self._audit(
                    trace_id,
                    "retrieval_performed",
                    {"query_preview": message_preview, "top_sources": top_sources},
                )

                if top:
                    answer_parts.append("### How-to")
                    answer_parts.append("Here's what I found in the docs:")
                    for hit in top[:3]:
                        citations.append(
                            {
                                "title": hit["title"],
                                "url": hit["url"],
                                "source": hit["source"],
                                "score": float(hit["score"]),
                            }
                        )
                    for idx, hit in enumerate(top[:3], start=1):
                        snippet = " ".join(hit["text"].strip().split())[:260]
                        answer_parts.append(f"{idx}. {snippet}")
                else:
                    warnings.append("No relevant docs found (add docs under data/<org>/<pack>/...).")

            if intent in (Intent.STATS, Intent.MIXED) and routed:
                pack_tool_names = [tool["name"] for pack in routed for tool in pack.tools()]
                allowed_tool_names = set(self.policy.filter_allowed_tools(pack_tool_names, roles))
                tool_name = self._select_tool(message, routed, allowed_tool_names)

                if tool_name:
                    start = time.perf_counter()
                    try:
                        result = self.tool_runner.call(tool_name, args={})
                        duration_ms = int((time.perf_counter() - start) * 1000)
                        rendered = apply_redaction(result.get("rendered", str(result)), redaction_rules)
                        actions.append(
                            {
                                "tool": tool_name,
                                "args": {},
                                "result_meta": result.get("meta", {"duration_ms": duration_ms}),
                            }
                        )
                        answer_parts.append("### Stats")
                        answer_parts.append(rendered)
                        self._audit(
                            trace_id,
                            "tool_called",
                            {"tool": tool_name, "args_summary": {}, "status": "ok", "duration_ms": duration_ms},
                        )
                    except ToolExecutionError as exc:
                        duration_ms = int((time.perf_counter() - start) * 1000)
                        warnings.append(str(exc))
                        self._audit(
                            trace_id,
                            "tool_called",
                            {
                                "tool": tool_name,
                                "args_summary": {},
                                "status": "error",
                                "duration_ms": duration_ms,
                                "error": str(exc),
                            },
                        )
                else:
                    warnings.append("No permitted stats tool matched your request.")

        citations = self._dedupe_citations(citations)
        warnings = sorted(set(warnings))

        answer = "\n".join(answer_parts).strip() or "I am not sure how to answer that yet."
        answer = apply_redaction(answer, redaction_rules)
        meta = self._build_meta(trace_id=trace_id, intent=intent, packs_used=packs_used, tool_calls=len(actions))

        self._audit(
            trace_id,
            "response_returned",
            {"intent": intent.value, "citations": len(citations), "tool_calls": len(actions), "warnings": warnings},
        )
        return {
            "answer": answer,
            "citations": citations,
            "actions": actions,
            "warnings": warnings,
            "meta": meta,
        }
