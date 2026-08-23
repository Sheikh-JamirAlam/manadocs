from __future__ import annotations

from collections import Counter
import re

from app.schemas.audit_conflicts import ConflictAuditResult
from app.schemas.deliverable import Deliverable
from app.schemas.extraction import DocumentExtractionResult
from app.schemas.match_documents import TransactionMatchResult
from app.schemas.rule_audit import RuleAuditResult


class PromptAwareProvider:
    def __init__(self, extraction_by_vendor, deliverable_by_vendor=None):
        self.extraction_by_vendor = extraction_by_vendor
        self.deliverable_by_vendor = deliverable_by_vendor or {}
        self.calls = Counter()
        self.prompts = []

    def structured(self, _model, schema):
        provider = self

        class Model:
            def invoke(self, prompt):
                provider.prompts.append(prompt)
                vendor = next(
                    (name for name in provider.extraction_by_vendor
                     if re.search(rf"(?<!\w){re.escape(name)}(?!\w)", prompt)),
                    None,
                )
                provider.calls[(schema, vendor)] += 1
                if schema is DocumentExtractionResult:
                    return provider.extraction_by_vendor[vendor]
                if schema is Deliverable:
                    return provider.deliverable_by_vendor.get(
                        vendor, Deliverable.model_validate(
                            {"t": vendor or "Register", "c": vendor or "No vendor"})
                    )
                if schema is TransactionMatchResult:
                    return TransactionMatchResult(matched_document_ids=[], reasoning="none")
                if schema is ConflictAuditResult:
                    return ConflictAuditResult()
                if schema is RuleAuditResult:
                    return RuleAuditResult()
                raise AssertionError(f"Unexpected schema: {schema}")

        return Model()
