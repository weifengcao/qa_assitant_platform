PRD: Universal Q&A Assistant Platform (OSS Baseline) — Production Grade
1) Summary

Build an open-source, pack-based assistant platform that supports three pillars for any service:

How-to: answer “how do I…” using docs/runbooks with citations (RAG)

Stats: answer “what’s the count/latency/usage…” via read-only tool calls

Security: enforce tenant isolation + RBAC + safe output (redaction + policy denies)

Text-first. Designed so a future “AI harness” can wrap tool execution, policy, audit, approvals, spend controls later without refactoring (interfaces must stay stable).

2) Goals and Non-Goals
Goals (M1)

Provide a working platform that can be self-hosted and extended via “packs.”

Ship with:

RAG ingestion + retrieval + citations

Tool calling framework (JSON schema tools), read-only

Baseline RBAC & policy denies

Observability: request tracing + structured audit events

Simple evaluation hooks (golden tests) to detect regressions

Offer excellent OSS ergonomics:

docker compose up works

Adding a new pack is <30 minutes using a template

Non-Goals (M1)

No voice/multimodal runtime (only adapter interfaces/stubs)

No enterprise admin UI (config files + API only)

No write actions/tools (all tools read-only)

No paid harness features (approvals/spend firewall/policy console) in this repo

3) Target Users & Personas

OSS Builder: wants to create an assistant for a product and share with community.

Platform Engineer: wants internal assistant for ops/docs + metrics.

DevRel/PM: wants demos and quick onboarding via packs.

4) Core User Stories
How-to

As a user, I can ask “How do I rotate an API key?” and get steps with citations.

As a user, I can ask follow-ups and the assistant uses the same pack context.

Stats

As a user, I can ask “request volume last 24h?” and get a numeric answer from a tool call.

As a user, I can ask “p95 latency by service X” and tool args are validated.

Security

As an org admin, I can restrict which roles can access which packs/tools.

As a user, I get a clear denial message if I request forbidden actions (e.g., “export all IDs”).

As an org admin, I can enforce redaction of emails/IDs.

5) Product Requirements
5.1 API (HTTP)

Implement FastAPI endpoints:

GET /health

Returns { ok: true, version, build_sha }

GET /packs

Returns a list of installed packs (id, display_name, keywords, tools metadata)

POST /chat

Request

{
  "message": "string",
  "session_id": "optional string",
  "pack_hint": "optional string",
  "metadata": { "optional": "object" }
}


Headers

X-Org-Id (required)

X-User-Id (required)

X-Roles (comma separated, required)

Response

{
  "answer": "markdown string",
  "citations": [{"title": "...", "url": "...", "source": "...", "score": 0.0}],
  "actions": [{"tool": "pack.tool.name", "args": {}, "result_meta": {}}],
  "warnings": ["..."],
  "meta": {
    "trace_id": "...",
    "intent": "how_to|stats|security|mixed",
    "packs_used": ["..."],
    "latency_ms": 1234,
    "retrieval": {"backend": "hybrid", "alpha": 0.55, "top_k": 5},
    "tool_calls": 0
  }
}

GET /audit/{trace_id} (optional but strongly recommended)

Returns structured audit events for debugging.

5.2 Intent Routing

Classify every message into: how_to | stats | security | mixed.

Rules:

deterministic heuristic is acceptable for M1 (keywords)

must be unit-tested with a small suite

5.3 Packs (Extensibility Model)

Define a ProductPack interface with:

pack_id: str (globally unique)

display_name: str

keywords(): list[str] (routing)

doc_sources(): list[DocSource] (ingestion config; see below)

tools(): list[ToolDef] (read-only tools)

optional: glossary(): dict[str, list[str]]

Pack loading

load built-in packs from packs/

allow runtime pack enablement via config

Pack template

provide scripts/new_pack.py to scaffold a new pack

5.4 Document Ingestion (RAG)

Docs are ingested per (org_id, pack_id) into an index.

Supported sources (M1)

filesystem directory (required)

HTTP URL list (nice-to-have; can be stubbed)

Chunking requirements

chunk size default: 800–1200 tokens equivalent (approx by chars ok)

overlap default: 100–200 tokens equivalent

preserve headings/subheadings as metadata (improves RAG quality)

Indexing requirements

support DOC_INDEX_BACKEND=hybrid|vector_only

hybrid means BM25 + vector search with tunable alpha (0..1)

store per-chunk metadata: org_id, pack_id, source, url, title, section_heading, updated_at

Retrieval

filters must enforce org_id isolation and optional pack_id scope

return top K hits (default K=5) with:

snippet

url/title

score breakdown (bm25/vector optional)

Citation requirement

every how-to answer must include ≥1 citation unless no docs found (then warn)

RAG reliability

include “how it was generated” metadata in response for trust (citations + pack + backend)

5.5 Tool Calling (Stats Pillar)

Tools are defined via JSON schema (function/tool calling style).

