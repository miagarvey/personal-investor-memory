from dataclasses import dataclass


@dataclass
class ChunkConfig:
    """Configuration for text chunking."""
    chunk_size: int = 512  # tokens
    chunk_overlap: int = 50  # tokens
    min_chunk_size: int = 100  # tokens


class TextChunker:
    """
    Splits text into overlapping chunks for embedding.

    Preserves context by maintaining overlap between chunks.
    """

    def __init__(self, config: ChunkConfig | None = None):
        self.config = config or ChunkConfig()

    def chunk_text(self, text: str) -> list[str]:
        """
        Split text into chunks.

        TODO: Implement proper tokenization-aware chunking.
        Current implementation uses simple character-based splitting.
        """
        # Rough approximation: 1 token ≈ 4 characters
        char_size = self.config.chunk_size * 4
        char_overlap = self.config.chunk_overlap * 4
        min_char_size = self.config.min_chunk_size * 4

        if len(text) <= char_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + char_size

            # Try to break at sentence or paragraph boundary
            if end < len(text):
                # Look for paragraph break
                para_break = text.rfind("\n\n", start, end)
                if para_break > start + min_char_size:
                    end = para_break
                else:
                    # Look for sentence break
                    for sep in [". ", "! ", "? ", "\n"]:
                        sent_break = text.rfind(sep, start, end)
                        if sent_break > start + min_char_size:
                            end = sent_break + len(sep)
                            break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - char_overlap

        return chunks
