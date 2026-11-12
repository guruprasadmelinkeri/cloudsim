"""
CloudArchSim — FastAPI Application Entry Point
Member 2 responsibility: FastAPI setup & backend/frontend communication.

Run with:
    uvicorn main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from api.routes import router
from api.intelligence import router as intelligence_router

# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="CloudArchSim API",
    description=(
        "Cloud Architecture Simulation & Evaluation Platform. "
        "Select a predefined architecture and scenario to run a SimPy simulation."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# Allow the Next.js frontend (localhost:3000) to call the API.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────────────────────

app.include_router(router, prefix="/api")
app.include_router(intelligence_router, prefix="/api/intelligence", tags=["Architecture Intelligence"])


@app.get("/")
def root():
    return {
        "name": "CloudArchSim API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": [
            "GET /api/architectures",
            "GET /api/scenarios",
            "POST /api/simulate",
            "POST /api/compare",
            "GET /api/health",
        ],
    }
