import re
from typing import Any, Dict, List, Tuple

from app.schemas.extraction import DocumentExtractionResult


PageText = Tuple[int, str]


def whitespace_match(source: str, quote: str) -> int:
    parts = [re.escape(part)
             for part in re.split(r"\s+", quote.strip()) if part]
    if not parts:
        return -1
    match = re.search(r"\s+".join(parts), source)
    return match.start() if match else -1


def calculate_exact_citation(
    extraction_result: DocumentExtractionResult,
    pages: List[PageText],
) -> Dict[str, Any]:
    page_by_number = {
        page_number: page_text for page_number, page_text in pages}
    payload = extraction_result.model_dump(mode="json")

    for fact in payload.get("facts", []):
        citation = fact.get("citation")
        if not citation or not citation.get("quote"):
            continue

        target_page_num = citation.get("page_number")
        quote = citation["quote"]

        matched_page_text = page_by_number.get(target_page_num)
        index = matched_page_text.find(quote) if matched_page_text else -1

        if index < 0 and matched_page_text:
            index = whitespace_match(matched_page_text, quote)

        if index < 0:
            for p_num, p_text in pages:
                if p_num == target_page_num:
                    continue
                idx = p_text.find(quote)
                if idx < 0:
                    idx = whitespace_match(p_text, quote)
                if idx >= 0:
                    index = idx
                    matched_page_text = p_text
                    citation["page_number"] = p_num
                    break

        if index >= 0 and matched_page_text is not None:
            text_before = matched_page_text[:index]

            last_newline_idx = text_before.rfind("\n")
            if last_newline_idx == -1:
                citation["character_index"] = index
            else:
                citation["character_index"] = index - (last_newline_idx + 1)

            normalized_text_before = text_before.replace(
                "\r\n", "\n").replace("\r", "\n")
            citation["line_number"] = normalized_text_before.count("\n") + 1

    return payload
