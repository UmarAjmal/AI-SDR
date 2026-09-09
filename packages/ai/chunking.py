import re

class ChunkItem:
    def __init__(self, chunk_index: int, content: str, token_count: int, metadata: dict):
        self.chunk_index = chunk_index
        self.content = content
        self.token_count = token_count
        self.metadata = metadata

class SemanticChunker:
    """
    Chunks document text into 500-800 token slices with 100-token overlap,
    preserving structural paragraph boundaries.
    """
    APPROX_WORDS_PER_CHUNK = 400
    APPROX_WORDS_OVERLAP = 60

    @classmethod
    def chunk_text(cls, text: str, source_url: str, title: str | None = None) -> list[ChunkItem]:
        if not text:
            return []

        # Split by paragraphs / headings
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        chunks: list[ChunkItem] = []
        current_words: list[str] = []
        chunk_idx = 0

        for p in paragraphs:
            words = p.split()
            if len(current_words) + len(words) > cls.APPROX_WORDS_PER_CHUNK and current_words:
                chunk_str = " ".join(current_words)
                token_est = int(len(current_words) * 1.3)
                chunks.append(ChunkItem(
                    chunk_index=chunk_idx,
                    content=chunk_str,
                    token_count=token_est,
                    metadata={
                        "source_url": source_url,
                        "title": title or "",
                        "chunk_index": chunk_idx
                    }
                ))
                chunk_idx += 1
                # Retain overlap words
                current_words = current_words[-cls.APPROX_WORDS_OVERLAP:] + words
            else:
                current_words.extend(words)

        # Last remaining chunk
        if current_words:
            chunk_str = " ".join(current_words)
            token_est = int(len(current_words) * 1.3)
            chunks.append(ChunkItem(
                chunk_index=chunk_idx,
                content=chunk_str,
                token_count=token_est,
                metadata={
                    "source_url": source_url,
                    "title": title or "",
                    "chunk_index": chunk_idx
                }
            ))

        return chunks
