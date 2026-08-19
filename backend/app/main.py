from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.providers import SimulatedChatProvider
from app.settings import settings


class HealthResponse(BaseModel):
    status: str = "ok"
    aws_region: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str | None = None
    provider: str


app = FastAPI(title="AI Assistant Backend", version="0.1.0")
chat_provider = SimulatedChatProvider()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_origin,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", aws_region=settings.aws_region)


@app.post("/api/v1/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    try:
        result = chat_provider.generate_reply(payload.message)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Provider error") from exc

    return ChatResponse(
        reply=result.reply,
        session_id=payload.session_id,
        provider=result.provider,
    )
