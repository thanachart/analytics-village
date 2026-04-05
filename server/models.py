"""Analytics Village — Pydantic request/response models."""
from __future__ import annotations

from pydantic import BaseModel
from typing import Any


class EpisodeCreate(BaseModel):
    title: str
    episode_number: int = 1
    primary_business: str = "supermarket"
    tier: int = 1
    challenge_type: str = "reporting"
    num_households: int = 150
    history_days: int = 90
    live_days: int = 30
    seed: int = 42
    use_llm: bool = False
    notes: str | None = None


class EpisodeResponse(BaseModel):
    episode_id: str
    title: str
    episode_number: int
    primary_business: str
    tier: int
    challenge_type: str
    status: str
    created_at: str
    notes: str | None = None
    config: dict | None = None
    village_db_path: str | None = None


class SimulationRunRequest(BaseModel):
    episode_id: str = "ep01"
    num_households: int = 150
    history_days: int = 90
    live_days: int = 30
    seed: int = 42
    use_llm: bool = False
    primary_business: str = "supermarket"


class SimulationStatus(BaseModel):
    status: str  # idle, generating, running, completed, error
    current_day: int | None = None
    total_days: int | None = None
    progress_pct: float = 0.0
    message: str = ""
    elapsed_seconds: float = 0.0


class SubmissionCreate(BaseModel):
    episode_id: str
    student_id: str
    team_id: str | None = None
    decision_json: dict


class ScoreOverride(BaseModel):
    criterion: str
    score: float
    feedback: str | None = None


class KPIResponse(BaseModel):
    total_revenue: float = 0.0
    total_transactions: int = 0
    active_households: int = 0
    avg_basket_thb: float = 0.0
    churn_rate: float = 0.0
    stockout_rate: float = 0.0
    days_simulated: int = 0


class ScoreboardEntry(BaseModel):
    rank: int
    student_id: str
    display_name: str
    final_score: float
    score_breakdown: dict | None = None
    outcome_summary: str | None = None
