from __future__ import annotations

import asyncio
import logging
from typing import Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command

from app.db.documents import update_document_status
from app.graph.workflow import build_extraction_graph, get_database_url
from app.db.workflow_events import record_workflow_event

logger = logging.getLogger(__name__)

_queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
_worker_task: asyncio.Task[None] | None = None


async def _resume_workflow(thread_id: str, decision: dict[str, Any]) -> None:
    async with AsyncPostgresSaver.from_conn_string(get_database_url()) as checkpointer:
        graph = build_extraction_graph(checkpointer)
        await graph.ainvoke(
            Command(resume=decision),
            config={"configurable": {"thread_id": thread_id}},
        )


async def _worker() -> None:
    while True:
        thread_id, decision = await _queue.get()
        try:
            await _resume_workflow(thread_id, decision)
        except Exception:
            logger.exception("Queued workflow failed for thread %s", thread_id)
            # The graph normally persists failure state; this event still gives
            # connected clients an immediate diagnostic signal.
        finally:
            _queue.task_done()


def start_worker() -> None:
    global _worker_task
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(_worker(), name="workflow-queue-worker")


async def stop_worker() -> None:
    global _worker_task
    if _worker_task is not None:
        _worker_task.cancel()
        await asyncio.gather(_worker_task, return_exceptions=True)
        _worker_task = None


def enqueue_workflow(thread_id: str, document_id: str, decision: dict[str, Any]) -> None:
    update_document_status(document_id, "processing")
    record_workflow_event(
        document_id, thread_id, "queued", node_name=None,
        message="Workflow resolution queued.", details={"decision": decision},
    )
    _queue.put_nowait((thread_id, decision))
