from fastapi import APIRouter, HTTPException
from app.db.documents import find_document_by_thread_id
from app.schemas.conflict_resolution import ConflictResolutionRequest
from app.services.workflow_queue import enqueue_workflow

router = APIRouter(prefix="/conflicts", tags=["conflicts"])


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
