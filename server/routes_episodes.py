"""Analytics Village — Episode management routes with GitHub integration."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .facilitator_db import FacilitatorDB
from .models import EpisodeCreate

router = APIRouter(prefix="/api/episodes", tags=["episodes"])

REPO_URL = "https://github.com/thanachart/analytics-village"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_db() -> FacilitatorDB:
    return FacilitatorDB("facilitator.db")


def _git(cmd: str, cwd: str = None) -> dict:
    """Run a git command and return result."""
    result = subprocess.run(
        f"git {cmd}", shell=True, capture_output=True, text=True,
        cwd=cwd or PROJECT_ROOT,
    )
    return {
        "ok": result.returncode == 0,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


# ── CRUD ─────────────────────────────────────────────────────


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

    # Enrich with file info
    ep["files"] = _get_episode_files(episode_id)
    ep["git_status"] = _get_git_status(episode_id)
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


# ── GitHub Actions ───────────────────────────────────────────


class PublishRequest(BaseModel):
    commit_message: str | None = None


@router.post("/{episode_id}/push")
def push_episode(episode_id: str, req: PublishRequest = None):
    """
    Push episode data files to GitHub.
    Stages data/, episodes/, notebooks/, submissions/ for this episode, commits, and pushes.
    """
    db = get_db()
    ep = db.get_episode(episode_id)
    db.close()
    if not ep:
        raise HTTPException(404, f"Episode {episode_id} not found")

    msg = (req.commit_message if req and req.commit_message
           else f"Publish {episode_id}: {ep.get('title', episode_id)}")

    # Stage only student-facing files (no facilitator/simulation/server code)
    student_files = [
        f"episodes/{episode_id}/",
        f"notebooks/",
        f"submissions/{episode_id}/",
        "student/",
        "README.md",
        ".gitignore",
        "requirements.txt",
    ]
    for f in student_files:
        path = os.path.join(PROJECT_ROOT, f)
        if os.path.exists(path):
            _git(f'add "{f}"')

    # Commit
    result = _git(f'commit -m "{msg}"')
    if not result["ok"] and "nothing to commit" in result["stdout"]:
        return {"status": "no_changes", "message": "Nothing new to commit"}

    # Push
    push = _git("push origin main")
    if not push["ok"]:
        # Try setting upstream
        _git("push -u origin main")
        push = _git("push origin main")

    # Update episode status
    db = get_db()
    db.update_episode_status(episode_id, "active")
    db.execute(
        "UPDATE episodes SET github_release_url = ? WHERE episode_id = ?",
        (f"{REPO_URL}/tree/main/data/{episode_id}", episode_id)
    )
    db.close()

    return {
        "status": "pushed" if push["ok"] else "push_failed",
        "commit": result["stdout"][:200],
        "push": push["stdout"][:200] or push["stderr"][:200],
        "url": f"{REPO_URL}/tree/main/data/{episode_id}",
    }


@router.post("/{episode_id}/update")
def update_episode_push(episode_id: str, req: PublishRequest = None):
    """
    Update (re-push) episode files to GitHub.
    Same as push but with an update commit message.
    """
    db = get_db()
    ep = db.get_episode(episode_id)
    db.close()
    if not ep:
        raise HTTPException(404, f"Episode {episode_id} not found")

    msg = (req.commit_message if req and req.commit_message
           else f"Update {episode_id}: {ep.get('title', episode_id)} data")

    # Stage only student-facing files
    _git(f"add episodes/{episode_id}/ notebooks/ submissions/{episode_id}/ student/ README.md")

    result = _git(f'commit -m "{msg}"')
    if not result["ok"] and "nothing to commit" in result["stdout"]:
        return {"status": "no_changes", "message": "Nothing new to commit"}

    push = _git("push origin main")

    return {
        "status": "updated" if push["ok"] else "push_failed",
        "commit": result["stdout"][:200],
        "push": push["stdout"][:200] or push["stderr"][:200],
    }


@router.post("/{episode_id}/lock")
def lock_episode(episode_id: str):
    """
    Lock an episode — sets status to 'closed', preventing further changes.
    Pushes a final commit marking the episode as locked.
    """
    db = get_db()
    ep = db.get_episode(episode_id)
    if not ep:
        db.close()
        raise HTTPException(404, f"Episode {episode_id} not found")

    db.update_episode_status(episode_id, "closed")
    db.close()

    # Commit the lock state
    _git(f"add -A")
    _git(f'commit -m "Lock {episode_id}: submissions closed"')
    push = _git("push origin main")

    return {
        "status": "locked",
        "episode_id": episode_id,
        "pushed": push["ok"],
    }


@router.post("/{episode_id}/unlock")
def unlock_episode(episode_id: str):
    """Unlock a closed episode back to active."""
    db = get_db()
    db.update_episode_status(episode_id, "active")
    db.close()
    return {"status": "unlocked", "episode_id": episode_id}


# ── Helpers ──────────────────────────────────────────────────


def _get_episode_files(episode_id: str) -> list[dict]:
    """List files for an episode with sizes."""
    files = []
    dirs = [
        f"data/{episode_id}",
        f"episodes/{episode_id}",
    ]
    for d in dirs:
        path = os.path.join(PROJECT_ROOT, d)
        if os.path.isdir(path):
            for name in os.listdir(path):
                fp = os.path.join(path, name)
                if os.path.isfile(fp):
                    size = os.path.getsize(fp)
                    files.append({
                        "name": name,
                        "path": f"{d}/{name}",
                        "size_kb": round(size / 1024, 1),
                        "type": name.split(".")[-1] if "." in name else "unknown",
                    })

    # Check notebook
    nb_path = os.path.join(PROJECT_ROOT, "notebooks")
    if os.path.isdir(nb_path):
        for name in os.listdir(nb_path):
            if episode_id in name:
                fp = os.path.join(nb_path, name)
                files.append({
                    "name": name,
                    "path": f"notebooks/{name}",
                    "size_kb": round(os.path.getsize(fp) / 1024, 1),
                    "type": "ipynb",
                })

    # Check submissions
    sub_path = os.path.join(PROJECT_ROOT, "submissions", episode_id)
    if os.path.isdir(sub_path):
        sub_count = len([f for f in os.listdir(sub_path) if f.endswith(".json")])
        files.append({
            "name": f"{sub_count} submissions",
            "path": f"submissions/{episode_id}/",
            "size_kb": 0,
            "type": "folder",
        })

    return files


def _get_git_status(episode_id: str) -> dict:
    """Get git status for episode files."""
    status = _git("status --porcelain")
    log = _git("log --oneline -3")
    remote = _git("remote get-url origin")

    # Check if episode files have uncommitted changes
    changes = []
    if status["ok"]:
        for line in status["stdout"].split("\n"):
            line = line.strip()
            if line and episode_id in line:
                changes.append(line)

    return {
        "has_changes": len(changes) > 0,
        "changes": changes,
        "recent_commits": log["stdout"].split("\n") if log["ok"] else [],
        "remote": remote["stdout"] if remote["ok"] else None,
    }
