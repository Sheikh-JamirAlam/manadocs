from typing import Any, Dict, List, Mapping

from psycopg.types.json import Jsonb

from app.db.connection import database_connection


def insert_conflicts(thread_id: str, conflicts: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    if not thread_id:
        raise ValueError("A thread_id is required to insert conflicts.")
    inserted = []
    with database_connection() as connection:
        with connection.cursor() as cursor:
            for conflict in conflicts:
                field_name = conflict.get("field_name")
                sources = conflict.get("conflicting_sources", [])
                if not field_name or not sources:
                    continue
                cursor.execute(
                    """INSERT INTO conflicts
                       (thread_id, field_name, status, description, conflicting_sources)
                       VALUES (%s, %s, 'pending', %s, %s)
                       RETURNING id, thread_id, field_name, status, description,
                                 resolution, conflicting_sources""",
                    (thread_id, field_name, conflict.get(
                        "description"), Jsonb(sources)),
                )
                row = cursor.fetchone()
                inserted.append({"id": str(row[0]), "thread_id": row[1],
                                 "field_name": row[2], "status": row[3],
                                 "description": row[4], "resolution": row[5],
                                 "conflicting_sources": row[6]})
        connection.commit()
    return inserted


def resolve_conflict(thread_id: str, conflict_id: str, decision: str) -> Dict[str, Any]:
    resolution = {"reject": "enforce_conflict",
                  "accept": "override_conflict"}.get(decision)
    if resolution is None:
        raise ValueError("Decision must be 'accept' or 'reject'.")
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """UPDATE conflicts
                   SET status = 'resolved', resolution = %s, updated_at = CURRENT_TIMESTAMP
                   WHERE id = %s AND thread_id = %s AND status = 'pending'
                   RETURNING id, thread_id, field_name, status, description,
                             resolution, conflicting_sources""",
                (resolution, conflict_id, thread_id),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(
                    "Pending conflict was not found for this thread.")
        connection.commit()
    return {"id": str(row[0]), "thread_id": row[1], "field_name": row[2],
            "status": row[3], "description": row[4], "resolution": row[5],
            "conflicting_sources": row[6]}


def get_pending_conflicts(thread_id: str) -> List[Dict[str, Any]]:
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id, thread_id, field_name, status, description,
                          resolution, conflicting_sources
                   FROM conflicts
                   WHERE thread_id = %s AND status = 'pending'
                   ORDER BY created_at""", (thread_id,))
            rows = cursor.fetchall()
    return [{"id": str(row[0]), "thread_id": row[1], "field_name": row[2],
             "status": row[3], "description": row[4], "resolution": row[5],
             "conflicting_sources": row[6]} for row in rows]
