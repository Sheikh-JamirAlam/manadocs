from __future__ import annotations
from app.graph.workflow import build_extraction_graph, get_database_url
from app.graph.state import AgentState
from app.db.documents import (
    SUPPORTED_DOCUMENT_EXTENSIONS,
    find_document_by_thread_id,
    increment_retry_count,
    register_document,
)

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

load_dotenv()

backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


def get_watch_folder() -> Path:
    configured_folder = os.getenv("WATCH_FOLDER", "/data/documents")
    if not configured_folder:
        raise RuntimeError("WATCH_FOLDER is not configured in .env")

    folder = Path(configured_folder).expanduser().resolve()
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def discover_documents(folder: Path) -> list[Path]:
    documents = []
    for path in folder.iterdir():
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_DOCUMENT_EXTENSIONS:
            continue
        try:
            documents.append(path)
        except OSError:
            continue
    return sorted(documents, key=lambda path: path.name.lower())


async def process_document(graph: Any, path: Path) -> dict[str, Any]:
    print(f"[watcher] Registering/checking {path.name}", flush=True)
    registration = register_document({
        "document_path": str(path),
    })
    print(f"[watcher] Registration result for {path.name}: "
          f"{registration.get('registration_status', 'error')} "
          f"status={registration.get('existing_status')} "
          f"error={registration.get('error')}", flush=True)
    if registration.get("error"):
        return registration

    document_id = registration.get("document_id")
    thread_id = registration.get("thread_id")
    if not document_id or not thread_id:
        return {
            "error": "Document registration did not return document_id and thread_id."
        }

    config = {"configurable": {"thread_id": str(thread_id)}}
    registration_status = registration.get("registration_status")
    existing_status = registration.get("existing_status")

    if registration_status == "duplicate":
        if existing_status in {
            "completed",
            "waiting_for_conflict",
            "waiting_for_rule",
        }:
            return {**registration, "skipped": True}

        if existing_status == "failed":
            max_retries = int(os.getenv("MAX_WORKFLOW_RETRIES", "3"))
            retry_count = registration.get("retry_count", 0)
            if retry_count >= max_retries:
                return {
                    **registration,
                    "skipped": True,
                    "retry_exhausted": True,
                }
            increment_retry_count(str(document_id))

        invocation_input: AgentState | None
        if existing_status == "pending":
            checkpoint = await graph.aget_state(config)
            has_checkpoint = bool(checkpoint and checkpoint.values)
            invocation_input = None if has_checkpoint else {
                "document_id": str(document_id),
                "document_path": str(path),
                "thread_id": str(thread_id),
                "extracted_facts": None,
                "matched_document_ids": [],
                "error": None,
            }
        else:
            invocation_input = None
        print(f"Resuming {path.name} ({existing_status})")
        return await graph.ainvoke(invocation_input, config=config)

    print(f"Processing {path.name}")

    state: AgentState = {
        "document_id": str(document_id),
        "document_path": str(path),
        "thread_id": str(thread_id),
        "extracted_facts": None,
        "matched_document_ids": [],
        "error": None,
    }

    return await graph.ainvoke(state, config=config)


async def watch() -> None:
    folder = get_watch_folder()
    interval = float(os.getenv("WATCH_INTERVAL_SECONDS", "5"))
    print(f"[watcher] Starting folder watcher: {folder}", flush=True)
    print(
        f"[watcher] Supported extensions: "
        f"{', '.join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))}",
        flush=True,
    )

    cached_status: dict[str, tuple[int, int, str]] = {}

    print("[watcher] Connecting to PostgreSQL checkpointer...", flush=True)
    async with AsyncPostgresSaver.from_conn_string(get_database_url()) as checkpointer:
        print("[watcher] Checkpointer connection established.", flush=True)
        await checkpointer.setup()
        print("[watcher] Checkpointer setup complete.", flush=True)
        graph = build_extraction_graph(checkpointer)
        print("[watcher] Extraction graph built. Entering polling loop.", flush=True)

        poll_number = 0
        while True:
            poll_number += 1
            paths = discover_documents(folder)
            print(
                f"[watcher] Poll #{poll_number}: found {len(paths)} supported file(s).",
                flush=True,
            )
            for path in paths:
                try:
                    stat = path.stat()
                    signature = (stat.st_size, stat.st_mtime_ns)
                    cached = cached_status.get(str(path))
                    if cached and cached[:2] == signature and cached[2] in {
                        "completed",
                        "waiting_for_conflict",
                        "waiting_for_rule",
                    }:
                        print(
                            f"[watcher] Skipping cached {path.name} "
                            f"(status={cached[2]}).",
                            flush=True,
                        )
                        continue

                    result = await process_document(graph, path)
                    #! If the decision was committed to the database but the process crashed before the document status was changed back to "processing", this skip can strand the workflow.
                    #! Recovery should eventually inspect pending conflicts/violations and resume an already-resolved interrupt safely.
                    if result.get("skipped"):
                        status = result.get("existing_status")
                        print(
                            f"[watcher] Skipped {path.name} "
                            f"(status={status}).",
                            flush=True,
                        )
                        if status in {
                            "completed",
                            "waiting_for_conflict",
                            "waiting_for_rule",
                        }:
                            cached_status[str(path)] = (*signature, status)
                        continue
                    if result.get("__interrupt__"):
                        print(
                            f"{path.name} paused for human review. "
                            "Use the returned thread_id to resume it."
                        )
                    elif result.get("error"):
                        print(f"{path.name} failed: {result['error']}")
                    else:
                        print(f"Completed {path.name}")

                    thread_id = result.get("thread_id")
                    if thread_id:
                        document = find_document_by_thread_id(str(thread_id))
                        status = (document or {}).get("status")
                        if status in {
                            "completed",
                            "waiting_for_conflict",
                            "waiting_for_rule",
                        }:
                            cached_status[str(path)] = (*signature, status)
                except Exception as exc:
                    print(
                        f"[watcher] Error processing {path.name}: {exc}",
                        file=sys.stderr,
                        flush=True,
                    )

            print(
                f"[watcher] Poll #{poll_number} complete. "
                f"Sleeping {interval:g} second(s).",
                flush=True,
            )
            await asyncio.sleep(interval)


def run_watch_thread() -> None:
    try:
        asyncio.run(watch())
    except KeyboardInterrupt:
        print("[watcher] Watcher stopped.", flush=True)
    except Exception as exc:
        print(
            f"[watcher] Watcher thread stopped unexpectedly: {exc!r}",
            file=sys.stderr,
            flush=True,
        )


if __name__ == "__main__":
    run_watch_thread()
