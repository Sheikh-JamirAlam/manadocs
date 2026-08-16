from typing import Any, Dict, List, Mapping
from psycopg.types.json import Jsonb
from app.db.connection import database_connection


# Insert conflicts into the database
def insert_conflicts(
    thread_id: str,
    conflicts: List[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    if not thread_id:
        raise ValueError("A thread_id is required to insert conflicts.")

    inserted: List[Dict[str, Any]] = []
    with database_connection() as connection:
        with connection.cursor() as cursor:
            for conflict in conflicts:
                field_name = conflict.get("field_name")
                sources = conflict.get("conflicting_sources", [])
                if not field_name or not sources:
                    continue

                cursor.execute(
                    """
                    SELECT active_value, active_source_doc_id
                    FROM conflicts
                    WHERE thread_id = %s AND field_name = %s
                      AND status = 'resolved'
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (thread_id, field_name),
                )
                baseline = cursor.fetchone()
                active_value = baseline[0] if baseline else None
                active_source_doc_id = baseline[1] if baseline else None

                cursor.execute(
                    """
                    INSERT INTO conflicts (thread_id, field_name, status, description, active_value, active_source_doc_id, conflicting_sources)
                    VALUES (%s, %s, 'pending', %s, %s, %s, %s)
                    RETURNING id, field_name, status, active_value, active_source_doc_id, conflicting_sources
                    """,
                    (
                        thread_id,
                        field_name,
                        conflict.get("description"),
                        Jsonb(active_value) if active_value is not None else None,
                        active_source_doc_id,
                        Jsonb(sources),
                    ),
                )
                row = cursor.fetchone()
                inserted.append({
                    "id": str(row[0]),
                    "field_name": row[1],
                    "status": row[2],
                    "active_value": row[3],
                    "active_source_doc_id": (
                        str(row[4]) if row[4] is not None else None
                    ),
                    "conflicting_sources": row[5],
                })
        connection.commit()
    return inserted


# Update/Resolve a conflict
def resolve_conflict(
    thread_id: str,
    conflict_id: str,
    selected_document_id: str,
) -> Dict[str, Any]:
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT conflicting_sources FROM conflicts
                WHERE id = %s AND thread_id = %s AND status = 'pending'
                FOR UPDATE
                """,
                (conflict_id, thread_id),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(
                    "Pending conflict was not found for this thread.")
            selected_source = next(
                (source for source in (row[0] or [])
                 if str(source.get("document_id")) == selected_document_id),
                None,
            )
            if selected_source is None:
                raise ValueError("Selected document is not a conflict source.")
            cursor.execute(
                """
                UPDATE conflicts
                SET active_value = %s, active_source_doc_id = %s, selected_doc_id = %s, resolution = 'selected_document', status = 'resolved', updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND thread_id = %s
                RETURNING id, field_name, status, description, active_value, active_source_doc_id, selected_doc_id, resolution, conflicting_sources
                """,
                (Jsonb(selected_source.get("value")), selected_document_id,
                 selected_document_id, conflict_id, thread_id),
            )
            resolved = cursor.fetchone()
        connection.commit()
    return {
        "id": str(resolved[0]), "field_name": resolved[1],
        "status": resolved[2], "description": resolved[3],
        "active_value": resolved[4],
        "active_source_doc_id": str(resolved[5]),
        "selected_doc_id": str(resolved[6]), "resolution": resolved[7],
        "conflicting_sources": resolved[8],
    }


# Load pending conflicts for a paused graph thread
def get_pending_conflicts(thread_id: str) -> List[Dict[str, Any]]:
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, field_name, status, description, active_value, active_source_doc_id, selected_doc_id, resolution, conflicting_sources
                FROM conflicts
                WHERE thread_id = %s AND status = 'pending'
                ORDER BY created_at
                """,
                (thread_id,),
            )
            rows = cursor.fetchall()
    return [
        {
            "id": str(row[0]),
            "field_name": row[1],
            "status": row[2],
            "description": row[3],
            "active_value": row[4],
            "active_source_doc_id": (
                str(row[5]) if row[5] is not None else None
            ),
            "selected_doc_id": str(row[6]) if row[6] is not None else None,
            "resolution": row[7],
            "conflicting_sources": row[8],
        }
        for row in rows
    ]
