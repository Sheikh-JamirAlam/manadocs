import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Mapping, Optional, Union
from psycopg.types.json import Jsonb
from app.db.connection import database_connection
from app.schemas.extraction import DocumentExtractionResult


# Some documents name might be slightly different
def normalize_name(value: Optional[str]) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


# Find likely matching fact records using normalized and fuzzy party names
def query_facts(
    vendor_name: Optional[str] = None,
    client_name: Optional[str] = None,
    exclude_document_id: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    vendor = normalize_name(vendor_name)
    client = normalize_name(client_name)
    if not vendor and not client:
        return []
    if limit <= 0:
        raise ValueError("limit must be greater than zero")

    try:
        conditions = ["df.summary IS NOT NULL"]
        params: List[Any] = []
        if exclude_document_id:
            conditions.append("df.document_id <> %s")
            params.append(exclude_document_id)

        name_terms = [term for term in (vendor, client) if term]
        conditions.append(
            "(" + " OR ".join(
                "regexp_replace(lower(coalesce(df.vendor_name, '') || coalesce(df.client_name, '')), '[^a-z0-9]', '', 'g') LIKE %s"
                for _ in name_terms
            ) + ")"
        )
        params.extend(f"%{term[:4]}%" for term in name_terms)

        with database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT df.document_id, df.vendor_name, df.client_name, df.summary, df.summary_embedding, df.facts
                    FROM document_facts AS df
                    WHERE {' AND '.join(conditions)}
                    LIMIT %s
                    """,
                    (*params, limit * 5),
                )
                rows = cursor.fetchall()

        results = []
        for row in rows:
            row_vendor = normalize_name(row[1])
            row_client = normalize_name(row[2])
            scores = []
            if vendor and row_vendor:
                scores.append(SequenceMatcher(
                    None, vendor, row_vendor).ratio())
            if client and row_client:
                scores.append(SequenceMatcher(
                    None, client, row_client).ratio())
            if scores and max(scores) >= 0.72:
                results.append({
                    "document_id": row[0],
                    "vendor_name": row[1],
                    "client_name": row[2],
                    "summary": row[3],
                    "summary_embedding": row[4],
                    "facts": row[5],
                    "name_match_score": max(scores),
                })
        return results[:limit]
    except Exception as exc:
        raise RuntimeError(f"Fact lookup failed: {exc}") from exc


# Get one stored fact record by document id
def get_one_fact(document_id: str) -> Optional[Dict[str, Any]]:
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT document_id, vendor_name, client_name, summary, summary_embedding, facts
                FROM document_facts
                WHERE document_id = %s
                """,
                (document_id,),
            )
            row = cursor.fetchone()
    if not row:
        return None
    return {
        "document_id": row[0],
        "vendor_name": row[1],
        "client_name": row[2],
        "summary": row[3],
        "facts": row[5],
    }


def get_one_fact_with_embedding(document_id: str) -> Optional[Dict[str, Any]]:
    with database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT document_id, vendor_name, client_name, summary, summary_embedding, facts
                FROM document_facts
                WHERE document_id = %s
                """,
                (document_id,),
            )
            row = cursor.fetchone()
    if not row:
        return None
    return {
        "document_id": row[0],
        "vendor_name": row[1],
        "client_name": row[2],
        "summary": row[3],
        "summary_embedding": row[4],
        "facts": row[5],
    }


# Find facts with similar summaries using vector embeddings
def vector_query_similar_facts(
    summary_embedding: List[float],
    exclude_document_id: Optional[str] = None,
    candidate_document_ids: Optional[List[str]] = None,
    limit: int = 10,
    max_distance: float = 0.35,
) -> List[Dict[str, Any]]:
    if not summary_embedding:
        return []
    if limit <= 0:
        raise ValueError("limit must be greater than zero")

    conditions = ["df.summary_embedding IS NOT NULL"]
    params: List[Any] = [summary_embedding]
    if exclude_document_id:
        conditions.append("df.document_id <> %s")
        params.append(exclude_document_id)
    if candidate_document_ids is not None:
        if not candidate_document_ids:
            return []
        placeholders = ", ".join(["%s"] * len(candidate_document_ids))
        conditions.append(f"df.document_id IN ({placeholders})")
        params.extend(candidate_document_ids)
    params.extend([summary_embedding, max_distance, summary_embedding, limit])

    try:
        with database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT df.document_id, df.vendor_name, df.client_name, df.summary, df.summary_embedding, df.facts, df.summary_embedding <=> %s AS distance
                    FROM document_facts AS df
                    WHERE {' AND '.join(conditions)}
                      AND df.summary_embedding <=> %s <= %s
                    ORDER BY df.summary_embedding <=> %s
                    LIMIT %s
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall()
        return [
            {
                "document_id": row[0],
                "vendor_name": row[1],
                "client_name": row[2],
                "summary": row[3],
                "summary_embedding": row[4],
                "facts": row[5],
                "distance": row[6],
            }
            for row in rows
        ]
    except Exception as exc:
        raise RuntimeError(f"Similar fact lookup failed: {exc}") from exc


# Add extracted facts to database
def insert_facts(
    document_id: str,
    extraction_result: Union[DocumentExtractionResult, Mapping[str, Any]],
    summary_embedding: Any = None,
) -> Dict[str, Any]:
    if not document_id:
        return {"error": "A document_id is required to insert facts."}

    try:
        if isinstance(extraction_result, DocumentExtractionResult):
            facts_payload = extraction_result.model_dump(mode="json")
        else:
            facts_payload = dict(extraction_result)

        with database_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO document_facts (document_id, vendor_name, client_name, summary, summary_embedding, facts)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (document_id)
                    DO UPDATE SET
                        vendor_name = EXCLUDED.vendor_name,
                        client_name = EXCLUDED.client_name,
                        summary = EXCLUDED.summary,
                        summary_embedding = EXCLUDED.summary_embedding,
                        facts = EXCLUDED.facts,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        document_id,
                        facts_payload.get("vendor_name"),
                        facts_payload.get("client_name"),
                        facts_payload.get("summary"),
                        summary_embedding,
                        Jsonb(facts_payload),
                    ),
                )

                cursor.execute(
                    """
                    UPDATE documents
                    SET document_type = %s,
                        vendor_name = %s,
                        status = %s,
                        error_message = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING id
                    """,
                    (
                        facts_payload["document_type"],
                        facts_payload["vendor_name"],
                        "processed",
                        document_id,
                    ),
                )
                if not cursor.fetchone():
                    raise ValueError(
                        f"Document record not found for id: {document_id}")

        return {
            "document_id": document_id,
            "facts_inserted": len(facts_payload["facts"]),
            "document_type": facts_payload["document_type"],
            "vendor_name": facts_payload["vendor_name"],
            "client_name": facts_payload.get("client_name"),
            "summary": facts_payload.get("summary"),
            "document_status": "processed",
            "error": None,
        }
    except Exception as exc:
        return {"error": f"Fact insertion failed: {exc}"}
