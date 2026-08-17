from pydantic import BaseModel, Field


class Deliverable(BaseModel):
    content: str = Field(
        alias="c", description="The master deliverable report for the document as plain text.")
