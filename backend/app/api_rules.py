from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db.rules import insert_rules
from app.db.documents import find_document_by_thread_id
from app.services.workflow_queue import enqueue_workflow

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
    document = find_document_by_thread_id(request.thread_id)
    if not document:
        raise HTTPException(status_code=404, detail="Workflow document not found.")
    if document["status"] != "waiting_for_rule":
        raise HTTPException(
            status_code=409,
            detail=(
                "Document is not waiting for rule verification. "
                f"Current status: {document['status']}"
            ),
        )

    enqueue_workflow(
        request.thread_id,
        str(document["document_id"]),
        request.decision.model_dump(),
    )
    return {"thread_id": request.thread_id, "status": "queued"}
