from contextlib import asynccontextmanager
from pathlib import Path
from collections.abc import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from backend.ai import AIServiceError, explain_dashboard
from backend.analytics import build_dashboard
from backend.database import get_session, initialize_database

STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    yield


app = FastAPI(title="OpsPulse API", version="1.0.0", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dashboard")
def dashboard(
    days: int = 30, session: Session = Depends(get_session)
) -> dict:
    return _dashboard_for_period(days, session)


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)

    @field_validator("question")
    @classmethod
    def strip_and_validate_question(cls, value: str) -> str:
        question = value.strip()
        if len(question) < 3:
            raise ValueError("question must contain at least 3 non-whitespace characters")
        return question


@app.post("/api/ai/summary")
def ai_summary(days: int = 30, session: Session = Depends(get_session)) -> dict[str, str]:
    return _explain(_dashboard_for_period(days, session))


@app.post("/api/ai/ask")
def ai_ask(
    payload: Question, days: int = 30, session: Session = Depends(get_session)
) -> dict[str, str]:
    return _explain(_dashboard_for_period(days, session), payload.question)


def _dashboard_for_period(days: int, session: Session) -> dict:
    if not 7 <= days <= 90:
        raise HTTPException(status_code=400, detail="days must be between 7 and 90")
    return build_dashboard(session, days)


def _explain(dashboard_data: dict, question: str | None = None) -> dict[str, str]:
    try:
        return {"answer": explain_dashboard(dashboard_data, question)}
    except AIServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
