"""Analytics Village — Episode management routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .facilitator_db import FacilitatorDB
from .models import EpisodeCreate, EpisodeResponse

router = APIRouter(prefix="/api/episodes", tags=["episodes"])


def get_db() -> FacilitatorDB:
    return FacilitatorDB("facilitator.db")


@router.get("")
def list_episodes(status: str = None):
    db = get_db()
    episodes = db.list_episodes(status)
    db.close()
    return episodes


@router.post("")
def create_episode(data: EpisodeCreate):
    db = get_db()
    ep = db.create_episode(data.model_dump())
    db.close()
    return ep


@router.get("/{episode_id}")
def get_episode(episode_id: str):
    db = get_db()
    ep = db.get_episode(episode_id)
    db.close()
    if not ep:
        raise HTTPException(404, f"Episode {episode_id} not found")
    return ep


@router.put("/{episode_id}/status")
def update_status(episode_id: str, status: str):
    db = get_db()
    db.update_episode_status(episode_id, status)
    db.close()
    return {"episode_id": episode_id, "status": status}


@router.delete("/{episode_id}")
def archive_episode(episode_id: str):
    db = get_db()
    db.update_episode_status(episode_id, "archived")
    db.close()
    return {"episode_id": episode_id, "status": "archived"}
