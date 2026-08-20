from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db.rules import delete_rule, insert_rules, get_active_rules, get_pending_rule_violations, get_rule_violations
from app.db.documents import find_document_by_thread_id
from app.services.workflow_queue import enqueue_workflow

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("")
async def list_rules():
    return get_active_rules()


@router.get("/findings")
async def list_rule_findings(thread_id: str | None = None):
    return get_rule_violations(thread_id)


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


@router.delete("/{rule_id}", status_code=204)
async def remove_rule(rule_id: str):
    if not delete_rule(rule_id):
        raise HTTPException(status_code=404, detail="Rule not found.")


@router.post("/resolve")
async def resolve_rule_violation(request: RuleViolationResolutionRequest):
    document = find_document_by_thread_id(request.thread_id)
    if not document:
        raise HTTPException(
            status_code=404, detail="Workflow document not found.")
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
