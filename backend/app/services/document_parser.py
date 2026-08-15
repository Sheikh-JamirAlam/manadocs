import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pypdf import PdfReader


def extract_pdf_pages(file_path: Path) -> List[Tuple[int, str]]:
    reader = PdfReader(str(file_path))
    return [
        (page_number, page.extract_text() or "")
        for page_number, page in enumerate(reader.pages, start=1)
    ]


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

    for paragraph in body.findall("w:p", namespace):
        paragraph_text: List[str] = []
        has_page_break = False
        for element in paragraph.iter():
            if element.tag == f"{{{namespace['w']}}}t" and element.text:
                paragraph_text.append(element.text)
            elif element.tag == f"{{{namespace['w']}}}br":
                has_page_break = has_page_break or (
                    element.attrib.get(f"{{{namespace['w']}}}type") == "page"
                )
            elif element.tag == f"{{{namespace['w']}}}lastRenderedPageBreak":
                has_page_break = True

        if paragraph_text:
            current_page.append("".join(paragraph_text))
        if has_page_break:
            pages.append("\n".join(current_page))
            current_page = []

    if current_page or not pages:
        pages.append("\n".join(current_page))
    return list(enumerate(pages, start=1))


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


# Text extraction and chunking for supported document formats.
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
