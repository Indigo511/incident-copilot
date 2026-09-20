# AI Incident Investigation Copilot

An industry-style learning project for investigating production incidents in a fictional fleet-card platform.

## What exists now

The first modules model two production principles:

- **Error classification belongs in deterministic backend code, not in the LLM.**
- **Knowledge is split by meaningful section before it is embedded.**

They compare error rates between deployment versions and turn runbooks/historical incidents into independently understandable chunks that an AI layer can later retrieve.

Run it:

```bash
python3 -m incident_copilot.main
```

Run tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Inspect the current semantic chunks:

```bash
PYTHONPATH=src python3 -m incident_copilot.inspect_chunks
```

## Planned architecture

1. Backend emits safe, structured unlock-request logs and deterministic error categories.
2. Incident knowledge (runbooks and historical incidents) is chunked, embedded and indexed in PostgreSQL + pgvector.
3. RAG retrieves relevant historical evidence.
4. Read-only tools fetch current logs, metrics and deployments.
5. An LLM synthesizes cited hypotheses; humans approve all remediation.
6. Evaluation measures retrieval quality, faithfulness, latency and cost.

## Core rule

An LLM can interpret evidence, but it must not invent a system-versus-user failure classification. The application assigns that category from known backend error codes.
