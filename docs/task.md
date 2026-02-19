CODING_TASKS.md — Universal Q&A Assistant Platform (OSS Baseline)
Conventions

Language: Python 3.11

Framework: FastAPI

Style: type hints everywhere, small modules, no circular imports

All public outputs must conform to the /chat response schema in PRD

Add unit tests under tests/

Add a small eval runner under eval/

0) Repo hygiene (must do first)
0.1 Add OSS meta files

 Create LICENSE (Apache-2.0 or MIT)

 Create CONTRIBUTING.md (how to run, how to add packs)

 Create SECURITY.md (how to report vulnerabilities)

 Create CODE_OF_CONDUCT.md (Contributor Covenant)

0.2 Tooling

 Add pyproject.toml (ruff + mypy + pytest config)

 Add requirements-dev.txt (pytest, ruff, mypy, httpx)

 Add Makefile targets:

make dev (uvicorn)

make test

make lint

Acceptance

make test passes (even if minimal tests)

make lint passes

1) Define stable API schemas (Pydantic models)
1.1 Add schema models

File: app/core/schemas.py

 ChatRequest (message, session_id?, pack_hint?, metadata?)

 Citation (title, url, source, score?)

 ActionRecord (tool, args, result_meta?)

 ChatMeta (trace_id, intent, packs_used, latency_ms, retrieval, tool_calls)

 ChatResponse (answer, citations, actions, warnings, meta)

1.2 Update API to use schemas

File: app/api.py

 Replace inline models with app/core/schemas.py

 Ensure response always includes all meta fields

Acceptance

OpenAPI /docs shows proper request/response schemas

/chat always returns valid ChatResponse

2) Production-grade policy engine + RBAC
2.1 Policy engine enhancements

File: app/core/policy.py

 Add explicit Policy dataclass / typed structure

 Support glob patterns:

exact match

prefix match x.*

wildcard *

 Add method filter_allowed_tools(tool_names, roles) -> list[str]

 Add method filter_allowed_packs(pack_ids, roles) -> list[str]

 Add deny pattern matching:

case-insensitive

supports substring match (M1)

 Add optional suppress_small_counts config

2.2 Redaction pass improvements

File: app/core/redaction.py

 Add:

email masking

long id masking

optional numeric suppression for small counts (e.g. if value < N, replace with “<N”)

 Ensure redaction applies to:

final answer

tool results rendered text (before merging)

audit previews

Acceptance

Unit tests:

roles allow/deny packs/tools correctly

deny patterns block properly

redaction masks emails + long ids

3) Observability: audit sink + trace events
3.1 Audit event schema

File: app/core/audit.py

 Define AuditEvent with:

timestamp

trace_id

kind

data (dict)

 Ensure every /chat logs:

request_received

intent_classified

packs_selected

retrieval_performed (if any)

tool_called (if any)

response_returned

denied (if denied)

3.2 Add File audit sink

File: app/core/audit_sinks.py

 InMemoryAuditSink (existing)

 FileAuditSink(path: str) writing JSONL

 AuditSink interface/protocol

3.3 Add endpoint

File: app/api.py

 Add GET /audit/{trace_id} returning audit events (if sink supports lookup; file sink can return “not supported”)

Acceptance

/chat returns a trace_id

/audit/{trace_id} returns an ordered list of events (in-memory mode)

4) RAG pipeline: ingestion + chunking + hybrid retrieval
4.1 DocSource model

File: app/core/docsources.py

 Define DocSource types:

filesystem directory (required)

URL list (stub OK)

 Each doc source must include:

org_id, pack_id, type, config

4.2 Chunker implementation

File: app/core/chunking.py

 Implement chunker:

chunk_size_chars default ~ 3500–5000

overlap_chars default ~ 500–800

 Preserve headings:

parse markdown headings #, ##, ###

attach section_heading metadata to chunks

4.3 Ingestion pipeline

File: app/core/ingest.py

 Refactor to:

load docs

chunk docs into chunks

pass chunks to doc index backend

 Each chunk must store metadata:

org_id, pack_id, title, url, source, section_heading, updated_at

4.4 Retrieval backend cleanup

File: app/core/doc_index.py

 Keep:

InMemoryDocIndex (vector-only)

HybridDocIndex (BM25 + vector)

 Add standard interface:

ingest(chunks)

search(query, filters, top_k)

4.5 Embedding backends

File: app/core/embeddings.py

 Keep:

HashEmbedder (default)

SentenceTransformerEmbedder (optional)

 Ensure embedder returns normalized vectors

