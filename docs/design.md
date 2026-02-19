# Universal Q&A Assistant Platform Design

## 1. Overview
Build a universal, OSS Q&A assistant platform for any product or internal service stack.

Core strategy:
- RAG for documentation and runbook questions
- Tool calling for live stats and status
- Connector packs for extensibility
- Permission enforcement and response safety by default
- Observability for production use

The architecture keeps a clean pack/connector boundary so a future Harness integration can be added without major refactoring.

This document describes the target architecture and the Milestone 1 baseline currently implemented in this repository.

## 2. Product Goal
Enable contributors to deploy a production-style assistant with three pillars:

1. `How-to`: answer "how do I..." from docs and runbooks with citations.
2. `Stats`: answer "status/count/latency/usage..." using read-only tools.
3. `Security`: enforce org/user permissions and reduce sensitive leakage (RBAC + redaction baseline).

Initial modality is text-first, with planned adapters for voice and multimodal input.

## 3. Current Industry Pattern
The platform follows the dominant enterprise assistant blueprint:

1. Intent routing: `how_to | stats | security | mixed`
2. RAG for how-to: hybrid retrieval (`BM25 + embeddings`) with reranking
3. Tool calling for stats: typed tools with JSON Schemas
4. Policy checks before retrieval/tool execution: RBAC + tenant scope
5. Stable response contract: `answer + citations + actions + warnings`

## 4. High-Level Architecture
### Runtime Components
- **API Gateway (`FastAPI`)**: exposes `/chat`, `/packs`, `/health`, and `/audit/{trace_id}`.
- **Orchestrator**: intent classifier, planner (retrieval vs tool calls), and response composer.
- **Knowledge Service (RAG)**: ingestion pipeline, chunking/embeddings, hybrid retrieval, and reranking.
- **Tool Service**: tool registry, schema validation, and connectors (`HTTP`, read-only `SQL`, `Prometheus`, etc.).
- **AuthZ / Security Service**: identity mapping, RBAC/resource scoping, and "no raw export" redaction rules.
- **Storage Layer**: Postgres for metadata/state, vector DB (`pgvector` default or `Qdrant`), and Redis for cache/rate limits.

### Optional Later Additions
- Voice adapter (`STT/TTS`)
- Multimodal adapter (images/screenshots for UI-guided how-to)
- Harness integration (capabilities, audit, spend controls, approvals)

## 5. Key Product Concepts
### 5.1 Connector Packs (Primary OSS Extensibility)
A pack is the extension unit for a new product or service.

Each pack can provide:
- Documentation sources (`URLs`, `GitHub`, `Confluence`, `PDFs`)
- Read-only tools (metrics/status queries)
- Security bindings (role/resource mapping)
- Glossary and synonyms (better routing and retrieval)

### 5.2 Tenant Isolation
All operations are scoped by:
- `org_id`
- Optional `workspace_id` / `project_id`

Tools and documents are always resolved within tenant scope.

### 5.3 Safety Baseline (Without Harness)
Baseline controls for OSS adoption:
- RBAC (`role -> allowed packs/tools/datasets`)
- Retrieval filtering by org/doc collection
- PII redaction in responses and logs
- Configurable deny patterns for raw exports/raw IDs
- Tool allowlist by role

## 6. Data Model (MVP)
### Postgres Tables
- `orgs(id, name, created_at)`
- `users(id, org_id, email, roles[], created_at)`
- `sessions(id, org_id, user_id, created_at)`
- `messages(id, session_id, role, content, created_at)`
- `doc_sources(id, org_id, pack_id, type, config_json, created_at)`
- `documents(id, org_id, source_id, title, url, hash, created_at)`
- `chunks(id, document_id, chunk_index, text, metadata_json)`
- `tools(id, org_id, pack_id, name, schema_json, config_json, read_only_bool)`
- `policies(id, org_id, version, policy_yaml, active_bool)`

### Vector Store
- Embeddings for `chunks`, always filterable by `org_id`

