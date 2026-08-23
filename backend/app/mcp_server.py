from __future__ import annotations

import base64
import binascii
import os
import uuid
from pathlib import Path

from mcp.server import MCPServer as FastMCP

from app.db.conflicts import get_pending_conflicts
from app.db.deliverables import get_all_deliverables
from app.db.documents import find_document_by_thread_id, register_document
from app.db.rules import get_pending_rule_violations, insert_rules
from app.db.workflow_events import get_workflow_events as read_workflow_events
from app.services.workflow_queue import enqueue_workflow

mcp = FastMCP("DocTask")

SUPPORTED_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".txt"}


def _document(thread_id: str) -> dict:
    document = find_document_by_thread_id(thread_id)
    if not document:
        raise ValueError("Workflow document not found.")
    return document


# Submit a PDF, DOCX, or TXT document and start its workflow
@mcp.tool()
def submit_document(filename: str, content_base64: str) -> dict:
    original_name = Path(filename or "document").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in SUPPORTED_DOCUMENT_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))
        raise ValueError(f"Supported document types: {supported}.")
    if not content_base64:
        raise ValueError("content_base64 is required.")

    try:
        content = base64.b64decode(content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("content_base64 must be valid base64.") from exc
    if not content:
        raise ValueError("The submitted document is empty.")

    watch_folder = Path(os.getenv("WATCH_FOLDER", "/data/documents"))
    watch_folder.mkdir(parents=True, exist_ok=True)
    target = watch_folder / f"{uuid.uuid4().hex}_{original_name}"
    target.write_bytes(content)

    registration = register_document({"document_path": str(target)})
    if registration.get("error"):
        try:
            target.unlink()
        except OSError:
            pass
        raise ValueError(registration["error"])

    return {
        "filename": filename,
        "path": str(target),
        **registration,
    }


# Get the current status and active node for a workflow
@mcp.tool()
def get_workflow_status(thread_id: str) -> dict:
    return _document(thread_id)


# Read durable workflow progress events after an event ID
@mcp.tool()
def get_workflow_events(thread_id: str, after_id: int = 0) -> list[dict]:
    _document(thread_id)
    return read_workflow_events(thread_id, after_id=after_id)


# List conflicts awaiting explicit human or machine approval
@mcp.tool()
def list_pending_conflicts(thread_id: str) -> list[dict]:
    document = _document(thread_id)
    if document["status"] != "waiting_for_conflict":
        return []
    return get_pending_conflicts(thread_id)


# Accept or reject one conflict and queue workflow continuation
@mcp.tool()
def resolve_conflict(thread_id: str, conflict_id: str, decision: str) -> dict:
    if decision not in {"accept", "reject"}:
        raise ValueError("decision must be 'accept' or 'reject'.")
    document = _document(thread_id)
    if document["status"] != "waiting_for_conflict":
        raise ValueError(
            f"Workflow is not waiting for conflict resolution: {document['status']}")
    enqueue_workflow(
        thread_id, document["document_id"],
        {"conflict_id": conflict_id, "decision": decision},
    )
    return {"thread_id": thread_id, "status": "queued"}


# List rule violations awaiting explicit human or machine approval
@mcp.tool()
def list_pending_rule_violations(thread_id: str) -> list[dict]:
    document = _document(thread_id)
    if document["status"] != "waiting_for_rule":
        return []
    return get_pending_rule_violations(thread_id)


# Accept or reject one rule violation and queue workflow continuation
@mcp.tool()
def resolve_rule_violation(
    thread_id: str, rule_violation_id: str, decision: str
) -> dict:
    if decision not in {"accept", "reject"}:
        raise ValueError("decision must be 'accept' or 'reject'.")
    document = _document(thread_id)
    if document["status"] != "waiting_for_rule":
        raise ValueError(
            f"Workflow is not waiting for rule verification: {document['status']}")
    enqueue_workflow(
        thread_id, document["document_id"],
        {"rule_violation_id": rule_violation_id, "decision": decision},
    )
    return {"thread_id": thread_id, "status": "queued"}


# Create new business rules for future workflow runs
@mcp.tool()
def create_rules(rules: list[dict[str, str]]) -> list[dict]:
    if not rules:
        raise ValueError("At least one rule is required.")
    return insert_rules(rules)


# List the current generated deliverables
@mcp.tool()
def list_deliverables() -> list[dict]:
    return get_all_deliverables()


# Expose the current workflow status as an MCP resource
@mcp.resource("workflow://{thread_id}/status")
def workflow_status_resource(thread_id: str) -> str:
    return str(get_workflow_status(thread_id))
