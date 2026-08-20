from __future__ import annotations

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError:
    # MCP 2 moved FastMCP to MCPServer. Keep the v1 import working for
    # environments that still resolve the 1.x SDK line.
    from mcp.server import MCPServer as FastMCP

from app.db.conflicts import get_pending_conflicts
from app.db.deliverables import get_all_deliverables
from app.db.documents import find_document_by_thread_id
from app.db.rules import get_pending_rule_violations, insert_rules
from app.db.workflow_events import get_workflow_events as read_workflow_events
from app.services.workflow_queue import enqueue_workflow

mcp = FastMCP("DocTask")


def _document(thread_id: str) -> dict:
    document = find_document_by_thread_id(thread_id)
    if not document:
        raise ValueError("Workflow document not found.")
    return document


@mcp.tool()
def get_workflow_status(thread_id: str) -> dict:
    """Get the current status and active node for a workflow."""
    return _document(thread_id)


@mcp.tool()
def get_workflow_events(thread_id: str, after_id: int = 0) -> list[dict]:
    """Read durable workflow progress events after an event ID."""
    _document(thread_id)
    return read_workflow_events(thread_id, after_id=after_id)


@mcp.tool()
def list_pending_conflicts(thread_id: str) -> list[dict]:
    """List conflicts awaiting explicit human or machine approval."""
    document = _document(thread_id)
    if document["status"] != "waiting_for_conflict":
        return []
    return get_pending_conflicts(thread_id)


@mcp.tool()
def resolve_conflict(thread_id: str, conflict_id: str, decision: str) -> dict:
    """Accept or reject one conflict and queue workflow continuation."""
    if decision not in {"accept", "reject"}:
        raise ValueError("decision must be 'accept' or 'reject'.")
    document = _document(thread_id)
    if document["status"] != "waiting_for_conflict":
        raise ValueError(f"Workflow is not waiting for conflict resolution: {document['status']}")
    enqueue_workflow(
        thread_id, document["document_id"],
        {"conflict_id": conflict_id, "decision": decision},
    )
    return {"thread_id": thread_id, "status": "queued"}


@mcp.tool()
def list_pending_rule_violations(thread_id: str) -> list[dict]:
    """List rule violations awaiting explicit human or machine approval."""
    document = _document(thread_id)
    if document["status"] != "waiting_for_rule":
        return []
    return get_pending_rule_violations(thread_id)


@mcp.tool()
def resolve_rule_violation(
    thread_id: str, rule_violation_id: str, decision: str
) -> dict:
    """Accept or reject one rule violation and queue workflow continuation."""
    if decision not in {"accept", "reject"}:
        raise ValueError("decision must be 'accept' or 'reject'.")
    document = _document(thread_id)
    if document["status"] != "waiting_for_rule":
        raise ValueError(f"Workflow is not waiting for rule verification: {document['status']}")
    enqueue_workflow(
        thread_id, document["document_id"],
        {"rule_violation_id": rule_violation_id, "decision": decision},
    )
    return {"thread_id": thread_id, "status": "queued"}


@mcp.tool()
def create_rules(rules: list[dict[str, str]]) -> list[dict]:
    """Create active business rules used by future workflow runs."""
    if not rules:
        raise ValueError("At least one rule is required.")
    return insert_rules(rules)


@mcp.tool()
def list_deliverables() -> list[dict]:
    """List the current generated deliverables."""
    return get_all_deliverables()


@mcp.resource("workflow://{thread_id}/status")
def workflow_status_resource(thread_id: str) -> str:
    """Expose the current workflow status as an MCP resource."""
    return str(get_workflow_status(thread_id))
