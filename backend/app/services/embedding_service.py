import os
from typing import Any, Dict, List, Optional

from langchain_google_genai import GoogleGenerativeAIEmbeddings


EMBEDDING_DIMENSIONS = 1536
EMBEDDING_BATCH_SIZE = 32


def generate_embeddings(
    chunks: List[Dict[str, Any]],
    model_name: Optional[str] = None,
    batch_size: Optional[int] = None,
) -> List[Dict[str, Any]]:
    # Generate embeddings in batches.
    if not chunks:
        return []

    if batch_size is None:
        batch_size = int(EMBEDDING_BATCH_SIZE)
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")

    embedding_model = GoogleGenerativeAIEmbeddings(
        model=model_name or "gemini-embedding-001",
        output_dimensionality=EMBEDDING_DIMENSIONS,
    )
    embedded_chunks: List[Dict[str, Any]] = []

    for batch_start in range(0, len(chunks), batch_size):
        batch = chunks[batch_start:batch_start + batch_size]
        batch_texts = [chunk.get("text", "") for chunk in batch]

        for chunk, chunk_text in zip(batch, batch_texts):
            if not chunk_text.strip():
                raise ValueError(
                    f"Chunk {chunk.get('chunk_index')} has no text to embed."
                )

        vectors = embedding_model.embed_documents(batch_texts)
        if len(vectors) != len(batch):
            raise ValueError(
                f"Embedding provider returned {len(vectors)} vectors for "
                f"{len(batch)} chunks in batch starting at index {batch_start}."
            )

        for chunk, vector in zip(batch, vectors):
            if len(vector) != EMBEDDING_DIMENSIONS:
                raise ValueError(
                    f"Embedding for chunk {chunk['chunk_index']} has dimension "
                    f"{len(vector)}; expected {EMBEDDING_DIMENSIONS}."
                )
            embedded_chunks.append({**chunk, "embedding": vector})

    return embedded_chunks
