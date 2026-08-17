from fastapi import APIRouter
from pydantic import BaseModel, Field

from langgraph.types import Command
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.db.rules import insert_rules
from app.graph.workflow import build_extraction_graph, get_database_url

router = APIRouter(prefix="/rules", tags=["rules"])


class RuleCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)


class RulesCreateRequest(BaseModel):
    rules: list[RuleCreateRequest] = Field(min_length=1)


class RuleViolationDecision(BaseModel):
    rule_violation_id: str = Field(min_length=1)
    decision: str = Field(pattern="^(accept|reject)$")


class RuleViolationResolutionRequest(BaseModel):
    thread_id: str = Field(min_length=1)
    decision: RuleViolationDecision


@router.post("", status_code=201)
async def create_rules(request: RulesCreateRequest):
    return insert_rules([rule.model_dump() for rule in request.rules])


@router.post("/resolve")
async def resolve_rule_violation(request: RuleViolationResolutionRequest):
    async with AsyncPostgresSaver.from_conn_string(get_database_url()) as checkpointer:
        graph = build_extraction_graph(checkpointer)
        result = await graph.ainvoke(
            Command(resume=request.decision.model_dump()),
            config={"configurable": {"thread_id": request.thread_id}},
        )
    return {"thread_id": request.thread_id, "state": result}
