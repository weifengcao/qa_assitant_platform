# Universal Q&A Assistant Platform (OSS) — PRD (Milestone 1 Baseline)

## Goal
Provide an open-source platform to build **product/service assistants** with three pillars:
1) **How-to**: grounded answers from docs/runbooks with citations (RAG).
2) **Stats**: read-only operational or product metrics via typed tools/connectors.
3) **Security**: baseline tenant isolation + RBAC + response redaction.

Text-first. Architecture must make later “harness integration” a drop-in upgrade (capabilities, audit, spend, approvals), but Milestone 1 ships without it.

## Target users
- OSS community building assistants for internal tools/products
- DevRel teams publishing “assistant for our product”
- Platform engineers wanting a reference implementation

## Non-goals (Milestone 1)
- No enterprise policy admin UI (just YAML config)
- No voice/multimodal runtime (adapters are stubs only)
- No full eval/benchmark suite (basic tests only)
- No write actions/tools (read-only tools only)

## Product experience
### Inputs
- org/user identity (simple header-based auth for OSS demo)
- optional pack hint
- user message

### Outputs
- answer (markdown)
- citations (title/url/source)
- actions (tool calls)
- warnings (policy or safety notes)
- meta (intent, packs used, trace id, latency)

## Core capabilities
### 1) Packs
A **pack** is the unit of extensibility:
- docs sources (local folder, URLs, GitHub, etc.)
- tools (typed JSON schema tools)
- domain keywords for routing

### 2) RAG (How-to)
- ingest docs (markdown/html/text)
- chunk + embed
- Milestone 1 baseline: lightweight hybrid retrieval (lexical overlap + deterministic embedding similarity)
- future profile: BM25 + vector retrieval + reranking
- citations required

### 3) Tools (Stats)
- tools are described with name + JSON schema + connector config
- tool selection uses intent + keyword matching, then enforces RBAC allowlists
- connectors include HTTP + mock; SQL/Prometheus are stubs

### 4) Security
- org isolation for docs/tools
- RBAC: role -> allowed packs/tools
- deny patterns: “export raw IDs”, “download all”, etc. (phrase matching; optional regex via `re:` prefix)
- redaction pass (emails, long ids)

## Success criteria (Milestone 1)
- `docker compose up` brings up API + Postgres (pgvector) + Redis
- sample pack works end-to-end:
  - “how-to” query returns citations
  - “stats” query calls tool and returns result
  - “security” query explains allowed packs/tools
- traceability endpoint `/audit/{trace_id}` returns request/intent/response events
- adding a new pack is <30 minutes with template

## Milestone plan
- M1: baseline platform (this repo)
- M2: harness integration (capabilities/audit/spend/approvals) as a wrapper layer around the same interfaces
