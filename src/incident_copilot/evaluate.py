from __future__ import annotations

import json

from incident_copilot.cli import build_copilot, project_root


def evaluate_recall_at_k(k: int = 5) -> tuple[int, int]:
    root = project_root()
    cases = json.loads((root / "evaluation" / "questions.json").read_text(encoding="utf-8"))
    retriever = build_copilot().retriever
    hits = 0

    for case in cases:
        results = retriever.search(case["question"], limit=k)
        found = any(
            result.chunk.document_id == case["expected_document"]
            and result.chunk.section == case["expected_section"]
            for result in results
        )
        hits += int(found)
        print(f"{'PASS' if found else 'FAIL'} | {case['question']}")

    return hits, len(cases)


def main() -> None:
    hits, total = evaluate_recall_at_k()
    print(f"Recall@5: {hits}/{total} = {hits / total:.1%}")


if __name__ == "__main__":
    main()
