import re
import uuid
from typing import Any, Dict, List, Optional

from app.core.intent import classify_intent, Intent
from app.core.packs import PackRegistry, filter_packs_for_user
from app.core.policy import PolicyEngine
from app.core.redaction import apply_redaction
from app.core.ingest import load_docs_from_globs
from app.core.audit import AuditEvent, InMemoryAuditSink
from app.core.doc_index import InMemoryDocIndex
from app.core.tools import ToolExecutionError, ToolRunner

_WORD_RE = re.compile(r"[a-z0-9_]+")


class Orchestrator:
    def __init__(
        self,
        pack_registry: PackRegistry,
        policy_engine: PolicyEngine,
        doc_index: InMemoryDocIndex,
        tool_runner: ToolRunner,
        audit_sink: InMemoryAuditSink,
        data_dir: str,
    ):
        self.packs = pack_registry
        self.policy = policy_engine
        self.doc_index = doc_index
        self.tool_runner = tool_runner
        self.audit = audit_sink
        self.data_dir = data_dir
        self._ingested: Dict[str, bool] = {}

        # Register pack tools into the shared registry once on startup.
        self._register_tools()

    def _register_tools(self) -> None:
        for pack in self.packs.list():
            for tool in pack.tools():
                self.tool_runner.registry.register(tool)

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

    def _select_tool(self, message: str, routed_packs: List[Any], allowed_patterns: List[str]) -> Optional[str]:
        msg = message.lower()
        tokens = self._tokenize(message)

        best_name: Optional[str] = None
        best_score = float("-inf")

        for pack in routed_packs:
            for tool in pack.tools():
                name = tool["name"]
                if not PolicyEngine.match_pattern(name, allowed_patterns):
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

    def handle_chat(self, user: Dict[str, Any], message: str, session_id: Optional[str], pack_hint: Optional[str]) -> Dict[str, Any]:
        trace_id = str(uuid.uuid4())
        org_id = user["org_id"]
        roles = user.get("roles", [])

        self.audit.log(
            trace_id,
            AuditEvent(
                kind="request",
                data={"user": user, "message": message, "session_id": session_id, "pack_hint": pack_hint},
            ),
        )

        if self.policy.is_denied(message):
            answer = "I can’t help with exporting or listing raw identifiers. I can answer how-to questions or provide aggregate stats if permitted."
            answer = apply_redaction(answer, self.policy.redaction())
            self.audit.log(trace_id, AuditEvent(kind="deny", data={"reason": "deny_patterns"}))
            return {
                "answer": answer,
                "citations": [],
                "actions": [],
                "warnings": ["Request blocked by policy (deny_patterns)."],
                "meta": {"trace_id": trace_id, "intent": Intent.SECURITY.value, "packs_used": []},
            }

        intent = classify_intent(message)

        routed = self.packs.route(message, pack_hint=pack_hint)
        routed = filter_packs_for_user(routed, policy=self.policy, roles=roles)
        packs_used = [pack.pack_id for pack in routed]

        self.audit.log(trace_id, AuditEvent(kind="intent", data={"intent": intent.value, "packs_used": packs_used}))

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

                if top:
                    answer_parts.append("### How-to")
                    answer_parts.append("Here’s what I found in the docs:")
                    for hit in top[:3]:
                        citations.append({"title": hit["title"], "url": hit["url"], "source": hit["source"]})
                    for idx, hit in enumerate(top[:3], start=1):
                        snippet = " ".join(hit["text"].strip().split())[:260]
                        answer_parts.append(f"{idx}. {snippet}")
                else:
                    warnings.append("No relevant docs found (add docs under data/<org>/<pack>/...).")

            if intent in (Intent.STATS, Intent.MIXED) and routed:
                allowed_tools = self.policy.allowed_tools(roles)
                tool_name = self._select_tool(message, routed, allowed_tools)

                if tool_name:
                    try:
                        result = self.tool_runner.call(tool_name, args={})
                        actions.append({"tool": tool_name, "args": {}})
                        answer_parts.append("### Stats")
                        answer_parts.append(result.get("rendered", str(result)))
                    except ToolExecutionError as exc:
                        warnings.append(str(exc))
                else:
                    warnings.append("No permitted stats tool matched your request.")

        citations = self._dedupe_citations(citations)
        warnings = sorted(set(warnings))

        answer = "\n".join(answer_parts).strip() or "I’m not sure how to answer that yet."
        answer = apply_redaction(answer, self.policy.redaction())

        self.audit.log(
            trace_id,
            AuditEvent(kind="response", data={"citations": len(citations), "actions": len(actions), "warnings": warnings}),
        )
        return {
            "answer": answer,
            "citations": citations,
            "actions": actions,
            "warnings": warnings,
            "meta": {"trace_id": trace_id, "intent": intent.value, "packs_used": packs_used},
        }