ToolDef structure

name (namespaced, e.g. aep.stats.profile_count)

description

schema (JSON schema for args)

connector config (mock/http/sql/prometheus)

read_only: true (M1 hard requirement)

Tool execution

validate args against JSON schema (reject on mismatch)

enforce RBAC allowlist before executing tool

enforce rate limit per user/org (basic)

tool results must be sanitized (redaction pass)

LLM argument extraction (M1)

For baseline, you may implement:

a heuristic parser for tool args

OR a plug-in “LLM adapter” interface but keep it optional (no keys required to run)

Regardless, tool calling must be deterministic and testable.

5.6 Security (Baseline)

Implement a YAML policy file per deployment:

Policy supports

roles → allowed packs (glob patterns)

roles → allowed tools (glob patterns)

deny patterns (phrases like “export”, “download all”, “dump”)

redaction rules:

mask emails

mask long ids

suppress tiny counts (optional)

Enforcement

deny patterns are evaluated before retrieval/tool calls

RBAC is applied to:

pack routing results (remove packs user cannot access)

tool execution allowlists

Denial UX

return helpful safe alternative: “I can provide aggregates” etc.

5.7 Observability & Auditability

Must implement:

trace_id per request

structured audit events:

request received (user/org/roles)

intent

packs selected

retrieval query + top sources (metadata only)

tool calls (name, args summary, duration, status)

final response metadata (counts, warnings)

Audit sink:

default in-memory

optional file sink (AUDIT_SINK=file) writing JSONL to disk

5.8 Configuration

Support environment variables + config files:

POLICY_PATH

DATA_DIR

DOC_INDEX_BACKEND=hybrid|vector_only

EMBEDDING_BACKEND=hash|st

hash is zero-deps deterministic

st uses sentence-transformers (optional install)

Provide docker-compose.yml that works with defaults.

6) Non-Functional Requirements
Performance (baseline targets)

p50 /chat < 1.2s with small corpus (<2k chunks), hash embeddings

retrieval time < 150ms for in-memory index on small corpus

tool call overhead < 250ms for mock connector

Reliability

system must not crash on:

missing docs

malformed tool args (return warning)

unknown pack hints (fallback)

Security

strict org isolation for docs/tools (filters always applied)

never log raw message content in audit by default (store preview/hashed optional)

Portability

runs on Mac/Linux with docker compose

no mandatory external APIs to function

7) Data Model
Minimal persistent storage (M1)

To keep OSS simple, persistence can be:

file-based docs

optional Postgres for future backends

However, implement interfaces so Postgres/pgvector can be added without breaking changes.

Recommended tables (if implemented)

orgs/users/sessions/messages

doc_chunks (metadata + text)

tool_defs

audit_events (optional)

8) Evaluation & Testing (must-have)

RAG systems drift; include evaluation hooks.

Golden tests

Provide a eval/ folder:

howto_golden.json: Q → expected citation contains keyword(s)

stats_golden.json: Q → expected tool called

security_golden.json: Q → expected deny or allowed list

Run via:

python -m eval.run

CI checks (minimum)

unit tests for policy matching

unit tests for tool schema validation

smoke test for /health, /packs, /chat

9) UX / Output Guidelines

Always structure answers:

How-to: short steps + citations

Stats: value + timeframe + source tool

Security: clear allowed list + next steps

If no data: say what’s missing and how to configure it.

10) Open Source Packaging

License: Apache-2.0 (or MIT)

Provide:

CONTRIBUTING.md

SECURITY.md

CODE_OF_CONDUCT.md

pack template generator script

1–2 reference packs with docs + mock tools

11) Acceptance Criteria (Definition of Done)
Platform DoD

docker compose up starts API successfully

GET /packs returns installed packs

How-to query returns ≥1 citation when docs exist

Stats query executes a tool and returns result (and action record)

Forbidden “export/dump” query returns denial with warning

RBAC prevents executing tools not permitted for the role

Audit trace exists and is retrievable (in-memory or file sink)

Quality DoD

Test suite passes locally and in CI

Golden eval runner passes for sample pack

README includes:

quickstart

how to add docs

how to add a tool

how to create a new pack

12) Milestones (implementation order)
M1.0 Core skeleton (1–2 days)

API endpoints

policy engine + redaction

pack registry

in-memory audit

M1.1 RAG pipeline (2–4 days)

ingestion from filesystem

chunking

hybrid retrieval backend with hash embeddings by default

M1.2 Tools (2–4 days)

tool registry + schema validation

mock connector + 1 reference tool

basic arg extraction (heuristic)

M1.3 Evals + OSS polish (1–2 days)

golden tests

docs, contribution guides

13) Explicit “Harness later” constraints

To keep harness integration easy, Codex must:

route all tool calls through ToolRunner interface

route all policy decisions through PolicyEngine

emit audit events through AuditSink

keep response contract stable (answer/citations/actions/warnings/meta)