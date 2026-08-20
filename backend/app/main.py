import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api_conflicts import router as conflicts_router
from app.api_rules import router as rules_router
from scripts.watch_folder import run_watch_thread
from app.services.workflow_queue import start_worker, stop_worker
from app.api_workflow import router as workflow_router
from app.api_documents import router as documents_router
from app.api_deliverables import router as deliverables_router
from app.mcp_server import mcp
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(_: FastAPI):
    start_worker()
    watcher_thread = threading.Thread(
        target=run_watch_thread,
        name="document-watcher",
        daemon=True,
    )
    watcher_thread.start()
    try:
        yield
    finally:
        await stop_worker()
        print("[watcher] FastAPI shutdown requested.", flush=True)


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(documents_router)
app.include_router(deliverables_router)
app.include_router(conflicts_router)
app.include_router(rules_router)
app.include_router(workflow_router)
app.mount("/mcp", mcp.streamable_http_app(streamable_http_path="/"))


@app.get("/")
async def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
