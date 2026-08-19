import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.db.documents import find_document_by_thread_id
from app.db.workflow_events import get_workflow_events

router = APIRouter(prefix="/workflow", tags=["workflow"])


def _sse(event: dict) -> str:
    return f"id: {event['id']}\nevent: workflow\ndata: {json.dumps(event, default=str)}\n\n"


@router.get("/{thread_id}/events")
async def workflow_events(
    thread_id: str,
    after: int = Query(0, ge=0),
):
    if not find_document_by_thread_id(thread_id):
        raise HTTPException(status_code=404, detail="Workflow document not found.")
    return get_workflow_events(thread_id, after_id=after)


@router.get("/{thread_id}/events/stream")
async def workflow_event_stream(
    request: Request,
    thread_id: str,
    after: int = Query(0, ge=0),
):
    if not find_document_by_thread_id(thread_id):
        raise HTTPException(status_code=404, detail="Workflow document not found.")
    last_event_id = after
    try:
        header_id = request.headers.get("last-event-id")
        if header_id:
            last_event_id = max(last_event_id, int(header_id))
    except ValueError:
        pass

    async def events() -> AsyncIterator[str]:
        nonlocal last_event_id
        while not await request.is_disconnected():
            batch = get_workflow_events(thread_id, after_id=last_event_id)
            if batch:
                for event in batch:
                    last_event_id = event["id"]
                    yield _sse(event)
            else:
                yield ": keep-alive\n\n"
                await asyncio.sleep(1)

    return StreamingResponse(
        events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
