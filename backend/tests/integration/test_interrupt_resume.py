from __future__ import annotations

import psycopg
import pytest
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.db.conflicts import insert_conflicts, resolve_conflict
from app.db.documents import find_document_by_thread_id, register_document
from app.graph.workflow import build_extraction_graph

from tests.test_helpers import PromptAwareProvider


@pytest.mark.asyncio
async def test_resume_uses_postgres_checkpoint_without_rerunning_extraction(
    postgres_url, monkeypatch, tmp_path, deterministic_embeddings
):
    from app.graph.nodes import analyze_and_extract
    from app.schemas.deliverable import Deliverable
    from app.schemas.extraction import DocumentExtractionResult

    path = tmp_path / "resume.txt"
    path.write_text(
        "Vendor ResumeVendor. Total amount is $100.", encoding="utf-8")
    registration = register_document({"document_path": str(path)})
    provider = PromptAwareProvider({"ResumeVendor": DocumentExtractionResult.model_validate(
        {"dt": "invoice", "vn": "ResumeVendor",
            "cn": "Client", "sum": "Saved summary", "fac": []}
    )})
    monkeypatch.setattr("app.services.model_provider._provider", provider)
    monkeypatch.setattr(analyze_and_extract, "generate_embeddings", lambda chunks: [
                        {**c, "embedding": deterministic_embeddings} for c in chunks])
    monkeypatch.setattr(analyze_and_extract, "generate_text_embedding",
                        lambda _text: deterministic_embeddings)
    conflict = insert_conflicts(registration["thread_id"], [{"field_name": "total", "description": "Review total", "conflicting_sources": [
                                {"document_id": registration["document_id"], "value": "$100"}]}])[0]
    config: RunnableConfig = {"configurable": {
        "thread_id": registration["thread_id"]}}
    state = {"document_id": registration["document_id"], "document_path": str(
        path), "thread_id": registration["thread_id"], "extracted_facts": None, "matched_document_ids": [], "error": None}

    async with AsyncPostgresSaver.from_conn_string(postgres_url) as saver:
        await saver.setup()
        interrupted = await build_extraction_graph(saver).ainvoke(state, config=config)
        assert interrupted.get("__interrupt__")
    extraction_calls = provider.calls[(
        DocumentExtractionResult, "ResumeVendor")]
    with psycopg.connect(postgres_url) as connection:
        assert connection.execute("SELECT count(*) FROM checkpoints WHERE thread_id = %s",
                                  (registration["thread_id"],)).fetchone()[0] > 0

    resolve_conflict(registration["thread_id"], conflict["id"], "accept")
    async with AsyncPostgresSaver.from_conn_string(postgres_url) as saver:
        await saver.setup()
        resumed = await build_extraction_graph(saver).ainvoke(Command(resume={"conflict_id": conflict["id"], "decision": "accept"}), config=config)
    assert provider.calls[(DocumentExtractionResult,
                           "ResumeVendor")] == extraction_calls
    assert provider.calls[(Deliverable, "ResumeVendor")] >= 1
    assert resumed["master_deliverable_text"] == "ResumeVendor"
    assert find_document_by_thread_id(registration["thread_id"])[
        "status"] == "completed"
