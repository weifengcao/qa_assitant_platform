import uuid
from typing import Dict, Any, Optional, List

from app.core.intent import classify_intent, Intent
from app.core.packs import PackRegistry, filter_packs_for_user
from app.core.policy import PolicyEngine
from app.core.redaction import apply_redaction
from app.core.ingest import load_docs_from_globs
from app.core.audit import AuditEvent, InMemoryAuditSink
from app.core.doc_index import InMemoryDocIndex
from app.core.tools import ToolRunner, ToolRegistry

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

        # Register pack tools into global registry on startup
        self._register_tools()

    def _register_tools(self) -> None:
        # Packs can attach tools via their definition; we register them once.
        # Tool handlers are Python callables in baseline sample packs.
        for p in self.packs.list():
            for t in p.tools():
                self.tool_runner.registry.register(t)

    def _ensure_ingested(self, org_id: str, pack_id: str) -> None:
        key = f"{org_id}:{pack_id}"
        if self._ingested.get(key):
            return
        pack = self.packs.get(pack_id)
        if not pack:
            return
        docs = load_docs_from_globs(self.data_dir, org_id=org_id, pack_id=pack_id, globs=pack.doc_globs())
        if docs:
            self.doc_index.ingest(docs)
        self._ingested[key] = True

    def handle_chat(self, user: Dict[str, Any], message: str, session_id: Optional[str], pack_hint: Optional[str]) -> Dict[str, Any]:
        trace_id = str(uuid.uuid4())
        org_id = user["org_id"]
        roles = user.get("roles", [])

        self.audit.log(trace_id, AuditEvent(kind="request", data={"user": user, "message": message, "session_id": session_id, "pack_hint": pack_hint}))

        # Security deny patterns
        if self.policy.is_denied(message):
            ans = "I can’t help with exporting or listing raw identifiers. I can answer how-to questions or provide aggregate stats if permitted."
            ans = apply_redaction(ans, self.policy.redaction())
            self.audit.log(trace_id, AuditEvent(kind="deny", data={"reason": "deny_patterns"}))
            return {
                "answer": ans,
                "citations": [],
                "actions": [],
                "warnings": ["Request blocked by policy (deny_patterns)."],
                "meta": {"trace_id": trace_id, "intent": "security", "packs_used": []},
            }

        intent = classify_intent(message)
        routed = self.packs.route(message, pack_hint=pack_hint)
        routed = filter_packs_for_user(routed, policy=self.policy, roles=roles)
        packs_used = [p.pack_id for p in routed]

        self.audit.log(trace_id, AuditEvent(kind="intent", data={"intent": intent.value, "packs_used": packs_used}))

        # Ensure docs ingested for routed packs
        for p in routed:
            self._ensure_ingested(org_id, p.pack_id)

        citations: List[Dict[str, Any]] = []
        actions: List[Dict[str, Any]] = []
        warnings: List[str] = []
        answer_parts: List[str] = []

        if intent in (Intent.SECURITY,):
            allowed_packs = self.policy.allowed_packs(roles)
            allowed_tools = self.policy.allowed_tools(roles)
            answer_parts.append("### Access summary\n")
            answer_parts.append(f"- Roles: **{', '.join(roles) if roles else '(none)'}**\n")
            answer_parts.append(f"- Allowed packs: **{', '.join(allowed_packs) if allowed_packs else '(none)'}**\n")
            answer_parts.append(f"- Allowed tools: **{', '.join(allowed_tools) if allowed_tools else '(none)'}**\n")
        else:
            if intent in (Intent.HOW_TO, Intent.MIXED):
                # Retrieve top docs from each pack (simple filter)
                hits = []
                for p in routed[:2]:
                    hits.extend(self.doc_index.search(message, k=3, filters={"org_id": org_id, "pack_id": p.pack_id}))
                hits.sort(key=lambda h: h["score"], reverse=True)
                top = hits[:5]
                if top:
                    answer_parts.append("### How-to\n")
                    answer_parts.append("Here’s what I found in the docs:\n")
                    for h in top[:3]:
                        citations.append({"title": h["title"], "url": h["url"], "source": h["source"]})
                    # Baseline: just summarize via extracted snippets
                    for i, h in enumerate(top[:3], start=1):
                        snippet = h["text"].strip().splitlines()
                        snippet = " ".join(snippet[:3])[:240]
                        answer_parts.append(f"{i}. {snippet}\n")
                else:
                    warnings.append("No relevant docs found (try adding docs under data/<org>/<pack>/...).")

            if intent in (Intent.STATS, Intent.MIXED):
                # Pick first pack with a matching tool pattern (baseline heuristic)
                allowed_tools = self.policy.allowed_tools(roles)
                tool_name = None
                for p in routed:
                    for t in p.tools():
                        name = t["name"]
                        if PolicyEngine.match_pattern(name, allowed_tools):
                            # naive keyword match for volume/latency
                            if "volume" in message.lower() and "volume" in name:
                                tool_name = name
                                break
                            if "latency" in message.lower() and "latency" in name:
                                tool_name = name
                                break
                            if tool_name is None and "stats" in name:
                                tool_name = name
                    if tool_name:
                        break

                if tool_name:
                    # Baseline args are fixed; in real version use LLM structured output
                    res = self.tool_runner.call(tool_name, args={})
                    actions.append({"tool": tool_name, "args": {}})
                    answer_parts.append("\n### Stats\n")
                    answer_parts.append(res.get("rendered", str(res)))
                else:
                    warnings.append("No permitted stats tool matched your request.")

        answer = "\n".join(answer_parts).strip() or "I’m not sure how to answer that yet."
        answer = apply_redaction(answer, self.policy.redaction())

        self.audit.log(trace_id, AuditEvent(kind="response", data={"citations": len(citations), "actions": len(actions), "warnings": warnings}))
        return {
            "answer": answer,
            "citations": citations,
            "actions": actions,
            "warnings": warnings,
            "meta": {"trace_id": trace_id, "intent": intent.value, "packs_used": packs_used},
        }
