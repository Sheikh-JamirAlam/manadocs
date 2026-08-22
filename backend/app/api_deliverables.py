from fastapi import APIRouter, HTTPException

from app.db.deliverables import get_all_deliverables, find_by_related_document_ids
from app.services.markdown_deliverable import get_output_path

router = APIRouter(prefix="/deliverables", tags=["deliverables"])


@router.get("")
async def list_deliverables():
    return get_all_deliverables()


@router.get("/master")
async def get_master_deliverable():
    output_path = get_output_path()
    if not output_path.is_file():
        raise HTTPException(
            status_code=404, detail="Master deliverable not found.")
    return {
        "title": "Master Deliverable",
        "content": output_path.read_text(encoding="utf-8"),
        "filename": output_path.name,
        "updated_at": output_path.stat().st_mtime,
    }


@router.get("/{deliverable_id}")
async def get_deliverable(deliverable_id: str):
    for deliverable in get_all_deliverables():
        if deliverable["id"] == deliverable_id:
            return deliverable
    raise HTTPException(status_code=404, detail="Deliverable not found.")


@router.get("/by-document/{document_id}")
async def get_document_deliverable(document_id: str):
    deliverable = find_by_related_document_ids([document_id])
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found.")
    return deliverable
