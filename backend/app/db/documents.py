import hashlib
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg

from app.graph.state import AgentState
from app.db.connection import database_connection
from app.db.workflow_events import record_workflow_event


SUPPORTED_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".txt"}


def get_file_hash(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def register_document(state: AgentState) -> Dict[str, Any]:
    document_path = state.get("document_path")
    if not document_path:
        return {"error": "No document path was provided."}

    file_path = Path(document_path).expanduser().resolve()
    if not file_path.is_file():
        return {"error": f"File not found at specified path: {file_path}"}

    if file_path.suffix.lower() not in SUPPORTED_DOCUMENT_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))
        file_extension = file_path.suffix or "<none>"
        return {
            "error": (
                f"Unsupported document type '{file_extension}'. "
                f"Supported types: {supported}."
            )
        }

    # File hashing to detect duplicates and ensure idempotency
    file_hash = get_file_hash(file_path)
    file_size_bytes = file_path.stat().st_size

    try:
        with database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, status, thread_id, retry_count FROM documents WHERE file_hash = %s",
                    (file_hash,),
                )
                existing_document = cursor.fetchone()

                if existing_document:
                    existing_id, existing_status, existing_thread_id, retry_count = existing_document
                    existing_thread_id = existing_thread_id or assign_thread_id(
                        str(existing_id)
                    )
                    return {
                        "document_id": str(existing_id),
                        "thread_id": existing_thread_id,
                        "registration_status": "duplicate",
                        "existing_status": existing_status,
                        "retry_count": retry_count or 0,
                        "file_hash": file_hash,
                        "error": None,
                    }

                try:
                    thread_id = str(uuid.uuid4())
                    cursor.execute(
                        """
                        INSERT INTO documents (filename, filepath, file_hash, file_size_bytes, thread_id, status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id, thread_id
                        """,
                        (
                            file_path.name,
                            str(file_path),
                            file_hash,
                            file_size_bytes,
                            thread_id,
                            "pending",
                        ),
                    )
                    inserted_id, inserted_thread_id = cursor.fetchone()
                except psycopg.errors.UniqueViolation:
                    connection.rollback()
                    cursor.execute(
                        "SELECT id, status, thread_id, retry_count FROM documents WHERE file_hash = %s",
                        (file_hash,),
                    )
                    existing_document = cursor.fetchone()
                    if not existing_document:
                        raise
                    existing_id, existing_status, existing_thread_id, retry_count = existing_document
                    existing_thread_id = existing_thread_id or assign_thread_id(
                        str(existing_id)
                    )
                    return {
                        "document_id": str(existing_id),
                        "thread_id": existing_thread_id,
                        "registration_status": "duplicate",
                        "existing_status": existing_status,
                        "retry_count": retry_count or 0,
                        "file_hash": file_hash,
                        "error": None,
                    }

                return {
                    "document_id": str(inserted_id),
                    "thread_id": str(inserted_thread_id),
                    "registration_status": "registered",
                    "file_hash": file_hash,
                    "file_size_bytes": file_size_bytes,
                    "error": None,
                }
    except Exception as exc:
        return {"error": f"Document registration failed: {exc}"}


def assign_thread_id(document_id: str, thread_id: Optional[str] = None) -> str:
    assigned_thread_id = thread_id or str(uuid.uuid4())
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE documents
                SET thread_id = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING thread_id
                """,
                (assigned_thread_id, document_id),
            )
            row = cursor.fetchone()
        connection.commit()
    if not row:
        raise ValueError(f"Document {document_id} was not found.")
    return str(row[0])


def update_document_status(
    document_id: str,
    status: str,
    error_message: Optional[str] = None,
) -> None:
    thread_id = None
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE documents
                SET status = %s, error_message = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (status, error_message, document_id),
            )
            cursor.execute("SELECT thread_id FROM documents WHERE id = %s", (document_id,))
            row = cursor.fetchone()
            thread_id = row[0] if row else None
        connection.commit()
    if thread_id:
        event_type = (
            "waiting_for_user"
            if status in {"waiting_for_conflict", "waiting_for_rule"}
            else "status_changed"
        )
        record_workflow_event(
            document_id, str(thread_id), event_type,
            message=f"Document status changed to {status}.",
            details={"status": status, "error_message": error_message},
        )


def update_current_node(document_id: str, current_node: Optional[str]) -> None:
    thread_id = None
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE documents
                SET current_node = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (current_node, document_id),
            )
            cursor.execute("SELECT thread_id FROM documents WHERE id = %s", (document_id,))
            row = cursor.fetchone()
            thread_id = row[0] if row else None
        connection.commit()
    if thread_id and current_node:
        record_workflow_event(
            document_id, str(thread_id), "started", node_name=current_node,
            message=f"Started {current_node}.",
        )


def save_document_error(document_id: str, error_message: str) -> None:
    update_document_status(document_id, "failed", error_message)


def increment_retry_count(document_id: str) -> int:
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE documents
                SET retry_count = retry_count + 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING retry_count
                """,
                (document_id,),
            )
            row = cursor.fetchone()
        connection.commit()
    if not row:
        raise ValueError(f"Document {document_id} was not found.")
    return row[0]


def find_incomplete_documents() -> List[Dict[str, Any]]:
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, filepath, thread_id, status, current_node, error_message, retry_count
                FROM documents
                WHERE status IN ('pending', 'processing',
                                 'waiting_for_conflict', 'waiting_for_rule',
                                 'failed')
                ORDER BY created_at
                """
            )
            rows = cursor.fetchall()
    return [
        {
            "document_id": str(row[0]),
            "document_path": row[1],
            "thread_id": str(row[2]) if row[2] else None,
            "status": row[3],
            "current_node": row[4],
            "error_message": row[5],
            "retry_count": row[6],
        }
        for row in rows
    ]


def find_document_by_thread_id(thread_id: str) -> Optional[Dict[str, Any]]:
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, filepath, thread_id, status, current_node,
                       error_message, retry_count
                FROM documents
                WHERE thread_id = %s
                """,
                (thread_id,),
            )
            row = cursor.fetchone()
    if not row:
        return None
    return {
        "document_id": str(row[0]),
        "document_path": row[1],
        "thread_id": str(row[2]) if row[2] else None,
        "status": row[3],
        "current_node": row[4],
        "error_message": row[5],
        "retry_count": row[6],
    }
