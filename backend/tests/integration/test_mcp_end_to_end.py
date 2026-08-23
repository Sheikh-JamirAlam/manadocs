from __future__ import annotations

import asyncio

import pytest
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app import mcp_server
from app.db.conflicts import insert_conflicts
from app.db.documents import register_document
from app.graph.workflow import build_extraction_graph
from app.schemas.deliverable import Deliverable
from app.schemas.extraction import DocumentExtractionResult
from app.services import workflow_queue
from tests.test_helpers import PromptAwareProvider


async def _wait_for_status(thread_id: str, expected: set[str], timeout: float = 10):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        status = mcp_server.get_workflow_status(thread_id)["status"]
        if status in expected:
            return status
        await asyncio.sleep(0.05)
    raise AssertionError(f"workflow did not reach {expected}")


async def _interrupted_workflow(postgres_url, monkeypatch, tmp_path, deterministic_embeddings):
    from app.graph.nodes import analyze_and_extract

    path = tmp_path / "mcp.txt"
    path.write_text("Vendor Acme. Total amount is $100.", encoding="utf-8")
    registration = register_document({"document_path": str(path)})
    provider = PromptAwareProvider({"Acme": DocumentExtractionResult.model_validate({
        "dt": "invoice", "vn": "Acme", "cn": "Client", "sum": "Acme", "fac": []
    })})
    monkeypatch.setattr("app.services.model_provider._provider", provider)
    monkeypatch.setattr(analyze_and_extract, "generate_embeddings", lambda chunks: [
                        {**c, "embedding": deterministic_embeddings} for c in chunks])
    monkeypatch.setattr(analyze_and_extract, "generate_text_embedding",
                        lambda _text: deterministic_embeddings)
    conflict = insert_conflicts(registration["thread_id"], [{
        "field_name": "total_amount", "description": "Conflicting totals.",
        "conflicting_sources": [{"document_id": registration["document_id"], "value": "$100"}],
    }])[0]
    state = {"document_id": registration["document_id"], "document_path": str(
        path), "thread_id": registration["thread_id"], "extracted_facts": None, "matched_document_ids": [], "error": None}
    async with AsyncPostgresSaver.from_conn_string(postgres_url) as saver:
        await saver.setup()
        result = await build_extraction_graph(saver).ainvoke(state, config={"configurable": {"thread_id": registration["thread_id"]}})
    assert result.get("__interrupt__")
    return registration, conflict, provider


@pytest.mark.asyncio
async def test_mcp_resolution_resumes_and_completes_real_workflow(postgres_url, monkeypatch, tmp_path, deterministic_embeddings):
    registration, conflict, provider = await _interrupted_workflow(postgres_url, monkeypatch, tmp_path, deterministic_embeddings)
    thread_id = registration["thread_id"]
    extraction_calls = provider.calls[(DocumentExtractionResult, "Acme")]
    assert mcp_server.get_workflow_status(
        thread_id)["status"] == "waiting_for_conflict"
    assert mcp_server.list_pending_conflicts(
        thread_id)[0]["id"] == conflict["id"]
    workflow_queue.start_worker()
    try:
        assert mcp_server.resolve_conflict(thread_id, conflict["id"], "accept")[
            "status"] == "queued"
        assert await _wait_for_status(thread_id, {"completed"}) == "completed"
    finally:
        await workflow_queue.stop_worker()
    assert provider.calls[(DocumentExtractionResult,
                           "Acme")] == extraction_calls
    assert provider.calls[(Deliverable, "Acme")] >= 1


@pytest.mark.asyncio
async def test_mcp_flag_path_completes_and_preserves_finding(postgres_url, monkeypatch, tmp_path, deterministic_embeddings):
    registration, conflict, provider = await _interrupted_workflow(postgres_url, monkeypatch, tmp_path, deterministic_embeddings)
    workflow_queue.start_worker()
    try:
        mcp_server.resolve_conflict(
            registration["thread_id"], conflict["id"], "reject")
        status = await _wait_for_status(registration["thread_id"], {"completed", "failed"})
    finally:
        await workflow_queue.stop_worker()
    assert status == "completed"
    assert provider.calls[(Deliverable, "Acme")] >= 1


def test_mcp_invalid_resolution_is_rejected(postgres_url):
    with pytest.raises(ValueError, match="Workflow document not found"):
        mcp_server.resolve_conflict(
            "does-not-exist", "does-not-exist", "accept")
