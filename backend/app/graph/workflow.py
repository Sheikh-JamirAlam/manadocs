import os

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import START, StateGraph

from app.graph.nodes.analyze_and_extract import analyze_and_extract_node
from app.graph.nodes.audit_document_conflicts import audit_document_conflicts_node
from app.graph.state import AgentState

from dotenv import load_dotenv

load_dotenv()


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    return (
        f"postgresql://{os.getenv('PGUSER', os.getenv('POSTGRES_USER', 'postgres'))}:"
        f"{os.getenv('PGPASSWORD', os.getenv('POSTGRES_PASSWORD', ''))}@"
        f"{os.getenv('PGHOST', 'localhost')}:{os.getenv('PGPORT', '5432')}/"
        f"{os.getenv('PGDATABASE', os.getenv('POSTGRES_DB', 'doctask'))}"
    )


def build_extraction_graph(checkpointer: AsyncPostgresSaver):
    workflow = StateGraph(AgentState)
    workflow.add_node("analyze_and_extract", analyze_and_extract_node)
    workflow.add_node("audit_document_conflicts",
                      audit_document_conflicts_node)
    workflow.add_edge(START, "analyze_and_extract")
    workflow.add_edge("analyze_and_extract", "audit_document_conflicts")
    return workflow.compile(checkpointer=checkpointer)
