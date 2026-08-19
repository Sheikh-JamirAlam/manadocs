from copy import deepcopy
from typing import Any, Dict, Iterable, List, Mapping


def get_enforced_findings(
    rule_violations: Iterable[Mapping[str, Any]] | None,
    conflicts: Iterable[Mapping[str, Any]] | None,
) -> Dict[str, List[Dict[str, Any]]]:
    return {
        "rule_violations": [
            dict(item)
            for item in (rule_violations or [])
            if item.get("resolution") == "enforce_rule"
        ],
        "conflicts": [
            dict(item)
            for item in (conflicts or [])
            if item.get("resolution") == "enforce_conflict"
        ],
    }


def remove_enforced_conflict_facts(
    extracted_facts: Mapping[str, Any] | None,
    enforced_conflicts: Iterable[Mapping[str, Any]] | None,
    current_document_id: str,
) -> Dict[str, Any]:
    filtered = deepcopy(dict(extracted_facts or {}))
    facts = filtered.get("facts") or []
    if not current_document_id or not enforced_conflicts:
        return filtered

    excluded: set[tuple[str, str]] = set()
    for conflict in enforced_conflicts:
        for source in conflict.get("conflicting_sources") or []:
            if str(source.get("document_id")) != str(current_document_id):
                continue
            citation = source.get("citation") or {}
            quote = citation.get("quote")
            if quote is not None:
                excluded.add((str(conflict.get("field_name")), str(quote)))

    filtered["facts"] = [
        fact for fact in facts
        if (str(fact.get("field_name")), str((fact.get("citation") or {}).get("quote")))
        not in excluded
    ]
    return filtered
