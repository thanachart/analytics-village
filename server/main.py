"""
Analytics Village — Facilitator App Server.
FastAPI backend serving the React SPA + API endpoints.
"""
from __future__ import annotations

import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routes_episodes import router as episodes_router
from .routes_simulation import router as simulation_router
from .routes_submissions import router as submissions_router
from .routes_export import router as export_router
from .routes_data import router as data_router

app = FastAPI(
    title="Analytics Village Facilitator",
    version="0.1.0",
    description="Instructor dashboard for Analytics Village simulation",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(episodes_router)
app.include_router(simulation_router)
app.include_router(submissions_router)
app.include_router(export_router)
app.include_router(data_router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "analytics-village-facilitator"}


# Mount React SPA static files (after all API routes)
frontend_dist = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend", "dist"
)
if os.path.isdir(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="spa")


def run():
    """Entry point for `village-server` console script."""
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    run()
