from typing import List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


class Citation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    quote: str = Field(
        alias="q", description="Exact verbatim excerpt from the source supporting this value.")
    page_number: Optional[int] = Field(
        alias="p", default=None, description="1-based page number where the quote is located.")
    section_header: Optional[str] = Field(
        alias="sh", default=None, description="Section/header where this quote appeared (if applicable).")
    character_index: Optional[int] = Field(
        alias="ci", default=None, description="Zero-based character offset of the citation within its line.",)
    line_number: Optional[int] = Field(
        alias="ln", default=None, description="One-based line number containing the citation.",)


class ConflictingSourceValue(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    document_id: str = Field(alias="did", description="UUID of the document.")
    doc_name: Optional[str] = Field(
        alias="dn", default=None, description="Filename/title.")
    value: Union[str, int, float, bool] = Field(
        alias="v", description="The conflicting value extracted from this document.")
    description: str = Field(
        alias="d", description="The conflicting description extracted from this document.")
    citation: Citation = Field(
        alias="cit", description="Exact location and quote backing this specific value.")


class ConflictFinding(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    field_name: str = Field(
        alias="fn", description="Field name in conflict (e.g., 'hourly_rate').")
    description: str = Field(
        alias="desc", description="Explanation of the discrepancy.")
    conflicting_sources: List[ConflictingSourceValue] = Field(
        alias="cs", description="List of differing source values.")


class ConflictAuditResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    conflicts: List[ConflictFinding] = Field(
        alias="cfl", default_factory=list, description="List of detected conflicts across the matched transaction documents.")
