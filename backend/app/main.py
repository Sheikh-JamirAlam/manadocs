from fastapi import FastAPI
from app.api_conflicts import router as conflicts_router

app = FastAPI()
app.include_router(conflicts_router)


@app.get("/")
async def root():
    return {"message": "Hello World"}
