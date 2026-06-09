"""Embedding input and provider helpers for topic grouping candidates."""

import hashlib
import math
from typing import Protocol, Sequence

import requests

from app.utils.article_classification import normalize_classification_text


DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_HASH_DIMENSIONS = 64


class EmbeddingProvider(Protocol):
    model: str

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one embedding vector for each input text."""


def build_embedding_input(
    *,
    title: str | None,
    summary: str | None,
    source: str | None,
    source_category: str | None,
    rule_category: str | None,
) -> str:
    fields = (
        ("title", title),
        ("summary", summary),
        ("source", source),
        ("source_category", source_category),
        ("rule_category", rule_category),
    )
    return "\n".join(
        f"{name}: {normalize_classification_text(value)}"
        for name, value in fields
        if normalize_classification_text(value)
    )


def estimate_tokens(texts: Sequence[str]) -> int:
    return sum(max(1, math.ceil(len(text) / 4)) for text in texts)


class DeterministicHashEmbeddingProvider:
    """Dependency-free local embeddings for repeatable dry-run analysis."""

    model = "deterministic-hash-v1"

    def __init__(self, dimensions: int = DEFAULT_HASH_DIMENSIONS):
        if dimensions <= 0:
            raise ValueError("dimensions must be greater than zero")
        self.dimensions = dimensions

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_text(text) for text in texts]

    def _embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = normalize_classification_text(text).split()

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            return vector
        return [value / magnitude for value in vector]


class OpenAIEmbeddingProvider:
    """Minimal OpenAI embeddings provider used only after explicit CLI opt-in."""

    endpoint = "https://api.openai.com/v1/embeddings"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_EMBEDDING_MODEL,
        timeout_seconds: int = 60,
    ):
        if not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={"model": self.model, "input": list(texts)},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()["data"]
        ordered = sorted(data, key=lambda item: item["index"])
        return [item["embedding"] for item in ordered]
