"""FastAPI application entry point for Mnemonic."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from mnemonic.api.routes import auth, cards, decks

app = FastAPI(
    title="Mnemonic API",
    description="Adaptive spaced repetition system with LLM-powered question variations",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative frontend port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(decks.router)
app.include_router(cards.router)


@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "healthy"}, status_code=200)


@app.get("/")
async def root() -> JSONResponse:
    """Root endpoint."""
    return JSONResponse(
        {"message": "Mnemonic API", "version": "0.1.0"},
        status_code=200,
    )
