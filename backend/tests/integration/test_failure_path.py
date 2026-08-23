from __future__ import annotations

from app.db.documents import find_document_by_thread_id, register_document
from app.db.facts import get_one_fact
from app.graph.nodes.analyze_and_extract import analyze_and_extract_node
from app.graph.nodes.generate_deliverable import generate_deliverable_node
from app.services.model_provider import set_model_provider


class FailingProvider:
    def __init__(self):
        self.calls = 0

    def structured(self, _model, _schema):
        self.calls += 1
        raise RuntimeError("Gemini quota exceeded")


def test_provider_failure_marks_document_failed(postgres_url, monkeypatch, tmp_path):
    document = tmp_path / "quota.txt"
    document.write_text("Vendor Acme. Total amount is $100.", encoding="utf-8")
    registration = register_document({"document_path": str(document)})

    from app.graph.nodes import analyze_and_extract
    monkeypatch.setattr(analyze_and_extract, "parse_document", lambda _path: [
                        {"text": "Vendor Acme.", "chunk_index": 0, "page_start": 1, "page_end": 1}])
    monkeypatch.setattr(analyze_and_extract, "generate_embeddings", lambda chunks: [
                        {**chunk, "embedding": [0.0] * 1536} for chunk in chunks])
    set_model_provider(FailingProvider())

    result = analyze_and_extract_node({
        "document_id": registration["document_id"],
        "document_path": str(document),
        "thread_id": registration["thread_id"],
        "extracted_facts": None,
        "matched_document_ids": [],
        "error": None,
    })

    stored = find_document_by_thread_id(registration["thread_id"])
    assert "Gemini quota exceeded" in result["error"]
    assert stored["status"] == "failed"
    assert "Gemini quota exceeded" in stored["error_message"]
    assert get_one_fact(registration["document_id"]) is None


def test_empty_document_is_rejected_before_llm_ingestion(postgres_url, monkeypatch, tmp_path):
    document = tmp_path / "empty.txt"
    document.write_text("   \n\t", encoding="utf-8")
    registration = register_document({"document_path": str(document)})
    provider = FailingProvider()
    set_model_provider(provider)
    monkeypatch.setattr(
        "app.graph.nodes.analyze_and_extract.parse_document", lambda _path: [])

    result = analyze_and_extract_node({"document_id": registration["document_id"], "document_path": str(
        document), "thread_id": registration["thread_id"], "extracted_facts": None, "matched_document_ids": [], "error": None})

    assert provider.calls == 0
    assert result["error"] == "The document contains no extractable text."
    assert find_document_by_thread_id(registration["thread_id"])[
        "status"] == "failed"


def test_embedding_failure_is_explicit(postgres_url, monkeypatch, tmp_path):
    document = tmp_path / "embedding.txt"
    document.write_text("Vendor Acme. Total amount is $100.", encoding="utf-8")
    registration = register_document({"document_path": str(document)})
    monkeypatch.setattr("app.graph.nodes.analyze_and_extract.generate_embeddings", lambda _chunks: (
        _ for _ in ()).throw(RuntimeError("embedding service unavailable")))

    result = analyze_and_extract_node({"document_id": registration["document_id"], "document_path": str(
        document), "thread_id": registration["thread_id"], "extracted_facts": None, "matched_document_ids": [], "error": None})

    assert "embedding service unavailable" in result["error"]
    assert find_document_by_thread_id(registration["thread_id"])[
        "status"] == "failed"


def test_deliverable_rejects_missing_extraction_state(postgres_url, monkeypatch, tmp_path):
    document = tmp_path / "partial.txt"
    document.write_text("Vendor Acme.", encoding="utf-8")
    registration = register_document({"document_path": str(document)})
    provider = FailingProvider()
    set_model_provider(provider)

    result = generate_deliverable_node({"document_id": registration["document_id"], "thread_id": registration["thread_id"],
                                       "extracted_facts": None, "matched_document_ids": [], "rule_violations": [], "conflicts": []})

    assert result["error"] is not None
    assert provider.calls == 0
