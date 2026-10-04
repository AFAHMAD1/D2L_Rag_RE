import os
import sys

import groq
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.genai import errors as google_errors
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from pipeline import answer_question

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
FRONTEND_PATH = os.path.join(FRONTEND_DIR, "index.html")

app = FastAPI(title="D2L RAG API")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


class AskRequest(BaseModel):
    question: str
    k: int = Field(default=4, ge=1, le=10)


class Source(BaseModel):
    chapter: str
    page: int
    distance: float
    text: str


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_PATH)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    try:
        result = answer_question(question, request.k)
    except (google_errors.APIError, groq.APIError) as e:
        raise HTTPException(
            status_code=503,
            detail=f"The language model is unavailable right now, please try again later. ({type(e).__name__})",
        )

    sources = [
        Source(
            chapter=s["chapter"],
            page=s["page"],
            distance=round(s["distance"], 3),
            text=s["text"],
        )
        for s in result["sources"]
    ]
    return AskResponse(answer=result["answer"], sources=sources)
