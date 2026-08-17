from typing import TypedDict, Optional, Dict, Any, List
from app.schemas.extraction import DocumentExtractionResult


class AgentState(TypedDict):
    # Initial input parameters
    document_id: Optional[str]
    document_path: str
    thread_id: Optional[str]

    # Data populated by analyze_and_extract node
    extracted_facts: Optional[DocumentExtractionResult]

    # Data populated by future nodes
    proposed_updates: Optional[List[Dict[str, Any]]]
    rule_violations: Optional[List[Dict[str, Any]]]
    conflicts: Optional[List[Dict[str, Any]]]
    master_deliverable_text: Optional[str]

    # Matched documents_id with current document
    matched_document_ids: Optional[List[str]]

    # Error tracking
    error: Optional[str]
