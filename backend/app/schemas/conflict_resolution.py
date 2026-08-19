from pydantic import BaseModel, Field


class ConflictResolutionDecision(BaseModel):
    conflict_id: str = Field(min_length=1)
    decision: str = Field(pattern="^(accept|reject)$")


class ConflictResolutionRequest(BaseModel):
    thread_id: str = Field(min_length=1)
    decision: ConflictResolutionDecision
