import hashlib
from pathlib import Path
from typing import Any, Dict

import psycopg

from app.graph.state import AgentState
from app.db.connection import database_connection


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
                    "SELECT id, status FROM documents WHERE file_hash = %s",
                    (file_hash,),
                )
                existing_document = cursor.fetchone()

                if existing_document:
                    existing_id, existing_status = existing_document
                    return {
                        "document_id": str(existing_id),
                        "registration_status": "duplicate",
                        "existing_status": existing_status,
                        "file_hash": file_hash,
                        "error": None,
                    }

                try:
                    cursor.execute(
                        """
                        INSERT INTO documents (filename, filepath, file_hash, file_size_bytes, status)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            file_path.name,
                            str(file_path),
                            file_hash,
                            file_size_bytes,
                            "pending",
                        ),
                    )
                    inserted_id = cursor.fetchone()[0]
                except psycopg.errors.UniqueViolation:
                    connection.rollback()
                    cursor.execute(
                        "SELECT id, status FROM documents WHERE file_hash = %s",
                        (file_hash,),
                    )
                    existing_document = cursor.fetchone()
                    if not existing_document:
                        raise
                    existing_id, existing_status = existing_document
                    return {
                        "document_id": str(existing_id),
                        "registration_status": "duplicate",
                        "existing_status": existing_status,
                        "file_hash": file_hash,
                        "error": None,
                    }

                return {
                    "document_id": str(inserted_id),
                    "registration_status": "registered",
                    "file_hash": file_hash,
                    "file_size_bytes": file_size_bytes,
                    "error": None,
                }
    except Exception as exc:
        return {"error": f"Document registration failed: {exc}"}
