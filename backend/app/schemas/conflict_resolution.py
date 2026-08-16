from pydantic import BaseModel, Field


class ConflictResolutionDecision(BaseModel):
    conflict_id: str = Field(min_length=1)
    selected_document_id: str = Field(min_length=1)


class ConflictResolutionRequest(BaseModel):
    thread_id: str = Field(min_length=1)
    decision: ConflictResolutionDecision
