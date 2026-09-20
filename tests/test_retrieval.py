from pathlib import Path
import unittest

from incident_copilot.chunking import chunk_directory
from incident_copilot.embeddings import HashingEmbeddingProvider
from incident_copilot.retrieval import InMemoryHybridRetriever


class TestRetrieval(unittest.TestCase):
    def test_root_cause_is_retrieved_for_release_failure_question(self) -> None:
        chunks = chunk_directory(Path("knowledge"))
        retriever = InMemoryHybridRetriever(chunks, HashingEmbeddingProvider())
        results = retriever.search(
            "Why are asset-card unlocks failing after the latest release?", limit=5
        )
        sections = {(result.chunk.document_id, result.chunk.section) for result in results}
        self.assertIn(("INC-104-card-unlock-v2-4", "Root cause"), sections)


if __name__ == "__main__":
    unittest.main()
