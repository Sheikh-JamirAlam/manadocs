from __future__ import annotations

import asyncio

import psycopg
import pytest
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.db.documents import register_document
from app.graph.workflow import build_extraction_graph
from tests.test_helpers import PromptAwareProvider


@pytest.mark.asyncio
async def test_concurrent_runs_keep_vendor_data_and_checkpoints_isolated(postgres_url, monkeypatch, tmp_path, deterministic_embeddings):
    from app.graph.nodes import analyze_and_extract
    from app.schemas.extraction import DocumentExtractionResult

    paths = [tmp_path / "a.txt", tmp_path / "b.txt"]
    vendors = ["Vendor-A", "Vendor-B"]
    for path, vendor in zip(paths, vendors):
        path.write_text(
            f"Vendor {vendor}. Total amount is ${100 if vendor == 'Vendor-A' else 200}.", encoding="utf-8")
    registrations = [register_document(
        {"document_path": str(path)}) for path in paths]
    provider = PromptAwareProvider({vendor: DocumentExtractionResult.model_validate(
        {"dt": "invoice", "vn": vendor, "cn": "Client", "sum": vendor, "fac": []}) for vendor in vendors})
    monkeypatch.setattr("app.services.model_provider._provider", provider)
    monkeypatch.setattr(analyze_and_extract, "generate_embeddings", lambda chunks: [
                        {**c, "embedding": deterministic_embeddings} for c in chunks])
    monkeypatch.setattr(analyze_and_extract, "generate_text_embedding",
                        lambda _text: deterministic_embeddings)
    async with AsyncPostgresSaver.from_conn_string(postgres_url) as saver:
        await saver.setup()
        graph = build_extraction_graph(saver)

        async def run(registration, path):
            return await graph.ainvoke({"document_id": registration["document_id"], "document_path": str(path), "thread_id": registration["thread_id"], "extracted_facts": None, "matched_document_ids": [], "error": None}, config={"configurable": {"thread_id": registration["thread_id"]}})
        results = await asyncio.gather(*(run(r, p) for r, p in zip(registrations, paths)))
    assert [vendor in result["master_deliverable_text"]
            for vendor, result in zip(vendors, results)] == [True, True]
    with psycopg.connect(postgres_url) as connection:
        rows = connection.execute("SELECT DISTINCT thread_id FROM checkpoints WHERE thread_id = ANY(%s)", ([
                                  r["thread_id"] for r in registrations],)).fetchall()
    assert {row[0] for row in rows} == {r["thread_id"] for r in registrations}
