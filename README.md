# Universal Q&A Assistant Platform (OSS) - Baseline

A pack-based assistant platform with three pillars:
- **How-to**: RAG answers with citations.
- **Stats**: read-only tool calls with schema validation.
- **Security**: RBAC, deny patterns, and response redaction.

## Quickstart
```bash
docker compose up --build
```

API docs: http://localhost:8080/docs

## Development
```bash
pip install -r requirements-dev.txt
make test
make lint
make dev
```

## Try It
List packs:
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
  -d '{"message":"How do I rotate an API key in this service?"}' | jq
```

Stats query:
```bash
curl -s http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -H "X-Org-Id: demo" \
  -H "X-User-Id: u1" \
  -H "X-Roles: Viewer" \
  -d '{"message":"What is p95 latency last 24h?"}' | jq
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

Inspect audit trace:
```bash
curl -s http://localhost:8080/audit/<trace_id> | jq
```

Reindex docs for an org (Admin role required):
```bash
curl -s http://localhost:8080/admin/reindex \
  -H "Content-Type: application/json" \
  -H "X-Org-Id: demo" \
  -H "X-Roles: Admin" \
  -d '{"pack_id":"sample_service"}' | jq
```

## Add Docs
1. Add files under `data/<org_id>/<pack_id>/howto/` as `.md` or `.txt`.
2. Ensure the pack's `doc_globs()` includes those paths.
3. Reindex docs or issue a chat request to trigger lazy ingestion.

## Add Tools
1. Implement handler functions in `packs/<pack_id>/tools.py`.
2. Define `ToolDef` entries in `packs/<pack_id>/pack.py`.
3. Use JSON schema args and keep `read_only=True`.
4. Ensure connector type is one of `mock`, `http`, or `sql_readonly`.

## Add a Pack
1. Generate scaffold:
   `python scripts/new_pack.py --pack_id mypack --display_name "My Pack"`
2. Register `packs/mypack/pack.py` in `app/api.py`.
3. Add docs under `data/demo/mypack/howto/`.
4. Add tool handlers in `packs/mypack/tools.py`.

## Retrieval and Embeddings Backends
Environment variables:
- `DOC_INDEX_BACKEND=hybrid|vector_only`
- `DOC_INDEX_ALPHA=0.75` (hybrid only)
- `EMBEDDING_BACKEND=hash|st`
- `DATA_DIR=...`
- `POLICY_PATH=...`

Defaults are zero-dependency:
- `DOC_INDEX_BACKEND=hybrid`
- `EMBEDDING_BACKEND=hash`

`EMBEDDING_BACKEND=st` requires `sentence-transformers` installation.

## Run Evals
```bash
python -m eval.run
```

Golden files:
- `eval/howto_golden.json`
- `eval/stats_golden.json`
- `eval/security_golden.json`

## Baseline Security Posture
What baseline does:
- Applies deny patterns before retrieval or tool execution.
- Filters packs and tools by role-based allowlists.
- Redacts emails and long identifiers in responses and audit previews.
- Supports optional small-count suppression.

What baseline does not do:
- No enterprise authn/authz integration out of the box.
- No secret management or key rotation automation.
- No write-action tools in M1.

Production deployments should add stronger authentication, hardened secrets handling, network controls, and centralized audit retention.
