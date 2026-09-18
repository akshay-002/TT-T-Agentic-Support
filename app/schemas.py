from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(
        ...,
        examples=[
            "SESSION_01"
        ],
    )

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        examples=[
            "Why is my current bill higher than my previous bill?"
        ],
    )

    request_id: str | None = Field(
        default=None,
        examples=[
            "REQ_WEB_001"
        ],
    )


class ChatResponse(BaseModel):
    route: str
    agent: str
    answer: str
    sources: list[str] = Field(
        default_factory=list
    )


class HealthResponse(BaseModel):
    status: str