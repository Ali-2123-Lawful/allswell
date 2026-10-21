"""
Allswell backend
================

FastAPI app that:
  * holds the home-activity event stream (fed by the scenario simulator)
  * answers caregiver questions through backend/care.py, which runs the
    home_rhythm engine and phrases results with the Bedrock digest layer
  * serves the same tools over MCP (Streamable HTTP) at /mcp
  * serves the caregiver dashboard

Run:  uvicorn backend.main:app   (from the repo root)
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import assistant, care, seed
from .mcp_server import server as mcp_server

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"


def _load_dotenv(path: Path) -> None:
    """Minimal .env reader (no extra dependency). Real env vars take precedence."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv(ROOT / ".env")

mcp_app = mcp_server.streamable_http_app()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with mcp_server.session_manager.run():
        yield


app = FastAPI(title="Allswell", version="0.2.0", lifespan=lifespan)


@app.get("/api/state")
def api_state():
    """The one endpoint the dashboard polls: everything needed to render."""
    return {
        **care.snapshot(),
        "scenarios": seed.SCENARIOS,
        "generated_at": datetime.now().isoformat(),
    }


@app.post("/api/scenario/{scenario}")
def api_scenario(scenario: str):
    if scenario not in seed.SCENARIOS:
        return JSONResponse({"error": "unknown scenario"}, status_code=400)
    care.load_scenario(scenario)
    return {"ok": True, "scenario": scenario}


@app.post("/api/check-in")
def api_check_in():
    """Mock the one-tap check-in. In production this would place a call; here we
    just record that the caregiver reached out, no video ever involved."""
    return care.check_in()


@app.post("/api/ask")
async def api_ask(request: Request):
    """Simulated Alexa+: answer a caregiver's question by calling our own MCP
    server over Streamable HTTP, exactly as a voice assistant would."""
    body = await request.json()
    question = (body.get("question") or "").strip()
    if not question:
        return JSONResponse({"error": "empty question"}, status_code=400)
    try:
        return await assistant.ask(question, mcp_url=f"{request.base_url}mcp")
    except Exception:
        return {"reply": "Sorry, I couldn't reach Allswell just now. Please try again in a moment.", "tool": None}


# ------- static frontend ------- #
if FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")


@app.get("/")
def index():
    idx = FRONTEND / "index.html"
    if idx.exists():
        return FileResponse(str(idx))
    return JSONResponse({"message": "Allswell API running. Frontend not found."})


@app.get("/ask")
def ask_page():
    return FileResponse(str(FRONTEND / "ask.html"))


# MCP endpoint (/mcp). Mounted last so the routes above take precedence.
app.mount("/", mcp_app)
