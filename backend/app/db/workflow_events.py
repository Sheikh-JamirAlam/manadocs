from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from psycopg.types.json import Jsonb

from app.db.connection import database_connection


def record_workflow_event(
    document_id: str,
    thread_id: str,
    event_type: str,
    *,
    node_name: Optional[str] = None,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> int:
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO workflow_events
                    (document_id, thread_id, node_name, event_type, message, details)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (document_id, thread_id, node_name, event_type, message,
                 Jsonb(details or {})),
            )
            event_id = cursor.fetchone()[0]
        connection.commit()
    return int(event_id)


def get_workflow_events(
    thread_id: str,
    *,
    after_id: int = 0,
    limit: int = 500,
) -> list[Dict[str, Any]]:
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, document_id, thread_id, node_name, event_type,
                       message, details, created_at
                FROM workflow_events
                WHERE thread_id = %s AND id > %s
                ORDER BY id
                LIMIT %s
                """,
                (thread_id, after_id, min(max(limit, 1), 1000)),
            )
            rows = cursor.fetchall()
    return [
        {
            "id": int(row[0]), "document_id": str(row[1]),
            "thread_id": row[2], "node_name": row[3],
            "event_type": row[4], "message": row[5],
            "details": row[6] or {}, "created_at": row[7].isoformat(),
        }
        for row in rows
    ]


def get_all_workflow_events(*, after_id: int = 0, limit: int = 500) -> list[Dict[str, Any]]:
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, document_id, thread_id, node_name, event_type,
                       message, details, created_at
                FROM workflow_events
                WHERE id > %s
                ORDER BY id
                LIMIT %s
                """,
                (after_id, min(max(limit, 1), 1000)),
            )
            rows = cursor.fetchall()
    return [
        {
            "id": int(row[0]), "document_id": str(row[1]),
            "thread_id": row[2], "node_name": row[3],
            "event_type": row[4], "message": row[5],
            "details": row[6] or {}, "created_at": row[7].isoformat(),
        }
        for row in rows
    ]
