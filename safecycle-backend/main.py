"""SafeCycle backend — FastAPI application.

SafeCycle is a contraception guidance app. This service exposes:
  - GET  /health           : liveness check
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

# Default to the latest, most capable Claude model. Override via env if needed.
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")

app = FastAPI(
    title="SafeCycle API",
    description="Contraception guidance, made clear.",
    version="0.1.0",
)


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
@app.get("/health")
def health() -> dict:
    """Liveness probe. Returns 200 with basic service info."""
    return {"status": "ok", "service": "safecycle-backend", "version": app.version}
