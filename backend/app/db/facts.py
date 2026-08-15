from typing import Any, Dict, Mapping, Union
from psycopg.types.json import Jsonb
from app.db.connection import database_connection
from app.schemas.extraction import DocumentExtractionResult


def insert_facts(
    document_id: str,
    extraction_result: Union[DocumentExtractionResult, Mapping[str, Any]],
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
                    INSERT INTO document_facts (document_id, facts)
                    VALUES (%s, %s)
                    ON CONFLICT (document_id)
                    DO UPDATE SET
                        facts = EXCLUDED.facts,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (document_id, Jsonb(facts_payload)),
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
            "document_status": "processed",
            "error": None,
        }
    except Exception as exc:
        return {"error": f"Fact insertion failed: {exc}"}
