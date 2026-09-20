from __future__ import annotations

import argparse
import json
from pathlib import Path

from incident_copilot.copilot import IncidentCopilot
from incident_copilot.embeddings import HashingEmbeddingProvider, SentenceTransformerEmbeddingProvider
from incident_copilot.generation import DeterministicReportGenerator, OpenAIReportGenerator


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_copilot(use_semantic_model: bool = False, use_llm: bool = False) -> IncidentCopilot:
    root = project_root()
    embeddings = (
        SentenceTransformerEmbeddingProvider()
        if use_semantic_model
        else HashingEmbeddingProvider()
    )
    generator = OpenAIReportGenerator() if use_llm else DeterministicReportGenerator()
    return IncidentCopilot(
        root / "knowledge",
        root / "data" / "scenarios",
        embeddings,
        generator,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Investigate a fleet-card production incident")
    parser.add_argument(
        "question",
        nargs="?",
        default="Why are asset-card unlocks failing after the latest release?",
    )
    parser.add_argument("--semantic-model", action="store_true", help="Use all-MiniLM-L6-v2")
    parser.add_argument("--llm", action="store_true", help="Use OpenAI for grounded generation")
    parser.add_argument(
        "--scenario",
        default="deployment_regression",
        help="Synthetic evidence scenario to run",
    )
    args = parser.parse_args()

    investigation = build_copilot(args.semantic_model, args.llm).investigate(
        args.question, scenario=args.scenario
    )
    output = {
        "data_mode": investigation.data_mode,
        "limitations": investigation.limitations,
        "question": investigation.question,
        "retrieved_chunks": [
            {
                "source": result.chunk.chunk_id,
                "section": result.chunk.section,
                "score": round(result.final_score, 4),
            }
            for result in investigation.retrieved
        ],
        "live_evidence": [
            {"source": item.evidence_id, "tool": item.tool, "summary": item.summary}
            for item in investigation.live_evidence
        ],
        "report": investigation.report.to_dict(),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
