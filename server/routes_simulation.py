"""Analytics Village — Simulation control routes."""
from __future__ import annotations

import os
import shutil
import threading
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .models import SimulationRunRequest, SimulationStatus, KPIResponse
from .facilitator_db import FacilitatorDB

router = APIRouter(prefix="/api/simulation", tags=["simulation"])

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_sim_state = {
    "status": "idle", "current_day": None, "total_days": None,
    "progress_pct": 0.0, "message": "", "elapsed": 0.0, "thread": None,
}


class GenerateRequest(BaseModel):
    challenge_id: str = "ch01"
    title: str = "Challenge"
    primary_business: str = "supermarket"
    tier: int = 1
    challenge_type: str = "reporting"
    num_households: int = 150
    history_days: int = 90
    live_days: int = 0
    seed: int = 42
    use_llm: bool = False
    seed_findings: str | None = None
    max_retries: int = 3


def _run_simulation(req: GenerateRequest):
    """Background thread: generate data, validate, auto-retry if bad."""
    import sys
    sys.path.insert(0, PROJECT_ROOT)

    from simulation.world import SimConfig
    from simulation.history_runner import run_history
    from simulation.data_analyst import validate_data_quality

    _sim_state["status"] = "generating"
    _sim_state["message"] = "Starting..."
    t0 = time.time()

    config = SimConfig(
        num_households=req.num_households,
        history_days=req.history_days,
        live_days=req.live_days if req.use_llm else 0,
        random_seed=req.seed,
        episode_id=req.challenge_id,
        primary_business=req.primary_business,
    )

    output_dir = os.path.join(PROJECT_ROOT, "data", req.challenge_id)
    episode_dir = os.path.join(PROJECT_ROOT, "episodes", req.challenge_id, "data")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(episode_dir, exist_ok=True)

    db_path = os.path.join(output_dir, f"{req.challenge_id}_village.db")

    def progress(current, total, msg):
        _sim_state["current_day"] = current
        _sim_state["total_days"] = total
        _sim_state["progress_pct"] = (current / total * 100) if total > 0 else 0
        _sim_state["message"] = msg
        _sim_state["elapsed"] = time.time() - t0

    try:
        # Generate with auto-retry on quality failure
        attempt = 0
        quality_ok = False
        validation = None

        while attempt < req.max_retries and not quality_ok:
            attempt += 1
            seed = req.seed + (attempt - 1) * 100

            if attempt > 1:
                _sim_state["message"] = f"Retry {attempt}/{req.max_retries} (seed={seed})..."
                config.random_seed = seed

            if os.path.exists(db_path):
                os.remove(db_path)

            run_history(db_path, config, progress_callback=progress)

            # Validate data quality
            _sim_state["message"] = "Validating data quality..."
            from simulation.database import VillageDB
            db = VillageDB(db_path, read_only=True)
            validation = validate_data_quality(db)
            db.close()

            quality_ok = validation["passed"]
            if not quality_ok:
                failed = [c for c in validation["checks"] if not c["passed"]]
                _sim_state["message"] = f"Quality check failed: {', '.join(c['name'] for c in failed)}. Retrying..."

        # Generate key findings with LLM if available
        findings = []
        if req.use_llm:
            try:
                from simulation.llm_client import OllamaClient
                from simulation.data_analyst import generate_key_findings_sync
                llm = OllamaClient(model=config.ollama_model)
                if llm.is_available():
                    _sim_state["message"] = "LLM analyzing data and generating findings..."
                    db = VillageDB(db_path, read_only=True)
                    findings = generate_key_findings_sync(llm, db, req.seed_findings)
                    db.close()
            except Exception as e:
                _sim_state["message"] = f"LLM findings skipped: {e}"

        # Export
        _sim_state["message"] = "Exporting..."
        from simulation.exporter import EpisodeExporter
        exporter = EpisodeExporter(db_path, config)
        exporter.export_all(output_dir)

        # Copy DB to episode data folder
        shutil.copy2(db_path, os.path.join(episode_dir, "village.db"))

        # Copy brief and schema to episode folder
        ep_root = os.path.join(PROJECT_ROOT, "episodes", req.challenge_id)
        for fname in ["brief.md", "schema.json"]:
            src = os.path.join(output_dir, fname)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(ep_root, fname))

        # Create submissions folder
        sub_dir = os.path.join(PROJECT_ROOT, "submissions", req.challenge_id)
        os.makedirs(sub_dir, exist_ok=True)
        gitkeep = os.path.join(sub_dir, ".gitkeep")
        if not os.path.exists(gitkeep):
            open(gitkeep, "w").close()

        # Update facilitator DB
        fdb = FacilitatorDB("facilitator.db")
        fdb.create_episode({
            "episode_id": req.challenge_id,
            "title": req.title,
            "episode_number": int(req.challenge_id.replace("ch", "").replace("ep", "")) if any(req.challenge_id.startswith(p) for p in ["ch", "ep"]) else 1,
            "primary_business": req.primary_business,
            "tier": req.tier,
            "challenge_type": req.challenge_type,
            "village_db_path": db_path,
        })
        fdb.update_episode_status(req.challenge_id, "draft")

        # Save findings and validation
        import json
        if findings:
            fdb.set_pref(f"findings_{req.challenge_id}", json.dumps(findings))
        if validation:
            fdb.set_pref(f"validation_{req.challenge_id}", json.dumps(validation))
        fdb.close()

        _sim_state["status"] = "completed"
        _sim_state["progress_pct"] = 100.0
        _sim_state["message"] = (
            f"Done in {time.time()-t0:.1f}s. "
            f"{'Quality OK' if quality_ok else 'Quality warnings remain'}. "
            f"{len(findings)} findings generated."
            f"{f' (attempt {attempt})' if attempt > 1 else ''}"
        )

    except Exception as e:
        _sim_state["status"] = "error"
        _sim_state["message"] = str(e)
        import traceback
        traceback.print_exc()


