from typing import List

from pydantic import BaseModel, Field


class Deliverable(BaseModel):
    title: str = Field(
        alias="t", default="Vendor Register", description="Title of the transaction deliverable.")
    content: str = Field(
        alias="c", description="The master deliverable report for as plain text.")
