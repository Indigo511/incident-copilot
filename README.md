# AI Incident Investigation Copilot

A production-style learning project that investigates incidents in a fictional fleet-card platform. It combines historical RAG with read-only live diagnostic tools and returns an evidence-backed hypothesis rather than presenting correlation as fact.

## End-to-end flow

```text
Engineer question
  -> chunked runbooks and incidents
  -> embedding + hybrid retrieval + section reranking
  -> read-only deployment, version-comparison, and log tools
  -> grounded report generator
  -> cited hypothesis, missing evidence, and safe next steps
```

The default mode is dependency-free and deterministic so the complete pipeline works without credentials. Replaceable adapters support:

- `all-MiniLM-L6-v2` for real semantic embeddings;
- OpenAI for grounded report generation;
- FastAPI for an HTTP interface.

The local hashing embedder is an educational fallback, not a trained semantic model. The deterministic generator is an auditable fallback, not an LLM.

## Run locally

From the repository root:

```bash
PYTHONPATH=src python3 -m incident_copilot.cli
```

Ask a different question:

```bash
PYTHONPATH=src python3 -m incident_copilot.cli \
  "What evidence connects v2.4 to malformed vehicle identifiers?"
```

The JSON response contains retrieved historical chunks, live evidence, a confidence-labelled hypothesis, citations, missing evidence, and recommended next steps.

## Run with AI models

Install semantic embeddings:

```bash
python3 -m pip install -e '.[semantic]'
incident-copilot --semantic-model
```

Use an LLM after configuring `OPENAI_API_KEY`:

```bash
python3 -m pip install -e '.[llm]'
incident-copilot --semantic-model --llm
```

Both generators are subject to output-shape and citation-membership validation.
This does not verify that each cited source actually supports its associated claim.
The external LLM adapter has a 30-second request timeout and two retries.

## HTTP API

```bash
python3 -m pip install -e '.[api]'
uvicorn incident_copilot.api:app --app-dir src --reload
```

```bash
curl -X POST http://127.0.0.1:8000/v1/investigations \
  -H 'Content-Type: application/json' \
  -d '{"question":"Why are asset-card unlocks failing after the latest release?"}'
```

## Tests and retrieval evaluation

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m incident_copilot.evaluate
```

The evaluation reports Recall@5: whether an expected source section appears in the top five retrieved chunks.
These five questions were used to tune the baseline, so 5/5 is a regression check,
not a held-out benchmark or a production accuracy estimate.

Install `pip install -e '.[test-api]'` to include HTTP integration tests. Without
these optional dependencies the HTTP tests are explicitly skipped. LLM validation
tests use a mocked client; no external inference is performed during the test suite.

## Review improvements and current boundaries

- Removed the hard-coded v2.4 mapper diagnosis. Reports identify a possible release
  regression and explicitly request timing, cohort and trace evidence.
- Missing baselines, invalid rates, fewer than 100 requests per version, ambiguous
  deployments, or logs only from an old version result in abstention. The minimum
  sample count is a demo heuristic, not a statistical significance test.
- Release names are taken from evidence; logs are no longer filtered to one preset error.
- Blank/oversized questions and unsupported services are rejected.
- CLI and API responses explicitly label evidence as synthetic and disclose limitations.
- Cosine similarity now supports unnormalized vectors and rejects nonfinite values.
- Provider vector counts and dimensions are checked before indexing.

This is still a single-service demo: the tool order is fixed, `today` is not parsed,
and the fixture is not refreshed. Healthy-state verification, dynamic tool calling,
service-aware retrieval, persistent indexes, bounded chunking/context budgets and
production authentication remain future work. The default generator is a rule-based
regression detector, not a general question-answering model; use the optional LLM
adapter for free-form synthesis. Never expose the unauthenticated demo API publicly.

## Important design rules

- The backend assigns `system_induced` versus `user_induced`; the LLM does not invent this classification.
- Historical incidents suggest hypotheses. Current logs, metrics, and deployments test them.
- Diagnostic tools are read-only and return redacted or aggregated data.
- A deployment immediately before an error spike is correlation, not final proof.
- Rollback and traffic changes require human approval.
- Generated citations must refer to evidence actually supplied to the model.

## Repository map

```text
knowledge/                 Runbooks and historical incidents
data/                      Synthetic current incident evidence
evaluation/                Retrieval test questions
src/incident_copilot/
  chunking.py              Meaningful Markdown section chunking
  embeddings.py            Local baseline and semantic-model adapter
  retrieval.py             Hybrid retrieval and intent reranking
  live_tools.py            Read-only diagnostic-tool boundary
  generation.py            Deterministic and LLM report generators
  copilot.py               End-to-end orchestration
  api.py                   Optional FastAPI interface
  cli.py                   Runnable command-line demo
tests/                     Unit and end-to-end tests
```

## Next production upgrades

The interfaces are ready for later replacement with PostgreSQL + pgvector, real observability APIs, authentication/RBAC, durable audit history, prompt tracing, rate limiting, and a larger evaluation set. Those are intentionally separate from this runnable learning baseline.
