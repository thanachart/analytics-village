"""
Analytics Village — Compressed History Runner (Phase 1).
Runs the historical period (days -N to -1) without LLM calls.
Uses persona weights directly as decision probabilities.
~90 days x 150 households takes ~5-10 seconds.
"""
from __future__ import annotations

import json
import random
import time
from datetime import datetime
from typing import Callable

from .database import VillageDB
from .schema import create_village_db
from .world import WorldState, SimConfig, CalendarDay, LifecycleState, EventType
from .physics import fast_score, pantry_tick, reset_weekly_budget, apply_payday_boost, is_budget_reset_day
from .catalogue import (
    seed_businesses, seed_households, seed_skus, seed_suppliers,
    seed_calendar, seed_initial_stock,
)
from .transaction_engine import TransactionEngine
from .lifecycle_scanner import LifecycleScanner, assign_initial_lifecycle_states


def run_history(
    db_path: str,
    config: SimConfig,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> str:
    """
    Full history generation: create DB, seed entities, run compressed simulation.

    Parameters
    ----------
    db_path : str
        Output path for village.db
    config : SimConfig
        Simulation configuration
    progress_callback : callable, optional
        Called with (current_day_index, total_days, status_message)

    Returns
    -------
    str
        Path to the generated village.db
    """
    rng = random.Random(config.random_seed)
    t0 = time.time()

    # ── Phase 0: Create DB and seed ──────────────────────────────
    if progress_callback:
        progress_callback(0, config.history_days, "Phase 0: Creating database...")

    create_village_db(db_path)
    db = VillageDB(db_path)

    # Store config
    db.set_meta_json("config", {
        "num_households": config.num_households,
        "history_days": config.history_days,
        "live_days": config.live_days,
        "seed": config.random_seed,
        "scenario": config.scenario,
        "primary_business": config.primary_business,
    })

    # Seed entities
    if progress_callback:
        progress_callback(0, config.history_days, "Seeding businesses...")
    businesses = seed_businesses(db, config)

    if progress_callback:
        progress_callback(0, config.history_days, "Seeding households...")
    households = seed_households(db, config)

    if progress_callback:
        progress_callback(0, config.history_days, "Seeding SKUs...")
    skus = seed_skus(db)

    if progress_callback:
        progress_callback(0, config.history_days, "Seeding suppliers...")
    suppliers = seed_suppliers(db, config)

    if progress_callback:
        progress_callback(0, config.history_days, "Seeding calendar...")
    calendar = seed_calendar(db, config)

    # Initial stock
    first_day = -config.history_days
    seed_initial_stock(db, skus, first_day)
    db.commit()

    # ── Load world state ─────────────────────────────────────────
    world = WorldState.from_db(db, config)

    # In history mode: all households start as "retained" (they've been shopping here)
    # The lifecycle scanner will naturally create at_risk/churned during the simulation
    for hh in world.active_households():
        hh.lifecycle_state = "retained"
        hh.last_visit_day = first_day - rng.randint(1, 5)  # recently visited
        hh.total_visits = rng.randint(5, 30)
        hh.first_visit_day = first_day - rng.randint(30, 365)

    # Initialize budgets
    for hh in world.active_households():
        reset_weekly_budget(hh, rng)

    # Build calendar lookup
    for evt in db.fetchall("SELECT * FROM calendar_events"):
        day = evt["day"]
        if day not in world.calendar:
            world.calendar[day] = world.get_calendar_day(day)
        cal = world.calendar[day]
        cal.demand_multiplier = max(cal.demand_multiplier, evt["demand_multiplier"])
        cal.events.append(evt["event_name"])
        if evt["category_effects"]:
            effects = json.loads(evt["category_effects"])
            cal.category_effects.update(effects)

    # ── Phase 1: Compressed history run ──────────────────────────
    engine = TransactionEngine(db, world, rng)
    scanner = LifecycleScanner()
    total_txns = 0
    total_days = config.history_days

    for day_idx in range(total_days):
        day = first_day + day_idx
        world.start_day(day)
        cal = world.get_calendar_day(day)

        # Budget reset every 7 days (works with negative days)
        if is_budget_reset_day(day):
            for hh in world.active_households():
                reset_weekly_budget(hh, rng)

        # Payday boost
        if cal.is_payday_week:
            for hh in world.active_households():
                apply_payday_boost(hh)

        # Load stock for active businesses
        for biz in world.active_businesses():
            engine.load_stock_cache(biz.business_id, day)

        # Process each household
        day_txns = 0
        visiting = []

        for hh in world.active_households():
            # Passive pantry depletion
            pantry_tick(hh)

            # Skip households that haven't moved in yet
            if hasattr(hh, 'move_in_day') and day < getattr(hh, 'move_in_day', -9999):
                continue

            # Skip unaware (no shopping at this store)
            if hh.lifecycle_state == LifecycleState.UNAWARE.value:
                # Small chance of becoming aware via word-of-mouth
                if rng.random() < 0.02:
                    hh.lifecycle_state = LifecycleState.AWARE.value
                continue

            # Compute visit probability
            days_since = (day - hh.last_visit_day) if hh.last_visit_day is not None else None
            p_visit = fast_score(hh, cal, days_since)

            # Record resident_day
            decision = "stay_home"
            stores_visited = None

            if rng.random() < p_visit:
                # Decide which store to visit
                primary = config.primary_business
                visit_store = primary

                # Some households split shop
                if rng.random() < 0.15 and hh.lifecycle_state in (
                    LifecycleState.AT_RISK.value, LifecycleState.RETAINED.value
                ):
                    # Visit alternative store too
                    alt_stores = ["wet_market", "convenience"]
                    alt = rng.choice(alt_stores)
                    also_visited = [alt]
                    decision = "split_shop"
                    stores_visited = json.dumps([visit_store, alt])

                    # Record alt_transaction
                    alt_value = rng.uniform(30, 200) * (1 + (hh.income_bracket == "high") * 0.5)
                    db.insert("alt_transactions", {
                        "transaction_id": f"ALT_{hh.household_id}_{day:+05d}",
                        "household_id": hh.household_id,
                        "business_id": alt,
                        "day": day,
                        "total_value_thb": round(alt_value, 2),
                        "item_count": rng.randint(1, 5),
                        "category_breakdown": json.dumps({"fresh_produce": 0.6, "dry_goods": 0.4}),
                        "triggered_by": rng.choice(["habit", "stockout", "price"]),
                    })
                else:
                    also_visited = None
                    decision = "visit_our_store"
                    stores_visited = json.dumps([visit_store])

                # Build basket and process transaction
                basket = engine.build_rule_basket(hh, visit_store, day)
                if basket:
                    txn = engine.process_transaction(
                        hh, visit_store, basket, day,
                        decision_type="rule_decided",
                        also_visited=[a for a in (also_visited or [])],
                    )
                    if txn:
                        day_txns += 1
                        visiting.append(hh.household_id)

            # Write resident_day record
            db.insert("resident_days", {
                "rd_id": f"RD_{hh.household_id}_{day:+05d}",
                "household_id": hh.household_id,
                "day": day,
                "lifecycle_state": hh.lifecycle_state,
                "decision_type": decision,
                "stores_visited": stores_visited,
                "p_visit_score": round(p_visit, 4),
                "llm_called": 0,
                "pantry_urgency": round(hh.pantry_urgency, 4),
                "mood": hh.mood,
                "mood_modifier": round(hh.mood_modifier, 4),
                "calendar_multiplier": cal.demand_multiplier,
                "received_winback_offer": 0,
                "winback_offer_id": None,
                "word_of_mouth_spread": 0,
            })

        # End-of-day stock ledger
        for biz in world.active_businesses():
            engine.write_stock_ledger_day(biz.business_id, day)
            engine.write_store_metrics_day(biz.business_id, day)

        # Lifecycle scan (only for primary business)
        transitions = scanner.scan_all(db, world, config.primary_business, day)

        # Flush events
        world.flush_events(db)
        db.commit()

        total_txns += day_txns

        if progress_callback and (day_idx % 5 == 0 or day_idx == total_days - 1):
            elapsed = time.time() - t0
            progress_callback(
                day_idx + 1, total_days,
                f"Day {day:+d}: {day_txns} txns, {len(visiting)} visitors "
                f"({elapsed:.0f}s elapsed)"
            )

    # ── Finalize ─────────────────────────────────────────────────
    world.checkpoint(db, "post_history")

    # Summary stats
    elapsed = time.time() - t0
    db.set_meta_json("history_stats", {
        "total_transactions": total_txns,
        "total_days": total_days,
        "elapsed_seconds": round(elapsed, 1),
        "households": config.num_households,
    })
    db.commit()
    db.close()

    return db_path


def print_progress(current: int, total: int, message: str) -> None:
    """Default progress callback that prints to stdout."""
    pct = (current / total * 100) if total > 0 else 0
    bar_len = 30
    filled = int(bar_len * current / total) if total > 0 else 0
    bar = "#" * filled + "-" * (bar_len - filled)
    print(f"  [{bar}] {pct:5.1f}%  {message}", flush=True)