@router.post("/run")
def start_simulation(req: GenerateRequest):
    if _sim_state["status"] == "generating":
        return {"error": "Simulation already running"}
    _sim_state.update(status="generating", progress_pct=0, message="Starting...")
    thread = threading.Thread(target=_run_simulation, args=(req,), daemon=True)
    thread.start()
    _sim_state["thread"] = thread
    return {"status": "started", "challenge_id": req.challenge_id}


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
    fdb = FacilitatorDB("facilitator.db")
    episodes = fdb.list_episodes()
    fdb.close()
    if not episodes:
        return KPIResponse()

    ep = None
    if episode_id:
        ep = next((e for e in episodes if e["episode_id"] == episode_id), None)
    if not ep:
        ep = episodes[0]

    db_path = ep.get("village_db_path")
    if not db_path or not os.path.exists(db_path):
        return KPIResponse()

    from simulation.database import VillageDB
    db = VillageDB(db_path, read_only=True)
    try:
        rev = db.fetchone("SELECT COALESCE(SUM(gross_revenue_thb),0) AS total FROM store_metrics")
        txns = db.fetchone("SELECT COUNT(*) AS n FROM transactions")
        hh = db.fetchone("SELECT COUNT(*) AS n FROM households WHERE is_active=1")
        avg = db.fetchone("SELECT AVG(total_value_thb) AS avg FROM transactions")
        days = db.fetchone("SELECT COUNT(DISTINCT day) AS n FROM transactions")
        churn = db.fetchone("SELECT COUNT(DISTINCT household_id) AS n FROM lifecycle_events WHERE to_state='churned'")
        total_hh = hh["n"] if hh else 1
        return KPIResponse(
            total_revenue=rev["total"] if rev else 0,
            total_transactions=txns["n"] if txns else 0,
            active_households=total_hh,
            avg_basket_thb=round(avg["avg"], 2) if avg and avg["avg"] else 0,
            churn_rate=round((churn["n"] if churn else 0) / max(total_hh, 1), 3),
            days_simulated=days["n"] if days else 0,
        )
    finally:
        db.close()


@router.get("/validate/{challenge_id}")
def validate_challenge(challenge_id: str):
    """Run data quality validation on a challenge's data."""
    fdb = FacilitatorDB("facilitator.db")
    ep = fdb.get_episode(challenge_id)
    fdb.close()
    if not ep or not ep.get("village_db_path"):
        raise HTTPException(404, "Challenge not found")

    from simulation.database import VillageDB
    from simulation.data_analyst import validate_data_quality
    db = VillageDB(ep["village_db_path"], read_only=True)
    result = validate_data_quality(db)
    db.close()
    return result


@router.get("/findings/{challenge_id}")
def get_findings(challenge_id: str):
    """Get stored key findings for a challenge."""
    import json
    fdb = FacilitatorDB("facilitator.db")
    raw = fdb.get_pref(f"findings_{challenge_id}")
    fdb.close()
    if raw:
        return json.loads(raw)
    return []


@router.post("/findings/{challenge_id}/generate")
def regenerate_findings(challenge_id: str, seed_findings: str = None):
    """Generate key findings using LLM."""
    fdb = FacilitatorDB("facilitator.db")
    ep = fdb.get_episode(challenge_id)
    if not ep or not ep.get("village_db_path"):
        fdb.close()
        raise HTTPException(404, "Challenge not found")

    try:
        from simulation.llm_client import OllamaClient
        from simulation.database import VillageDB
        from simulation.data_analyst import generate_key_findings_sync

        llm = OllamaClient()
        if not llm.is_available():
            fdb.close()
            return {"error": "Ollama not available. Start Ollama first."}

        db = VillageDB(ep["village_db_path"], read_only=True)
        findings = generate_key_findings_sync(llm, db, seed_findings)
        db.close()

        import json
        fdb.set_pref(f"findings_{challenge_id}", json.dumps(findings))
        fdb.close()
        return findings
    except Exception as e:
        fdb.close()
        raise HTTPException(500, str(e))