Acceptance

With sample docs, “rotate API key” returns citations to the correct doc file

Retrieval returns top_k with score and optionally bm25/vector

5) Tooling system: registry + connectors + deterministic arg parsing
5.1 ToolDef schema

File: app/core/tools.py

 Define ToolDef typed structure:

name, description, schema, connector, read_only=True

 Ensure registry registers tools from packs at startup

5.2 Connectors

Create folder: app/connectors/

 mock.py (call Python callable)

 http.py (stub OK, but implement interface)

 sql_readonly.py (stub OK)

 All connectors return:

data (raw dict)

rendered (human string)

meta (duration_ms, source)

5.3 Deterministic arg extraction (M1)

File: app/core/tool_args.py

 Implement heuristic arg extraction for common stats queries:

timeframe detection (24h, 7d)

metric selection keywords (volume, latency, errors)

optional dimension extraction (service X, sandbox prod)

 If args cannot be extracted, call tool with defaults or return warning

 All tool args must validate against JSON schema

Acceptance

“request volume last 24h” triggers *.request_volume_24h

“p95 latency last 24h” triggers *.p95_latency_24h

invalid args are rejected with a warning, not a crash

6) Orchestrator: stable 3-pillar behavior + response formatting
6.1 Orchestrator refactor

File: app/core/orchestrator.py

 Ensure steps:

generate trace_id

apply deny patterns

classify intent

route packs (+ pack_hint)

RBAC filter packs/tools

ingestion ensure (lazy or eager)

how-to retrieval + answer synthesis (M1: structured snippet summary)

stats tool selection + execution

security response builder

redaction + warnings

emit audit events

return ChatResponse

6.2 Answer formatting rules

How-to:

header “### How-to”

3–5 bullet/step items

citations list

Stats:

header “### Stats”

include timeframe + tool name in answer

Security:

header “### Access summary”

list roles, allowed packs/tools

Acceptance

Mixed queries return both How-to and Stats sections

Security query does not trigger retrieval/tool calls

7) Pack template generator
7.1 Script

File: scripts/new_pack.py

 CLI:

python scripts/new_pack.py --pack_id mypack --display_name "My Pack"

 Generates:

packs/mypack/pack.py

packs/mypack/tools.py

data/demo/mypack/howto/README.md

 Updates README with pack install steps

Acceptance

Generated pack imports and appears in /packs after registration

8) Tests (pytest)

Create folder tests/

8.1 Unit tests

 test_policy.py:

glob matches

deny patterns

 test_redaction.py

 test_doc_index.py:

ingestion

retrieval filters by org/pack

 test_tools.py:

schema validation

connector execution

8.2 API smoke tests

 test_api.py using httpx test client:

/health

/packs

/chat how-to

/chat stats

/chat deny patterns

Acceptance

pytest -q passes

9) Eval harness (golden tests)

Create folder eval/

9.1 Golden data files

 eval/howto_golden.json

 eval/stats_golden.json

 eval/security_golden.json

9.2 Runner

File: eval/run.py

 Loads golden tests

 Calls local orchestrator directly (no HTTP)

 Validates:

how-to includes citations containing expected doc filename/keyword

stats includes expected tool action

security includes allowed packs/tools OR denial warning

Acceptance

python -m eval.run returns exit code 0

10) Docs & README finalization
10.1 README improvements

 Explain:

how to add docs

how to add tools

how to add packs

how to switch retrieval backends / embeddings

how to run evals/tests

10.2 Security posture docs

 Add a section: “Baseline security (what it does / doesn’t do)”

 Note that real deployments should add stronger auth, secrets handling, etc.

Acceptance

Fresh user can run in <5 minutes and get working responses

11) Optional (nice-to-have but not required for M1)

 Add /admin/reindex endpoint (trigger ingestion)

 Add caching for retrieval and tool calls (Redis)

 Add rate limiting middleware (simple)

 Add PgVectorDocIndex backend (real pgvector)

Execution Order (Codex should follow)

Sections 0–3 (schemas, policy, audit)

Section 4 (chunking + ingestion + retrieval)

Section 5 (tools + connectors + arg parsing)

Section 6 (orchestrator behavior)

Sections 8–9 (tests + eval)

Section 7 + 10 (pack template + docs)

Final Definition of Done

docker compose up --build works

/chat supports how-to + stats + security with citations/actions/warnings

RBAC is enforced

deny patterns block unsafe requests

audit events are emitted and retrievable (in-memory)

pytest passes

python -m eval.run passes

pack generator works