"""Analytics Village — Export routes (download DB, CSV, etc.)."""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .facilitator_db import FacilitatorDB

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/village-db/{episode_id}")
def download_village_db(episode_id: str):
    db = FacilitatorDB("facilitator.db")
    ep = db.get_episode(episode_id)
    db.close()
    if not ep or not ep.get("village_db_path"):
        raise HTTPException(404, "Episode or DB not found")
    path = ep["village_db_path"]
    if not os.path.exists(path):
        raise HTTPException(404, f"DB file not found at {path}")
    return FileResponse(path, filename=f"{episode_id}_village.db",
                        media_type="application/x-sqlite3")


@router.get("/brief/{episode_id}")
def download_brief(episode_id: str):
    output_dir = os.path.join("output", episode_id)
    path = os.path.join(output_dir, "brief.md")
    if not os.path.exists(path):
        raise HTTPException(404, "Brief not found")
    return FileResponse(path, filename="brief.md", media_type="text/markdown")


@router.get("/schema/{episode_id}")
def download_schema(episode_id: str):
    output_dir = os.path.join("output", episode_id)
    path = os.path.join(output_dir, "schema.json")
    if not os.path.exists(path):
        raise HTTPException(404, "Schema not found")
    return FileResponse(path, filename="schema.json", media_type="application/json")
