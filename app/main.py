from __future__ import annotations

import uuid

from fastapi import (
    FastAPI,
    HTTPException,
)

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from app.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
)

from packages.crew.support_flow import (
    run_support_flow,
)


app = FastAPI(
    title="TT&T AI Customer Support API",
    description=(
        "Agentic telecom support API using CrewAI, "
        "MCP, RAG, PostgreSQL, pgvector, and Ollama."
    ),
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=[
        "*"
    ],
    allow_headers=[
        "*"
    ],
)


# ============================================================
# HEALTH
# ============================================================

@app.get(
    "/health",
    response_model=HealthResponse,
)
async def health() -> HealthResponse:

    return HealthResponse(
        status="ok"
    )


# ============================================================
# CHAT
# ============================================================

@app.post(
    "/chat",
    response_model=ChatResponse,
)
async def chat(
    request: ChatRequest,
) -> ChatResponse:

    try:

        request_id = (
            request.request_id
            or str(uuid.uuid4())
        )

        result = await run_support_flow(
            question=request.message,
            session_id=request.session_id,
            request_id=request_id,
        )

        return ChatResponse(
            route=result["route"],
            agent=result["agent"],
            answer=result["answer"],
            sources=result.get(
                "sources",
                [],
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except PermissionError:

        raise HTTPException(
            status_code=403,
            detail="Access denied.",
        )

    except Exception as exc:

        print(
            f"Unhandled API error: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "The TT&T support service encountered "
                "an internal error."
            ),
        )