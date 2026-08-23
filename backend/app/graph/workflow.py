import os

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph

from app.graph.nodes.analyze_and_extract import analyze_and_extract_node
from app.graph.nodes.audit_document_conflicts import audit_document_conflicts_node
from app.graph.nodes.find_matching_documents import find_matching_documents_node
from app.graph.nodes.generate_deliverable import generate_deliverable_node
from app.graph.nodes.check_against_rule import check_against_rule_node
from app.graph.state import AgentState

from dotenv import load_dotenv

load_dotenv()


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    return (
        f"postgresql://{os.getenv('PGUSER', 'postgres')}:"
        f"{os.getenv('PGPASSWORD', '')}@"
        f"{os.getenv('PGHOST', 'localhost')}:{os.getenv('PGPORT', '5432')}/"
        f"{os.getenv('PGDATABASE', 'doctask')}"
    )


def build_extraction_graph(checkpointer: AsyncPostgresSaver):
    workflow = StateGraph(AgentState)
    workflow.add_node("analyze_and_extract", analyze_and_extract_node)
    workflow.add_node("audit_document_conflicts",
                      audit_document_conflicts_node)
    workflow.add_node("find_matching_documents",
                      find_matching_documents_node)
    workflow.add_node("generate_deliverable",
                      generate_deliverable_node)
    workflow.add_node("check_against_rule", check_against_rule_node)
    workflow.add_edge(START, "analyze_and_extract")

    def next_or_end(state: AgentState, next_node: str) -> str:
        return END if state.get("error") else next_node

    workflow.add_conditional_edges(
        "analyze_and_extract",
        lambda state: next_or_end(state, "find_matching_documents"),
        [END, "find_matching_documents"],
    )
    workflow.add_conditional_edges(
        "find_matching_documents",
        lambda state: next_or_end(state, "audit_document_conflicts"),
        [END, "audit_document_conflicts"],
    )
    workflow.add_conditional_edges(
        "audit_document_conflicts",
        lambda state: next_or_end(state, "check_against_rule"),
        [END, "check_against_rule"],
    )
    workflow.add_conditional_edges(
        "check_against_rule",
        lambda state: next_or_end(state, "generate_deliverable"),
        [END, "generate_deliverable"],
    )
    workflow.set_finish_point("generate_deliverable")
    return workflow.compile(checkpointer=checkpointer)
