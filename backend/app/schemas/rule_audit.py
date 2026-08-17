from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RuleCitation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    quote: str = Field(
        alias="q", description="Exact verbatim excerpt from the source supporting this value.")
    page_number: Optional[int] = Field(
        alias="p", default=None,  description="1-based page number where the quote is located.")
    section_header: Optional[str] = Field(
        alias="sh",  default=None, description="Section/header where this quote appeared (if applicable).")
    character_index: Optional[int] = Field(
        alias="ci", default=None, description="Zero-based character offset of the citation within its line.",)
    line_number: Optional[int] = Field(
        alias="ln",  default=None,   description="One-based line number containing the citation.",)


class RuleViolation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    rule_id: str = Field(alias="rid", description="UUID of the rule.")
    description: str = Field(
        alias="desc", description="Explaination of this rule violation.")
    citation: RuleCitation = Field(
        alias="cit", description="Exact location and quote backing this specific value.")


class RuleAuditResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    violations: List[RuleViolation] = Field(
        alias="vls", default_factory=list, description="List of detected rule violations.")
