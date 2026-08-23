from __future__ import annotations

import os
import sys
import asyncio
from pathlib import Path

import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


@pytest.fixture(scope="session")
def event_loop_policy():
    if sys.platform == "win32":
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.get_event_loop_policy()


SCHEMA = ROOT / "scripts" / "initial_schema.sql"


# Run tests against an isolated real pgvector PostgreSQL instance
@pytest.fixture(scope="session")
def postgres_url():
    with PostgresContainer("pgvector/pgvector:pg17") as postgres:
        url = postgres.get_connection_url().replace(
            "postgresql+psycopg2://", "postgresql://")
        with psycopg.connect(url) as connection:
            connection.execute(SCHEMA.read_text(encoding="utf-8"))
            connection.commit()
        os.environ["DATABASE_URL"] = url
        yield url


@pytest.fixture(autouse=True)
def clean_database(postgres_url):
    with psycopg.connect(postgres_url) as connection:
        tables = [
            "workflow_events", "deliverables", "rule_violations", "conflicts",
            "document_chunks", "document_facts", "rules", "documents",
            "checkpoints", "checkpoint_writes", "checkpoint_blobs",
        ]
        existing = connection.execute(
            "SELECT relname FROM pg_class "
            "WHERE relnamespace = (SELECT oid FROM pg_namespace "
            "WHERE nspname = current_schema()) AND relname = ANY(%s)",
            (tables,),
        ).fetchall()
        present = [row[0] for row in existing]
        if present:
            connection.execute(
                "TRUNCATE "
                + ", ".join(f'"{table}"' for table in present)
                + " RESTART IDENTITY CASCADE"
            )
        connection.commit()


@pytest.fixture
def deterministic_embeddings():
    return [0.0] * 1536