## 7. API Contract
Stable contract designed to map to future Harness audit/action semantics.

### `/chat` Request (Milestone 1 Baseline)
Identity and tenant scope are provided via headers:
- `X-Org-Id`
- `X-User-Id`
- `X-Roles` (comma-separated)

Body:
```json
{
  "session_id": "s1",
  "message": "How many profiles are in sandbox prod?",
  "pack_hint": "sample_service"
}
```

### `/chat` Response
```json
{
  "answer": "...",
  "citations": [
    { "title": "...", "url": "...", "source": "..." }
  ],
  "actions": [
    {
      "tool": "aep.stats.profile_count",
      "args": { "sandbox": "prod" }
    }
  ],
  "warnings": ["..."],
  "meta": {
    "trace_id": "c4a5b4e7-....",
    "intent": "stats",
    "packs_used": ["sample_service"],
    "latency_ms": 842
  }
}
```

## 8. RAG Design
### Ingestion
- `HTML -> Markdown`
- `PDF -> text` extraction (optional)
- Milestone 1 baseline: word-window chunking (overlap) for lightweight indexing
- Target production profile: ~`500-1000` token chunks with overlap
- Persist metadata: `url`, `heading`, `version`, `timestamp`

### Retrieval
- Milestone 1 baseline: in-memory hybrid scoring (`lexical overlap + deterministic embedding similarity`)
- Target production profile: `BM25 + embeddings` with rerank (`top 20 -> top 5`)
- Always return citations

### Answering
- Cite-first generation grounded in retrieved chunks
- If context is insufficient, ask targeted follow-up questions or suggest exact docs to check

## 9. Tooling Design (Stats Pillar)
Tools are typed and read-only by default.

Each tool includes:
- `tool_name`
- JSON Schema
- Connector config (`HTTP`, `SQL query template`, `PromQL template`)

Execution flow:
1. Parse tool arguments via structured LLM output
2. Validate against JSON Schema
3. Run RBAC/policy checks and select best permitted tool by intent/keyword match
4. Execute connector (read-only by default)
5. Post-process (units, rounding, suppression)
6. Compose response

## 10. Security Design (Baseline)
### RBAC Policy (YAML)
- `roles -> allowed packs`
- `roles -> allowed tools` (glob patterns)
- `roles -> allowed resource filters` (sandbox/project scopes)
- Redaction settings (mask emails/IDs; suppress small counts)

### Response Safety
- PII redaction pass
- Small-count suppression
- Deny patterns for "export/list raw IDs" (phrase matching; optional regex with `re:` prefix)

This baseline is sufficient for OSS and leaves room for Harness as a richer control plane later.

## 11. OSS Packaging and Developer Experience
### Community-Usable Defaults
- `docker compose up` starts: API + Postgres + Redis + Vector DB
- Single `config.yaml` defines docs sources, tools, and policy roles
- Pack scaffolding template (`cookiecutter` or script)
- Example packs: `github`, `datadog`, `jira`

## 12. Recommended Stack
- FastAPI + Pydantic
- Postgres + pgvector (default) or Qdrant
- Redis
- Background jobs: Celery/RQ or asyncio worker

## 13. MVP Scope
### Must Have
- `/chat` with intent routing
- RAG ingestion/retrieval with citations
- Tool registry with at least 2 sample tools
- RBAC allowlist + basic redaction
- Pack interface + 1 sample pack

### Next
- Admin endpoints (`upload docs`, `register tools`, `view logs`)
- Eval harness (golden Q&A tests per pack)
- UI (simple Next.js app)

## 14. Baseline Implementation Notes (Current Repo)
- Docs are ingested on demand per `org_id + pack_id` and cached in-memory.
- The default index backend is `InMemoryDocIndex` with lightweight hybrid scoring.
- Tool execution is schema-validated and returns typed execution errors rather than hard failures.
- The API exposes per-trace audit logs through `/audit/{trace_id}` for debugging and observability.
