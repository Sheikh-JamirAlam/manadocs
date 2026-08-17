from typing import Any, Dict, List, Mapping

from psycopg.types.json import Jsonb

from app.db.connection import database_connection


def insert_rules(rules: List[Mapping[str, str]]) -> List[Dict[str, Any]]:
    if not rules:
        raise ValueError("At least one rule is required.")
    inserted = []
    with database_connection() as connection:
        with connection.cursor() as cursor:
            for rule in rules:
                name = (rule.get("name") or "").strip()
                description = (rule.get("description") or "").strip()
                if not name or not description:
                    raise ValueError(
                        "Every rule requires a name and description.")
                cursor.execute(
                    """INSERT INTO rules (name, description)
                       VALUES (%s, %s)
                       RETURNING id, name, description, is_active, created_at, updated_at""",
                    (name, description),
                )
                row = cursor.fetchone()
                inserted.append({"id": str(row[0]), "name": row[1],
                                 "description": row[2], "is_active": row[3],
                                 "created_at": row[4], "updated_at": row[5]})
        connection.commit()
    return inserted


def get_active_rules() -> List[Dict[str, Any]]:
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT id, name, description FROM rules
                              WHERE is_active = TRUE ORDER BY created_at""")
            rows = cursor.fetchall()
    return [{"id": str(row[0]), "name": row[1], "description": row[2]} for row in rows]


def insert_rule_violations(thread_id: str, document_id: str,
                           violations: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    if not thread_id or not document_id:
        raise ValueError("thread_id and document_id are required.")
    inserted = []
    with database_connection() as connection:
        with connection.cursor() as cursor:
            for violation in violations:
                rule_id = violation.get("rule_id")
                if not rule_id:
                    continue
                cursor.execute(
                    """INSERT INTO rule_violations
                       (thread_id, document_id, rule_id, description, citation)
                       VALUES (%s, %s, %s, %s, %s)
                       RETURNING id, thread_id, document_id, rule_id, description, citation, status""",
                    (thread_id, document_id, rule_id, violation.get("description", ""),
                     Jsonb(violation.get("citation", {}))),
                )
                row = cursor.fetchone()
                inserted.append({"id": str(row[0]), "thread_id": row[1],
                                 "document_id": str(row[2]), "rule_id": str(row[3]),
                                 "description": row[4], "citation": row[5], "status": row[6]})
        connection.commit()
    return inserted


def get_pending_rule_violations(thread_id: str) -> List[Dict[str, Any]]:
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id, thread_id, document_id, rule_id, description,
                          citation, status, resolution
                   FROM rule_violations
                   WHERE thread_id = %s AND status = 'pending'
                   ORDER BY created_at""",
                (thread_id,),
            )
            rows = cursor.fetchall()
    return [
        {"id": str(row[0]), "thread_id": row[1], "document_id": str(row[2]),
         "rule_id": str(row[3]), "description": row[4], "citation": row[5],
         "status": row[6], "resolution": row[7]}
        for row in rows
    ]


def resolve_rule_violation(thread_id: str, violation_id: str,
                           decision: str) -> Dict[str, Any]:
    resolution = {"reject": "enforce_rule",
                  "accept": "override_rule"}.get(decision)
    if resolution is None:
        raise ValueError("Decision must be 'accept' or 'reject'.")
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """UPDATE rule_violations
                   SET status = 'resolved', resolution = %s,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = %s AND thread_id = %s AND status = 'pending'
                   RETURNING id, thread_id, document_id, rule_id, description,
                             citation, status, resolution""",
                (resolution, violation_id, thread_id),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(
                    "Pending rule violation was not found for this thread.")
        connection.commit()
    return {"id": str(row[0]), "thread_id": row[1], "document_id": str(row[2]),
            "rule_id": str(row[3]), "description": row[4], "citation": row[5],
            "status": row[6], "resolution": row[7]}
