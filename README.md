# Universal Q&A Assistant Platform (OSS Baseline)

Build a production-style assistant that is **pack-based**, **self-hostable**, and centered on three pillars:

- **How-to**: doc-grounded answers with citations (RAG)
- **Stats**: deterministic, schema-validated read-only tool calls
- **Security**: RBAC, deny patterns, and output redaction by default

This repo is designed as an OSS baseline that runs without external proprietary services.

## Why This Repo

- Stable `/chat` contract ready for future harness integrations
- Clear separation between packs, retrieval, policy, and tool execution
- Works with local docs and mock tools out of the box
- Includes tests + eval harness to catch regressions

## Core Capabilities

1. **Pack model** for adding product-specific docs and tools quickly
1. **Hybrid retrieval** (`lexical + vector`) and `vector_only` mode
1. **Typed tools** with JSON Schema validation and deterministic argument extraction
1. **Policy engine** for allowed packs/tools + deny phrases + redaction
1. **Audit events** for request lifecycle tracing

## Architecture at a Glance

- API: `FastAPI` endpoints (`/health`, `/packs`, `/chat`, `/audit/{trace_id}`, `/admin/reindex`)
- Orchestrator: intent routing + policy checks + retrieval + tool execution + response shaping
- Retrieval: chunking + embedding + in-memory index backends
- Tools: registry + connectors (`mock`, `http` stub, `sql_readonly` stub)
- Security: RBAC filtering, deny rules, and redaction pass

## Quickstart

Run with Docker:

```bash
docker compose up --build
```

API docs:

- http://localhost:8080/docs

## Local Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
make test
make lint
make dev
```

## API Examples

List installed packs:

```bash
curl -s http://localhost:8080/packs | jq
```

How-to query:

```bash
curl -s http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -H "X-Org-Id: demo" \
  -H "X-User-Id: u1" \
  -H "X-Roles: Viewer" \
  -d '{"message":"How do I rotate an API key?"}' | jq
```

Stats query:

```bash
curl -s http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -H "X-Org-Id: demo" \
  -H "X-User-Id: u1" \
  -H "X-Roles: Viewer" \
  -d '{"message":"What is p95 latency last 24h for service auth in prod?"}' | jq
```

Security query:

```bash
curl -s http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -H "X-Org-Id: demo" \
  -H "X-User-Id: u1" \
  -H "X-Roles: Viewer" \
  -d '{"message":"What can I access?"}' | jq
```

Fetch audit events by trace id:

```bash
curl -s http://localhost:8080/audit/<trace_id> | jq
```

## Example `/chat` Response Shape

```json
{
  "answer": "### How-to\n...\n### Stats\n...",
  "citations": [
    { "title": "rotating_api_keys.md", "url": "data/demo/sample_service/howto/rotating_api_keys.md", "source": "sample_service docs", "score": 0.77 }
  ],
  "actions": [
    { "tool": "sample.stats.request_volume_24h", "args": { "timeframe": "24h" }, "result_meta": { "duration_ms": 3, "source": "sample_service_metrics" } }
  ],
  "warnings": [],
  "meta": {
    "trace_id": "uuid",
    "intent": "mixed",
    "packs_used": ["sample_service"],
    "latency_ms": 120,
    "retrieval": { "backend": "hybrid", "alpha": 0.75, "top_k": 5 },
    "tool_calls": 1
  }
}
```

## Configuration

See `.env.example` for a complete list of environment variables. Copy it to `.env` to customize your local overrides.

Key environment variables:

- `POLICY_PATH` (default: `config/policy.yaml`)
- `DATA_DIR` (default: `data`)
- `AUDIT_SINK` (`memory` or `file`)
- `AUDIT_FILE_PATH` (used when `AUDIT_SINK=file`)
- `DOC_INDEX_BACKEND` (`hybrid` or `vector_only`)
- `DOC_INDEX_ALPHA` (hybrid weighting, default `0.75`)
- `EMBEDDING_BACKEND` (`hash` or `st`)

Notes:

- `EMBEDDING_BACKEND=hash` is zero-dependency and deterministic
- `EMBEDDING_BACKEND=st` requires `sentence-transformers` installation

## Add Docs, Tools, and Packs

Add docs:

1. Put files under `data/<org_id>/<pack_id>/howto/` (`.md` or `.txt`)
1. Confirm pack `doc_globs()` includes the files
1. Query `/chat` (lazy ingest) or call `/admin/reindex`

Add tools:

1. Implement handlers in `packs/<pack_id>/tools.py`
1. Register `ToolDef` entries in `packs/<pack_id>/pack.py`
1. Keep tools read-only for M1

Scaffold a new pack:

```bash
python scripts/new_pack.py --pack_id mypack --display_name "My Pack"
```

Then register the new pack class in `app/api.py`.

## Quality Gates

Run tests:

```bash
make test
```

Run lint + type-check:

```bash
make lint
make typecheck
```

Run golden eval harness:

```bash
make eval
```

Golden datasets:

- `eval/howto_golden.json`
- `eval/stats_golden.json`
- `eval/security_golden.json`

## Baseline Security Scope

What baseline includes:

- Deny pattern checks before retrieval/tooling
- RBAC allowlists for packs and tools
- Email/long-id redaction and optional small-count suppression

What baseline does not include:

- Enterprise SSO/IdP integration
- Secrets lifecycle management
- Write-action tools

For production, add stronger authn/authz, secret handling, network controls, and centralized audit retention.
