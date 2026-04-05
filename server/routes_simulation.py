"""Analytics Village — Simulation control routes."""
from __future__ import annotations

import os
import threading
import time

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from .models import SimulationRunRequest, SimulationStatus, KPIResponse
from .facilitator_db import FacilitatorDB

router = APIRouter(prefix="/api/simulation", tags=["simulation"])

# Global simulation state
_sim_state = {
    "status": "idle",
    "current_day": None,
    "total_days": None,
    "progress_pct": 0.0,
    "message": "",
    "elapsed": 0.0,
    "thread": None,
}


def _run_simulation(req: SimulationRunRequest):
    """Background thread for running simulation."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from simulation.world import SimConfig
    from simulation.history_runner import run_history

    _sim_state["status"] = "generating"
    _sim_state["message"] = "Starting..."
    t0 = time.time()

    config = SimConfig(
        num_households=req.num_households,
        history_days=req.history_days,
        live_days=req.live_days if req.use_llm else 0,
        random_seed=req.seed,
        episode_id=req.episode_id,
        primary_business=req.primary_business,
    )

    output_dir = os.path.join("output", req.episode_id)
    os.makedirs(output_dir, exist_ok=True)
    db_path = os.path.join(output_dir, f"{req.episode_id}_village.db")

    if os.path.exists(db_path):
        os.remove(db_path)

    def progress(current, total, msg):
        _sim_state["current_day"] = current
        _sim_state["total_days"] = total
        _sim_state["progress_pct"] = (current / total * 100) if total > 0 else 0
        _sim_state["message"] = msg
        _sim_state["elapsed"] = time.time() - t0

    try:
        run_history(db_path, config, progress_callback=progress)

        # Export
        from simulation.exporter import EpisodeExporter
        exporter = EpisodeExporter(db_path, config)
        exporter.export_all(output_dir)

        # Update facilitator DB
        fdb = FacilitatorDB("facilitator.db")
        fdb.create_episode({
            "episode_id": req.episode_id,
            "title": f"Episode {req.episode_id.upper()}",
            "episode_number": int(req.episode_id.replace("ep", "")) if req.episode_id.startswith("ep") else 1,
            "primary_business": req.primary_business,
            "village_db_path": db_path,
            "num_households": req.num_households,
            "history_days": req.history_days,
            "live_days": req.live_days,
            "seed": req.seed,
        })
        fdb.update_episode_status(req.episode_id, "draft")
        fdb.close()

        _sim_state["status"] = "completed"
        _sim_state["progress_pct"] = 100.0
        _sim_state["message"] = f"Done in {time.time() - t0:.1f}s"

    except Exception as e:
        _sim_state["status"] = "error"
        _sim_state["message"] = str(e)


@router.post("/run")
def start_simulation(req: SimulationRunRequest):
    if _sim_state["status"] == "generating":
        return {"error": "Simulation already running"}

    _sim_state["status"] = "generating"
    _sim_state["progress_pct"] = 0.0
    _sim_state["message"] = "Starting..."

    thread = threading.Thread(target=_run_simulation, args=(req,), daemon=True)
    thread.start()
    _sim_state["thread"] = thread

    return {"status": "started", "episode_id": req.episode_id}


@router.get("/status")
def get_status():
    return SimulationStatus(
        status=_sim_state["status"],
        current_day=_sim_state["current_day"],
        total_days=_sim_state["total_days"],
        progress_pct=_sim_state["progress_pct"],
        message=_sim_state["message"],
        elapsed_seconds=_sim_state["elapsed"],
    )


@router.get("/kpis")
def get_kpis(episode_id: str = None):
    """Get KPI summary from the latest village.db."""
    fdb = FacilitatorDB("facilitator.db")
    episodes = fdb.list_episodes()
    fdb.close()

    if not episodes:
        return KPIResponse()

    # Find the episode
    ep = None
    if episode_id:
        for e in episodes:
            if e["episode_id"] == episode_id:
                ep = e
                break
    if not ep:
        ep = episodes[0]  # latest

    db_path = ep.get("village_db_path")
    if not db_path or not os.path.exists(db_path):
        return KPIResponse()

    from simulation.database import VillageDB
    db = VillageDB(db_path, read_only=True)

    try:
        rev = db.fetchone("SELECT COALESCE(SUM(gross_revenue_thb), 0) AS total FROM store_metrics")
        txns = db.fetchone("SELECT COUNT(*) AS n FROM transactions")
        hh = db.fetchone("SELECT COUNT(*) AS n FROM households WHERE is_active = 1")
        avg = db.fetchone("SELECT AVG(total_value_thb) AS avg FROM transactions")
        days = db.fetchone("SELECT COUNT(DISTINCT day) AS n FROM transactions")

        churn = db.fetchone(
            "SELECT COUNT(*) AS n FROM lifecycle_events WHERE to_state = 'churned'"
        )
        total_hh = hh["n"] if hh else 0
        churn_rate = (churn["n"] / max(total_hh, 1)) if churn else 0

        return KPIResponse(
            total_revenue=rev["total"] if rev else 0,
            total_transactions=txns["n"] if txns else 0,
            active_households=total_hh,
            avg_basket_thb=round(avg["avg"], 2) if avg and avg["avg"] else 0,
            churn_rate=round(churn_rate, 3),
            days_simulated=days["n"] if days else 0,
        )
    finally:
        db.close()
