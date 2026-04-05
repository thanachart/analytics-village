"""Analytics Village — Submission and scoring routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .facilitator_db import FacilitatorDB
from .models import SubmissionCreate, ScoreOverride

router = APIRouter(prefix="/api/submissions", tags=["submissions"])


@router.get("")
def list_submissions(episode_id: str = None):
    db = FacilitatorDB("facilitator.db")
    subs = db.list_submissions(episode_id)
    db.close()
    return subs


@router.post("")
def create_submission(data: SubmissionCreate):
    db = FacilitatorDB("facilitator.db")
    result = db.create_submission(data.model_dump())
    db.close()
    return result


@router.get("/{submission_id}")
def get_submission(submission_id: str):
    db = FacilitatorDB("facilitator.db")
    sub = db.get_submission(submission_id)
    db.close()
    if not sub:
        raise HTTPException(404, "Submission not found")
    return sub


@router.post("/{submission_id}/score")
def score_submission(submission_id: str, score: ScoreOverride):
    db = FacilitatorDB("facilitator.db")
    sub = db.get_submission(submission_id)
    if not sub:
        db.close()
        raise HTTPException(404, "Submission not found")
    db.update_submission_score(
        submission_id,
        manual_score=score.score,
        feedback=score.feedback,
    )
    db.close()
    return {"status": "scored", "score": score.score}


@router.get("/scoreboard/{episode_id}")
def get_scoreboard(episode_id: str):
    db = FacilitatorDB("facilitator.db")
    subs = db.list_submissions(episode_id)
    db.close()
    # Sort by score
    scored = [s for s in subs if s.get("final_score") is not None]
    scored.sort(key=lambda s: s["final_score"], reverse=True)
    board = []
    for i, s in enumerate(scored):
        board.append({
            "rank": i + 1,
            "student_id": s["student_id"],
            "display_name": s.get("student_id", "Anonymous"),
            "final_score": s["final_score"],
            "submitted_at": s["submitted_at"],
        })
    return board
