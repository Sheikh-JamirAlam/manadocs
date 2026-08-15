import os
import psycopg
from pgvector.psycopg import register_vector


def database_connection() -> psycopg.Connection:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        connection = psycopg.connect(database_url)
    else:
        connection = psycopg.connect(
            host=os.getenv("PGHOST", "localhost"),
            port=os.getenv("PGPORT", "5432"),
            dbname=os.getenv("PGDATABASE", os.getenv(
                "POSTGRES_DB", "doctask")),
            user=os.getenv("PGUSER", os.getenv("POSTGRES_USER", "postgres")),
            password=os.getenv("PGPASSWORD", os.getenv(
                "POSTGRES_PASSWORD", "")),
        )

    register_vector(connection)
    return connection
