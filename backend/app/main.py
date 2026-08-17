from fastapi import FastAPI
from app.api_conflicts import router as conflicts_router
from app.api_rules import router as rules_router

app = FastAPI()
app.include_router(conflicts_router)
app.include_router(rules_router)


@app.get("/")
async def root():
    return {"message": "Hello World"}
