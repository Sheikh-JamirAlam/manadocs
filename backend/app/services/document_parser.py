import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pdfplumber


# Convert docx to markdown to preserve tables and formatting
def docx_table_to_markdown(table_element, namespace) -> str:
    rows_text = []
    rows = table_element.findall("w:tr", namespace)
    for i, row in enumerate(rows):
        cells = []
        for cell in row.findall("w:tc", namespace):
            cell_text = "".join(
                t.text or "" for t in cell.findall(".//w:t", namespace)
            ).strip().replace("\n", " ")
            cells.append(cell_text if cell_text else " ")
        rows_text.append("| " + " | ".join(cells) + " |")
        if i == 0:
            rows_text.append("| " + " | ".join(["---"] * len(cells)) + " |")
    return "\n".join(rows_text)


def extract_docx_pages(file_path: Path) -> List[Tuple[int, str]]:
    namespace = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    pages: List[str] = []
    current_page: List[str] = []

    with zipfile.ZipFile(file_path) as archive:
        document_xml = archive.read("word/document.xml")

    root = ET.fromstring(document_xml)
    body = root.find("w:body", namespace)
    if body is None:
        return [(1, "")]

    for element in body:
        tag = element.tag

        if tag == f"{{{namespace['w']}}}p":
            paragraph_text: List[str] = []
            has_page_break = False
            for sub in element.iter():
                if sub.tag == f"{{{namespace['w']}}}t" and sub.text:
                    paragraph_text.append(sub.text)
                elif sub.tag == f"{{{namespace['w']}}}br":
                    has_page_break = has_page_break or (
                        sub.attrib.get(f"{{{namespace['w']}}}type") == "page"
                    )
                elif sub.tag == f"{{{namespace['w']}}}lastRenderedPageBreak":
                    has_page_break = True

            if paragraph_text:
                current_page.append("".join(paragraph_text))
            if has_page_break:
                pages.append("\n".join(current_page))
                current_page = []

        elif tag == f"{{{namespace['w']}}}tbl":
            md_table = docx_table_to_markdown(element, namespace)
            if md_table.strip():
                current_page.append("\n" + md_table + "\n")

    if current_page or not pages:
        pages.append("\n".join(current_page))
    return list(enumerate(pages, start=1))


# Convert pdf to markdown to preserve tables and formatting
def _pdf_table_to_markdown(table: List[List[Optional[str]]]) -> str:
    rows_text = []
    for i, row in enumerate(table):
        cells = [(c or "").strip().replace("\n", " ") for c in row]
        rows_text.append("| " + " | ".join(cells) + " |")
        if i == 0:
            rows_text.append("| " + " | ".join(["---"] * len(cells)) + " |")
    return "\n".join(rows_text)


def extract_pdf_pages(file_path: Path) -> List[Tuple[int, str]]:
    pages: List[Tuple[int, str]] = []

    with pdfplumber.open(str(file_path)) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            tables = page.find_tables()

            if not tables:
                pages.append((page_number, page.extract_text() or ""))
                continue

            table_bboxes = [t.bbox for t in tables]

            def _outside_tables(obj):
                for x0, top, x1, bottom in table_bboxes:
                    if (
                        obj["x0"] >= x0 - 1
                        and obj["x1"] <= x1 + 1
                        and obj["top"] >= top - 1
                        and obj["bottom"] <= bottom + 1
                    ):
                        return False
                return True

            filtered_page = page.filter(_outside_tables)
            text_blocks: List[Tuple[float, str]] = []

            for line in (filtered_page.extract_text() or "").split("\n"):
                if line.strip():
                    text_blocks.append((0.0, line))

            words = filtered_page.extract_words()
            lines_by_top: dict = {}
            for w in words:
                key = round(w["top"])
                lines_by_top.setdefault(key, []).append(w["text"])

            blocks: List[Tuple[float, str]] = [
                (top, " ".join(words_))
                for top, words_ in lines_by_top.items()
            ]

            for table in tables:
                md = _pdf_table_to_markdown(table.extract())
                if md.strip():
                    blocks.append((table.bbox[1], "\n" + md + "\n"))

            blocks.sort(key=lambda b: b[0])
            pages.append((page_number, "\n".join(b[1] for b in blocks)))

    return pages


def extract_txt_pages(file_path: Path) -> List[Tuple[int, str]]:
    return [(1, file_path.read_text(encoding="utf-8", errors="replace"))]


def extract_pages(file_path: Path) -> List[Tuple[int, str]]:
    if file_path.suffix.lower() == ".pdf":
        return extract_pdf_pages(file_path)
    if file_path.suffix.lower() == ".docx":
        return extract_docx_pages(file_path)
    if file_path.suffix.lower() == ".txt":
        return extract_txt_pages(file_path)
    raise ValueError(
        f"Unsupported document type: {file_path.suffix or '<none>'}")


# Text extraction and chunking for supported document formats
def parse_document(
    file_path: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[Dict[str, Any]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap must be >= 0 and smaller than chunk_size")

    chunks: List[Dict[str, Any]] = []
    step = chunk_size - chunk_overlap
    for page_number, page_text in extract_pages(Path(file_path)):
        normalized_text = page_text.strip()
        for start in range(0, len(normalized_text), step):
            chunk_text = normalized_text[start:start + chunk_size]
            if not chunk_text:
                break
            chunks.append(
                {
                    "chunk_index": len(chunks),
                    "text": chunk_text,
                    "page_start": page_number,
                    "page_end": page_number,
                }
            )
            if start + chunk_size >= len(normalized_text):
                break
    return chunks


# Add source markers to the chunks
def format_chunks_for_prompt(chunks: List[Dict[str, Any]]) -> str:
    return "\n\n".join(
        "\n".join(
            [
                f"--- [CHUNK {chunk['chunk_index']}] [PAGE {chunk['page_start']}] ---",
                chunk["text"],
                f"--- [END CHUNK {chunk['chunk_index']}] ---",
            ]
        )
        for chunk in chunks
    )
