import json
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from app.graph.state import AgentState
from app.schemas.deliverable import Deliverable

load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash")
structured_llm = llm.with_structured_output(Deliverable)


# Generate the master report from the facts
def generate_deliverable_node(state: AgentState) -> Dict[str, Any]:
    state_payload = {
        key: value.model_dump(mode="json") if hasattr(
            value, "model_dump") else value
        for key, value in state.items()
        if key != "master_deliverable_text"
    }

    prompt = f"""
    You are generating the Vendor Register — the master deliverable for a document intelligence pipeline that processes vendor contracts, amendments, and invoices. Your output is the single authoritative summary a business user will read instead of the underlying documents.

    INPUT DATA:
    You will receive the full pipeline state as JSON inside a <state> tag.
    Within it:

    - `facts` (or equivalent) — all extracted facts from every source document, each with a field name, value, and originating document_id.
    - `conflicts` — fields where source documents disagreed. Each entry has been through human review and includes an `active_value`, which is the confirmed correct value for that field. `active_value` is final — treat it exactly like any other fact. If `conflicts` is empty, there is nothing further to resolve; simply use `facts` as-is.
    - The state may contain other keys (metadata, document lists, thread info, etc.) that are not relevant to the report — ignore anything that isn't a fact or a resolved conflict value.

    RULES:
    1. Every fact must be reflected in the report. Do not omit, summarize away, or skip any fact, even minor ones.
    2. For fields present in `conflicts`, report ONLY the `active_value`. Write it as a normal, settled fact — the same way you'd write any undisputed value from `facts`. Do not report the other candidate values that were not chosen.
    3. Do not create any section, heading, or sentence referencing conflicts, discrepancies, disagreements, or unresolved issues. The reader should have no indication that a value was ever disputed. If you catch yourself about to write a word like "conflict," "discrepancy," or "originally stated," stop and rephrase as a plain fact.
    4. Do not infer, calculate, or add any fact not explicitly present in the state. If information seems incomplete, state only what is given — never fill gaps with assumptions.
    5. Organize the report logically (e.g., by vendor/transaction, then by category: parties, contract terms, financials, key dates, amendment history, invoice details) rather than by source document.
    6. Output only the report itself — no preamble, no meta-commentary about how it was generated.

    USER:
    <state>
    {json.dumps(state_payload, ensure_ascii=False, default=str)}
    </state>

    Generate the Vendor Register summary report now.
    """

    try:
        result = structured_llm.invoke(prompt)
        return {"master_deliverable_text": result.content, "error": None}
    except Exception as exc:
        return {"error": f"Error in generate_deliverable node: {exc}"}
