from fastapi import APIRouter, HTTPException
from app.db.connection import database_connection
from app.db.documents import find_document_by_thread_id
from app.schemas.conflict_resolution import ConflictResolutionRequest
from app.services.workflow_queue import enqueue_workflow

router = APIRouter(prefix="/conflicts", tags=["conflicts"])


@router.get("")
async def list_conflicts(status: str | None = None):
    query = """SELECT id, thread_id, field_name, status, description,
        resolution, conflicting_sources, created_at, updated_at
        FROM conflicts"""
    params: tuple = ()
    if status:
        query += " WHERE status = %s"
        params = (status,)
    query += " ORDER BY created_at DESC"
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return [{"id": str(r[0]), "thread_id": r[1], "field_name": r[2],
                     "status": r[3], "description": r[4], "resolution": r[5],
                     "conflicting_sources": r[6], "created_at": r[7], "updated_at": r[8]}
                    for r in cursor.fetchall()]


@router.post("/resolve")
async def resolve_conflicts(request: ConflictResolutionRequest):
    document = find_document_by_thread_id(request.thread_id)
    if not document:
        raise HTTPException(
            status_code=404, detail="Workflow document not found.")
    if document["status"] != "waiting_for_conflict":
        raise HTTPException(
            status_code=409,
            detail=(
                "Document is not waiting for conflict resolution. "
                f"Current status: {document['status']}"
            ),
        )

    try:
        enqueue_workflow(
            request.thread_id,
            str(document["document_id"]),
            request.decision.model_dump(mode="json"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"thread_id": request.thread_id, "status": "queued"}
