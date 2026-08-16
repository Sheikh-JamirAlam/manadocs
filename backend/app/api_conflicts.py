from fastapi import APIRouter, HTTPException
from langgraph.types import Command
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.graph.workflow import build_extraction_graph, get_database_url
from app.schemas.conflict_resolution import ConflictResolutionRequest

router = APIRouter(prefix="/conflicts", tags=["conflicts"])


@router.post("/resolve")
async def resolve_conflicts(request: ConflictResolutionRequest):
    # Conflict resolution
    async with AsyncPostgresSaver.from_conn_string(get_database_url()) as checkpointer:
        graph = build_extraction_graph(checkpointer)
        try:
            result = await graph.ainvoke(
                Command(resume=request.decision.model_dump(mode="json")),
                config={"configurable": {"thread_id": request.thread_id}},
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"thread_id": request.thread_id, "state": result}
