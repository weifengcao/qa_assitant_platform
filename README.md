# Universal Q&A Assistant Platform (OSS) — Baseline

A pack-based assistant platform that supports three pillars:
- **How-to** (RAG with citations)
- **Stats** (typed tool calls, read-only)
- **Security** (tenant isolation + RBAC + redaction)

This is **Milestone 1 (baseline)**: no external harness required. Designed to be wrapped by a harness later.

## Quickstart
```bash
docker compose up --build
```

API docs: http://localhost:8080/docs

## Try it
List packs:
```bash
curl -s http://localhost:8080/packs | jq
```

How-to:
```bash
curl -s http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -H "X-Org-Id: demo" \
  -H "X-User-Id: u1" \
  -H "X-Roles: Viewer" \
  -d '{"message":"How do I rotate an API key in this service?"}' | jq
```

Stats:
```bash
curl -s http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -H "X-Org-Id: demo" \
  -H "X-User-Id: u1" \
  -H "X-Roles: Viewer" \
  -d '{"message":"What is the request volume in the last 24h?"}' | jq
```

Security:
```bash
curl -s http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -H "X-Org-Id: demo" \
  -H "X-User-Id: u1" \
  -H "X-Roles: Viewer" \
  -d '{"message":"What can I access?"}' | jq
```

Inspect audit trace from a chat response:
```bash
curl -s http://localhost:8080/audit/<trace_id> | jq
```

## Configure
- Policy: `config/policy.yaml`
- Packs: `packs/` (Python modules) + sample docs under `data/`

## Notes
- Default doc index is **in-memory hybrid** (lexical overlap + deterministic embeddings) for ease of use.
- Postgres + pgvector is included in docker-compose; the pgvector index backend is scaffolded for later.
