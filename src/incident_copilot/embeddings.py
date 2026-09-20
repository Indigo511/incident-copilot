from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol, Sequence


class EmbeddingProvider(Protocol):
    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


_TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_.:/-]*")
_NORMALIZE = {
    "release": "deployment",
    "released": "deployment",
    "deploy": "deployment",
    "errors": "failure",
    "failed": "failure",
    "failing": "failure",
    "failures": "failure",
    "spike": "increase",
    "spiked": "increase",
    "increased": "increase",
    "asset-card": "asset_card",
    "asset-cards": "asset_card",
    "unlocks": "unlock",
    "users": "user",
}


def tokenize(text: str) -> list[str]:
    return [_NORMALIZE.get(token, token) for token in _TOKEN_PATTERN.findall(text.lower())]


class HashingEmbeddingProvider:
    """Dependency-free learning baseline, not a replacement for a trained embedding model.

    Tokens are feature-hashed into a normalized vector. This keeps tests and the demo
    offline and deterministic while preserving the same interface used by the real model.
    """

    def __init__(self, dimensions: int = 384) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self.dimensions = dimensions

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = tokenize(text)
        features = tokens + [f"{left}::{right}" for left, right in zip(tokens, tokens[1:])]
        for feature in features:
            digest = hashlib.sha256(feature.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector


class SentenceTransformerEmbeddingProvider:
    """Real local semantic embeddings; install the project's `semantic` extra."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError(
                "Install semantic dependencies with: pip install -e '.[semantic]'"
            ) from error
        self._model = SentenceTransformer(model_name)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = self._model.encode(list(texts), normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("vectors must have equal dimensions")
    return sum(a * b for a, b in zip(left, right))
