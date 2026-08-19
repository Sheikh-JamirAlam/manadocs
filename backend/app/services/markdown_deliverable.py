import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from app.db.deliverables import get_all_deliverables

load_dotenv()


def get_output_path() -> Path:
    watch_folder = os.getenv("WATCH_FOLDER", "/data/documents")
    if not watch_folder:
        raise RuntimeError("WATCH_FOLDER is not configured in .env")
    output_folder = Path(watch_folder).expanduser().resolve() / "output"
    output_folder.mkdir(parents=True, exist_ok=True)
    return output_folder / "master_deliverable.md"


def rebuild_master_deliverable() -> Path:
    output_path = get_output_path()
    deliverables = get_all_deliverables()

    sections = [
        "# Master Deliverable",
        "",
        f"_Last updated: {datetime.now(timezone.utc).isoformat()}_",
        "",
    ]
    for deliverable in deliverables:
        sections.extend([
            f"## {deliverable['title']}",
            "",
            deliverable["content"].rstrip(),
            "",
            "---",
            "",
        ])

    temporary_path = output_path.with_suffix(".tmp")
    temporary_path.write_text("\n".join(sections), encoding="utf-8")
    temporary_path.replace(output_path)
    return output_path
