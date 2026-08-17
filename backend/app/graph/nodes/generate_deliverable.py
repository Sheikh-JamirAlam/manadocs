import json
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from app.graph.state import AgentState
from app.db.deliverables import (
    find_by_related_document_ids, insert_deliverable, update_deliverable)
from app.schemas.deliverable import Deliverable

load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash")
structured_llm = llm.with_structured_output(Deliverable)


# Generate the master report from the facts
def generate_deliverable_node(state: AgentState) -> Dict[str, Any]:
    matched_document_ids = [str(value) for value in (
        state.get("matched_document_ids") or [])]
    existing_deliverable = find_by_related_document_ids(matched_document_ids)
    extracted_facts = state.get("extracted_facts")
    if hasattr(extracted_facts, "model_dump"):
        extracted_facts = extracted_facts.model_dump(mode="json")
    state_payload = {
        "extracted_facts": extracted_facts,
        "rule_violations": state.get("rule_violations") or [],
    }

    is_update = existing_deliverable is not None

    mode_block = (
        f"""
    MODE: UPDATE_TRANSACTION
    This transaction already has a Vendor Register entry. You must produce the COMPLETE, updated register content for this transaction — not just what changed.
    Merge the new facts and findings into the existing content below. Preserve every prior fact and finding unless the new facts explicitly supersede them (superseded values will already be reflected as the settled value in `extracted_facts` — do not flag them as conflicts).

    EXISTING TRANSACTION CONTENT:
    {json.dumps(existing_deliverable["content"], ensure_ascii=False, default=str)}
    """
        if is_update else
        """
    MODE: NEW_TRANSACTION
    This is the first document seen for this transaction. There is no prior content.
    Generate the initial Vendor Register entry from the facts and findings provided.
    """
    )

    prompt = f"""
    You are generating the Vendor Register — the master deliverable for a document intelligence pipeline that processes vendor contracts, amendments, and invoices. Your output is the single authoritative summary a business user will read instead of the underlying documents.

    {mode_block}

    INPUT DATA:
    You will receive the full pipeline state as JSON inside a <state> tag.
    Within it:
    - `extracted_facts` — verified, conflict-resolved facts relevant to this transaction.
    - `rule_violations` — verified rule findings to include in the report. May be empty.

    REQUIRED STRUCTURE:
    The report content must follow this fixed section structure, in this order, every time:
    1. Transaction Overview — parties involved, transaction type, current status.
    2. Key Terms — pricing, dates, deliverables, obligations, and other material terms.
    3. Other Facts — any extracted facts that don't fit the categories above.
    4. Findings — compliance/rule findings for this transaction (see FINDINGS RULE below).
    Use these section headers verbatim so every deliverable in the register looks and reads consistently across transactions.

    FINDINGS RULE:
    - If `rule_violations` is empty or absent, the Findings section must contain exactly: "No Findings."
      Do not invent, infer, or imply any compliance issue when there are none.
    - If `rule_violations` is non-empty, list each one under Findings with its description and citation.
    - Never put rule/compliance content anywhere outside the Findings section.

    RULES:
    1. Every fact in `extracted_facts` must be reflected in the report. Do not omit, summarize away, or skip any fact, even minor ones.
    2. Do not infer or add facts not explicitly present in the inputs.
    3. Do not infer or add findings not explicitly present in `rule_violations`.
    4. Output must be the FULL current state of the register for this transaction, self-contained and readable without the source documents.
    5. Return a concise title and the complete report content, following the REQUIRED STRUCTURE above.

    USER:
    <state>
    {json.dumps(state_payload, ensure_ascii=False, default=str)}
    </state>

    Generate the Vendor Register summary report now.
    """

    try:
        result = structured_llm.invoke(prompt)
        related_ids = list(dict.fromkeys(
            (existing_deliverable or {}).get("related_document_ids", []) +
            matched_document_ids +
            ([str(state.get("document_id"))] if state.get("document_id") else [])
        ))
        if existing_deliverable:
            stored = update_deliverable(
                existing_deliverable["id"], result.title, result.content, related_ids)
        else:
            stored = insert_deliverable(
                result.title, result.content, related_ids)
        return {"master_deliverable_text": stored["content"], "error": None}
    except Exception as exc:
        return {"error": f"Error in generate_deliverable node: {exc}"}
