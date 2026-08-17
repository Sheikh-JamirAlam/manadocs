from typing import Any, Dict, Iterable, Optional

from app.db.connection import database_connection


def find_by_related_document_ids(document_ids: Iterable[str]) -> Optional[Dict[str, Any]]:
    ids = [str(document_id) for document_id in document_ids if document_id]
    if not ids:
        return None

    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, title, content, version, index, related_document_ids
                FROM deliverables
                WHERE related_document_ids && %s::uuid[]
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (ids,),
            )
            row = cursor.fetchone()

    if not row:
        return None
    return {
        "id": str(row[0]), "title": row[1], "content": row[2],
        "version": row[3], "index": row[4],
        "related_document_ids": [str(value) for value in (row[5] or [])],
    }


def insert_deliverable(title: str, content: str, related_document_ids: Iterable[str]) -> Dict[str, Any]:
    ids = [str(document_id)
           for document_id in related_document_ids if document_id]
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO deliverables (title, content, index, related_document_ids)
                VALUES (%s, %s, DEFAULT, %s::uuid[])
                RETURNING id, title, content, version, index, related_document_ids
                """,
                (title, content, ids),
            )
            row = cursor.fetchone()
        connection.commit()
    return {
        "id": str(row[0]), "title": row[1], "content": row[2],
        "version": row[3], "index": row[4],
        "related_document_ids": [str(value) for value in (row[5] or [])],
    }


def update_deliverable(deliverable_id: str, title: str, content: str,
                       related_document_ids: Iterable[str]) -> Dict[str, Any]:
    ids = [str(document_id)
           for document_id in related_document_ids if document_id]
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE deliverables
                SET title = %s, content = %s, version = version + 1, related_document_ids = %s::uuid[], updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id, title, content, version, index, related_document_ids
                """,
                (title, content, ids, deliverable_id),
            )
            row = cursor.fetchone()
        connection.commit()
    if not row:
        raise ValueError(f"Deliverable {deliverable_id} was not found.")
    return {
        "id": str(row[0]), "title": row[1], "content": row[2],
        "version": row[3], "index": row[4],
        "related_document_ids": [str(value) for value in (row[5] or [])],
    }
