import os
import math
import hashlib
import httpx
from typing import Sequence

import re

class EmbeddingGenerator:
    DIMENSIONS = 1536

    @classmethod
    def _deterministic_mock_vector(cls, text: str) -> list[float]:
        """
        Generates a normalized 1536-dimension deterministic float vector based on text tokens
        using feature hashing (hashing trick). This ensures that offline / mock environments
        retain semantic keyword similarity and cluster matching documents with queries.
        """
        vector = [0.0] * cls.DIMENSIONS
        words = re.findall(r"\w+", text.lower())
        if not words:
            words = ["empty"]

        stopwords = {"the", "is", "at", "which", "on", "a", "an", "and", "or", "to", "in", "for", "with", "what", "we", "our", "you", "your"}

        for w in words:
            weight = 0.3 if w in stopwords else 1.5
            for seed in [1337, 7331, 9999]:
                h = int(hashlib.md5(f"{w}_{seed}".encode("utf-8")).hexdigest(), 16)
                idx = h % cls.DIMENSIONS
                sign = 1.0 if ((h >> 16) & 1) == 0 else -1.0
                vector[idx] += sign * weight

        # Also add character 3-grams for subword matching
        for i in range(len(text) - 2):
            trigram = text[i:i+3].lower()
            h = int(hashlib.md5(trigram.encode("utf-8")).hexdigest(), 16)
            idx = h % cls.DIMENSIONS
            sign = 1.0 if ((h >> 16) & 1) == 0 else -1.0
            vector[idx] += sign * 0.2

        # Normalize vector to unit length (L2 norm)
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [x / norm for x in vector]
        return vector

    @classmethod
    async def get_embedding(cls, text: str) -> list[float]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return cls._deterministic_mock_vector(text)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"input": text, "model": "text-embedding-3-small"}
                )
                if res.status_code == 200:
                    data = res.json()
                    return data["data"][0]["embedding"]
        except Exception:
            pass

        return cls._deterministic_mock_vector(text)

    @classmethod
    async def get_embeddings_batch(cls, texts: Sequence[str]) -> list[list[float]]:
        results = []
        for t in texts:
            emb = await cls.get_embedding(t)
            results.append(emb)
        return results

    @classmethod
    def cosine_similarity(cls, v1: list[float], v2: list[float]) -> float:
        """
        Calculates cosine similarity between two unit vectors: dot product.
        """
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        return sum(a * b for a, b in zip(v1, v2))
