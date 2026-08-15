from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


class Citation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    quote: str = Field(
        alias="q", description="Exact verbatim excerpt from the source supporting this value.")
    page_number: Optional[int] = Field(
        alias="p", default=None, description="1-based page number where the quote is located.")
    section_header: Optional[str] = Field(
        alias="sh", default=None, description="Section/header where this quote appeared (if applicable).",)


class ExtractedFact(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    field_name: str = Field(
        alias="f", description="Standardized name of the attribute (e.g., 'hourly_rate', 'vendor_name', 'payment_terms', 'total_amount').")
    value: Union[str, int, float, bool] = Field(
        alias="v", description="Extracted value.")
    unit: Optional[str] = Field(
        alias="u", default=None, description="Unit if applicable (e.g., 'USD', 'days').")
    category: str = Field(
        alias="c", default="general", description="Category classification (e.g., 'financial', 'legal', 'operational', 'identity').",)
    citation: Citation = Field(
        alias="cit", description="Exact location and quote backing this specific fact.")


class DocumentExtractionResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    document_type: Literal["contract", "amendment", "invoice", "unknown"] = Field(
        alias="dt", description="Classification of the document.")
    vendor_name: Optional[str] = Field(
        alias="vn", default=None, description="Name of the external vendor/party involved, if identifiable.",)
    summary: str = Field(
        alias="sum", description="2-3 sentence overview of the document.")
    facts: List[ExtractedFact] = Field(
        alias="fac", description="List of all key-value facts and citations extracted from the text.")
