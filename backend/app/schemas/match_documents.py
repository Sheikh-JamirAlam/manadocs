from typing import List
from pydantic import BaseModel, Field, ConfigDict


class TransactionMatchResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    matched_document_ids: List[str] = Field(
        alias="mids", description="List of document_ids that belong to the exact same commercial transaction as the incoming document.")
    reasoning: str = Field(
        alias="rsn", description="Brief narrative explaining why these specific documents match the transaction and why others were excluded.")
