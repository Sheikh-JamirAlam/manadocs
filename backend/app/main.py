import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api_conflicts import router as conflicts_router
from app.api_rules import router as rules_router
from scripts.watch_folder import run_watch_thread
from app.services.workflow_queue import start_worker, stop_worker
from app.api_workflow import router as workflow_router

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
app.include_router(conflicts_router)
app.include_router(rules_router)
app.include_router(workflow_router)


@app.get("/")
async def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
