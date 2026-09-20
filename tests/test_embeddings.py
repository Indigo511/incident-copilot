import unittest

from incident_copilot.embeddings import HashingEmbeddingProvider, cosine_similarity


class TestEmbeddings(unittest.TestCase):
    def test_related_phrases_are_closer_than_unrelated_text(self) -> None:
        provider = HashingEmbeddingProvider()
        query, related, unrelated = provider.embed(
            [
                "unlock failures increased after release",
                "unlock error spike following deployment",
                "monthly billing invoice was generated",
            ]
        )
        self.assertGreater(
            cosine_similarity(query, related), cosine_similarity(query, unrelated)
        )


if __name__ == "__main__":
    unittest.main()
