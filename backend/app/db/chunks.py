import uuid
from typing import Any, Dict, List

from psycopg.types.json import Jsonb

from app.db.connection import database_connection


EMBEDDING_DIMENSIONS = 1536


# Insert embedded chunks into the database
def register_chunks(document_id: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not document_id:
        return {"error": "A document_id is required to register chunks."}
    if not chunks:
        return {"error": "No chunks were provided for registration."}

    try:
        with database_connection() as connection:
            with connection.cursor() as cursor:
                for chunk in chunks:
                    embedding = chunk.get("embedding")
                    if embedding is None:
                        raise ValueError(
                            f"Chunk {chunk.get('chunk_index')} has no embedding."
                        )
                    if len(embedding) != EMBEDDING_DIMENSIONS:
                        raise ValueError(
                            f"Chunk {chunk['chunk_index']} has embedding dimension "
                            f"{len(embedding)}; expected {EMBEDDING_DIMENSIONS}."
                        )

                    cursor.execute(
                        """
                        INSERT INTO document_chunks (id, document_id, chunk_index, content, embedding, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (document_id, chunk_index)
                        DO UPDATE SET
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata
                        """,
                        (
                            str(uuid.uuid4()),
                            document_id,
                            chunk["chunk_index"],
                            chunk["text"],
                            embedding,
                            Jsonb(
                                {
                                    "page_number": chunk.get("page_start"),
                                    "page_start": chunk.get("page_start"),
                                    "page_end": chunk.get("page_end"),
                                }
                            ),
                        ),
                    )

        return {
            "document_id": document_id,
            "chunks_registered": len(chunks),
            "error": None,
        }
    except Exception as exc:
        return {"error": f"Chunk registration failed: {exc}"}


def get_document_chunks(document_id: str) -> List[Dict[str, Any]]:
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT chunk_index, content, metadata
                   FROM document_chunks
                   WHERE document_id = %s
                   ORDER BY chunk_index""",
                (document_id,),
            )
            rows = cursor.fetchall()
    return [
        {"chunk_index": row[0], "content": row[1], "metadata": row[2] or {}}
        for row in rows
    ]
