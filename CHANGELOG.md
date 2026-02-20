# Changelog

All notable changes to the Universal Q&A Assistant Platform are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.1.0] — 2026-02-19

### Added

- **`/chat` endpoint** — intent routing, RAG how-to, stats tool calling, and security access summary.
- **`/health` endpoint** — liveness check returning version and build SHA.
- **`/readyz` endpoint** — readiness check reporting indexed chunk count.
- **`/packs` endpoint** — lists installed packs with keywords and tool metadata.
- **`/audit/{trace_id}` endpoint** — per-request structured audit event lookup.
- **`/admin/reindex` endpoint** — Admin-only endpoint to rebuild the doc index.
- **Pack model** — `ProductPack` interface with `keywords()`, `glossary()`, `doc_globs()`, `tools()`.
- **Hybrid retrieval** — BM25 lexical overlap + hash-embedding vector search with tunable `alpha`.
- **`HashEmbedder`** — zero-dependency deterministic embeddings using SHA-256 seeded RNG.
- **`SentenceTransformerEmbedder`** — optional higher-quality embeddings via `sentence-transformers`.
- **Policy engine** — YAML-driven RBAC (allowed packs/tools as glob patterns) and deny-phrase patterns.
- **Redaction** — email masking, long-ID masking, and optional small-count suppression.
- **Audit sinks** — in-memory (default) and JSONL file sink.
- **`SampleServicePack`** — reference pack with two mock stats tools and how-to docs.
- **Eval harness** — golden Q&A tests for how-to, stats, and security categories.
- **Pack scaffolding script** — `scripts/new_pack.py` for bootstrapping new packs.
- **Docker support** — `Dockerfile` + `docker-compose.yml` for zero-config startup.
- **`.env.example`** — documents all supported environment variables.

### Non-Goals (M1)

- No voice/multimodal runtime.
- No write-action tools.
- No enterprise SSO/IdP integration.
- No paid harness features (approvals, spend firewall).
