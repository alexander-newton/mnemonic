"""Mnemonic FastAPI app entry point."""

from fastapi import FastAPI

from mnemonic.api.routes import api_router

app = FastAPI(title="Mnemonic", version="0.2.0")
app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok"}
