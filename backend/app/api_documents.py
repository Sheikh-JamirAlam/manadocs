from pathlib import Path
import os
import shutil
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.db.connection import database_connection
from app.db.documents import find_related_documents, register_document
from app.db.facts import get_one_fact
from app.db.conflicts import get_pending_conflicts
from app.db.rules import get_pending_rule_violations
from app.db.deliverables import find_by_related_document_ids
from app.db.chunks import get_document_chunks

router = APIRouter(prefix="/documents", tags=["documents"])


def document(row: tuple) -> dict:
    return {
        "id": str(row[0]), "filename": row[1], "filepath": row[2],
        "file_size_bytes": row[3], "document_type": row[4],
        "vendor_name": row[5], "status": row[6], "error_message": row[7],
        "thread_id": row[8], "current_node": row[9], "retry_count": row[10],
        "created_at": row[11], "updated_at": row[12],
    }


@router.get("")
async def list_documents():
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, filename, filepath, file_size_bytes, document_type, vendor_name, status, error_message, thread_id, current_node, retry_count, created_at, updated_at
                FROM documents
                ORDER BY created_at DESC""")
            return [document(row) for row in cursor.fetchall()]


@router.get("/summary")
async def document_summary():
    """Return dashboard aggregates used by the document library."""
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*) AS document_count,
                    COUNT(*) FILTER (WHERE status NOT IN ('completed', 'failed')) AS in_pipeline,
                    COUNT(*) FILTER (
                        WHERE status = 'completed'
                        AND updated_at >= date_trunc('month', CURRENT_TIMESTAMP)
                    ) AS processed_this_month,
                    COUNT(DISTINCT thread_id) FILTER (WHERE thread_id IS NOT NULL) AS transaction_count
                FROM documents
            """)
            totals = cursor.fetchone()
            cursor.execute("""
                SELECT COUNT(*) FROM conflicts WHERE status = 'pending'
            """)
            pending_conflicts = cursor.fetchone()[0]
            cursor.execute("""
                SELECT COUNT(*) FROM rule_violations WHERE status = 'pending'
            """)
            pending_findings = cursor.fetchone()[0]
            cursor.execute("""
                SELECT thread_id, COUNT(*) AS document_count
                FROM documents
                WHERE thread_id IS NOT NULL
                  AND status NOT IN ('completed', 'failed')
                GROUP BY thread_id
                ORDER BY document_count DESC
                LIMIT 1
            """)
            transaction = cursor.fetchone()
            cursor.execute("""
                SELECT d.thread_id, d.filename, e.event_type, e.message, e.created_at
                FROM workflow_events e
                JOIN documents d ON d.id = e.document_id
                ORDER BY e.created_at DESC
                LIMIT 1
            """)
            activity = cursor.fetchone()

    return {
        "document_count": totals[0],
        "in_pipeline": totals[1],
        "processed_this_month": totals[2],
        "transaction_count": totals[3],
        "needs_attention": pending_conflicts + pending_findings,
        "pending_conflicts": pending_conflicts,
        "pending_findings": pending_findings,
        "active_transaction": {
            "thread_id": transaction[0],
            "document_count": transaction[1],
        } if transaction else None,
        "latest_activity": {
            "thread_id": activity[0],
            "filename": activity[1],
            "event_type": activity[2],
            "message": activity[3],
            "created_at": activity[4],
        } if activity else None,
    }


@router.post("/upload", status_code=202)
async def upload_document(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(
            status_code=400, detail="Supported files: PDF, DOCX, TXT.")
    folder = Path(os.getenv("WATCH_FOLDER", "/data/documents")
                  ).expanduser().resolve()
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / \
        f"{uuid.uuid4().hex}_{Path(file.filename or 'document').name}"
    with target.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    registration = register_document({"document_path": str(target)})
    if registration.get("error"):
        raise HTTPException(status_code=500, detail=registration["error"])
    return {"filename": file.filename, "path": str(target), **registration}


@router.get("/{document_id}")
async def get_document(document_id: str):
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT id, filename, filepath, file_size_bytes,
                document_type, vendor_name, status, error_message, thread_id,
                current_node, retry_count, created_at, updated_at
                FROM documents WHERE id = %s""", (document_id,))
            row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found.")
    result = document(row)
    result["facts"] = get_one_fact(document_id)
    result["conflicts"] = get_pending_conflicts(
        result["thread_id"]) if result["thread_id"] else []
    result["findings"] = get_pending_rule_violations(
        result["thread_id"]) if result["thread_id"] else []
    result["deliverable"] = find_by_related_document_ids([document_id])
    result["content"] = get_document_chunks(document_id)
    result["related_documents"] = find_related_documents(
        result["thread_id"], document_id)
    return result


@router.get("/{document_id}/facts")
async def get_document_facts(document_id: str):
    facts = get_one_fact(document_id)
    if not facts:
        raise HTTPException(status_code=404, detail="Facts not found.")
    return facts
