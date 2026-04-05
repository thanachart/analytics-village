"""
Analytics Village — Live Simulation Runner (Phase 3).
Runs the live simulation period with LLM calls for uncertain decisions.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from typing import Callable, TYPE_CHECKING

from .physics import fast_score, pantry_tick, reset_weekly_budget, apply_payday_boost
from .transaction_engine import TransactionEngine
from .lifecycle_scanner import LifecycleScanner
from .consumer_agent import ConsumerAgent
from .store_agent import StoreManagerAgent
from .world import LifecycleState, EventType

if TYPE_CHECKING:
    from .database import VillageDB
    from .llm_client import OllamaClient
    from .world import WorldState, SimConfig, HouseholdState

logger = logging.getLogger(__name__)


class LiveSimRunner:
    """
    Runs the live simulation period with LLM-driven decisions.
    Uses async batching for concurrent LLM calls.
    """

    def __init__(
        self,
        db: VillageDB,
        world: WorldState,
        llm: OllamaClient,
        config: SimConfig,
    ):
        self.db = db
        self.world = world
        self.llm = llm
        self.config = config
        self.rng = random.Random(config.random_seed + 1000)
        self.engine = TransactionEngine(db, world, self.rng)
        self.scanner = LifecycleScanner()
        self.consumer = ConsumerAgent(llm)
        self.store_mgr = StoreManagerAgent(llm)

    async def run(
        self,
        days: int,
        progress_callback: Callable | None = None,
    ) -> dict:
        """Run the live simulation for N days."""
        stats = {"total_txns": 0, "llm_calls": 0, "rule_decisions": 0}
        t0 = time.time()

        for day_idx in range(days):
            day = day_idx  # Live sim starts at day 0
            day_stats = await self.run_day(day)
            stats["total_txns"] += day_stats.get("transactions", 0)
            stats["llm_calls"] += day_stats.get("llm_calls", 0)
            stats["rule_decisions"] += day_stats.get("rule_decisions", 0)

            if progress_callback:
                elapsed = time.time() - t0
                progress_callback(
                    day_idx + 1, days,
                    f"Day {day}: {day_stats['transactions']} txns, "
                    f"{day_stats['llm_calls']} LLM calls ({elapsed:.0f}s)"
                )

        stats["elapsed_seconds"] = round(time.time() - t0, 1)
        return stats

    async def run_day(self, day: int) -> dict:
        """Run one day of live simulation."""
        self.world.start_day(day)
        cal = self.world.get_calendar_day(day)
        stats = {"transactions": 0, "llm_calls": 0, "rule_decisions": 0}

        # Monday: reset budgets
        if cal.day_of_week == "monday":
            for hh in self.world.active_households():
                reset_weekly_budget(hh, self.rng)

        # Payday boost
        if cal.is_payday_week and cal.day_of_month == self.config.payday_day:
            for hh in self.world.active_households():
                apply_payday_boost(hh)

        # Step 1: Store decisions (before household decisions)
        for biz in self.world.active_businesses():
            self.engine.load_stock_cache(biz.business_id, day)
            if biz.business_id == self.config.primary_business:
                await self._store_decision(biz, day)

        # Step 2: Score all households
        scores = {}
        for hh in self.world.active_households():
            pantry_tick(hh)
            if hh.lifecycle_state == LifecycleState.UNAWARE.value:
                continue
            days_since = (day - hh.last_visit_day) if hh.last_visit_day is not None else None
            scores[hh.household_id] = fast_score(hh, cal, days_since)

        # Step 3: Route to LLM or rule
        llm_queue = []
        rule_skip = []
        rule_visit = []

        for hh_id, score in scores.items():
            hh = self.world.households[hh_id]
            has_override = self._check_overrides(hh, day)

            if has_override or (self.config.llm_skip_threshold < score < self.config.llm_rule_threshold):
                llm_queue.append(hh)
            elif score <= self.config.llm_skip_threshold:
                rule_skip.append(hh)
            else:
                rule_visit.append(hh)

        # Step 4: Process rule-based skips (stay home)
        for hh in rule_skip:
            self._record_stay_home(hh, day, cal, scores.get(hh.household_id, 0))
            stats["rule_decisions"] += 1

        # Step 5: Process rule-based visits
        for hh in rule_visit:
            basket = self.engine.build_rule_basket(
                hh, self.config.primary_business, day
            )
            if basket:
                txn = self.engine.process_transaction(
                    hh, self.config.primary_business, basket, day,
                    decision_type="high_certainty_rule",
                )
                if txn:
                    stats["transactions"] += 1
            self._record_visit(hh, day, cal, scores.get(hh.household_id, 0),
                              llm_called=False)
            stats["rule_decisions"] += 1

        # Step 6: Batch LLM decisions
        if llm_queue:
            llm_results = await self._batch_llm_decisions(llm_queue, cal, day)
            for hh, decision in llm_results:
                if decision and decision.get("visits"):
                    basket = self._convert_llm_basket(decision, hh)
                    if basket:
                        txn = self.engine.process_transaction(
                            hh, self.config.primary_business, basket, day,
                            decision_type="llm_decided",
                            llm_reasoning=decision.get("reasoning"),
                        )
                        if txn:
                            stats["transactions"] += 1
                    self._record_visit(hh, day, cal, scores.get(hh.household_id, 0),
                                      llm_called=True)
                else:
                    self._record_stay_home(hh, day, cal,
                                          scores.get(hh.household_id, 0),
                                          llm_called=True)
                stats["llm_calls"] += 1

        # Step 7: End of day
        for biz in self.world.active_businesses():
            self.engine.write_stock_ledger_day(biz.business_id, day)
            self.engine.write_store_metrics_day(biz.business_id, day)

        # Lifecycle scan
        self.scanner.scan_all(self.db, self.world, self.config.primary_business, day)

        # Flush events
        self.world.flush_events(self.db)
        self.db.commit()

        return stats

    async def _batch_llm_decisions(
        self,
        households: list[HouseholdState],
        cal,
        day: int,
    ) -> list[tuple]:
        """Run LLM decisions concurrently for a batch of households."""
        tasks = [
            self.consumer.decide(
                hh, self.world, cal,
                (day - hh.last_visit_day) if hh.last_visit_day is not None else None,
            )
            for hh in households
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = []
        for hh, result in zip(households, results):
            if isinstance(result, Exception):
                logger.warning(f"LLM failed for {hh.household_id}: {result}")
                # Fallback to rule
                output.append((hh, {"visits": self.rng.random() < 0.5}))
            else:
                output.append((hh, result))
        return output

    async def _store_decision(self, business, day: int) -> None:
        """Run store manager LLM decision."""
        # Get recent metrics
        metrics = self.db.fetchall(
            "SELECT * FROM store_metrics WHERE business_id = ? AND day BETWEEN ? AND ? ORDER BY day",
            (business.business_id, day - 7, day - 1)
        )

        # Get low stock SKUs
        low_stock = self.db.fetchall(
            "SELECT sl.sku_id, s.sku_name, sl.total_stock_close AS stock "
            "FROM stock_ledger sl JOIN skus s ON sl.sku_id = s.sku_id "
            "WHERE sl.business_id = ? AND sl.day = ? AND sl.total_stock_close < 15 "
            "ORDER BY sl.total_stock_close",
            (business.business_id, day - 1)
        )

        # Lifecycle counts
        lc_counts = {}
        for hh in self.world.active_households():
            state = hh.lifecycle_state
            lc_counts[state] = lc_counts.get(state, 0) + 1

        decision = await self.store_mgr.decide(
            business, self.world, day, metrics, low_stock, lc_counts
        )

        if decision:
            # Apply pricing changes
            for pc in decision.get("pricing_changes", []):
                sku_id = pc.get("sku_id")
                if sku_id and sku_id in self.world.skus:
                    business.current_prices[sku_id] = pc.get("new_price",
                        self.world.skus[sku_id].base_price_thb)

            # Apply promotions
            promo = decision.get("promotion")
            if promo and isinstance(promo, dict):
                for sku_id in promo.get("skus", []):
                    business.active_promos.append({
                        "sku_id": sku_id,
                        "discount_pct": promo.get("discount_pct", 10),
                        "end_day": day + promo.get("duration_days", 3),
                    })

    def _check_overrides(self, hh: HouseholdState, day: int) -> bool:
        """Check if this household MUST get an LLM call regardless of score."""
        if hh.lifecycle_state == LifecycleState.AWARE.value and hh.total_visits == 0:
            return True
        if hh.last_visit_day is not None:
            absent = day - hh.last_visit_day
            if absent == 14 or absent == 30:
                return True
        if hh.mood == "negative":
            return True
        return False

    def _convert_llm_basket(self, decision: dict, hh: HouseholdState) -> list[dict]:
        """Convert LLM basket output to transaction engine format."""
        basket = []
        for item in decision.get("basket", []):
            sku_id = item.get("sku_id", "")
            sku = self.world.skus.get(sku_id)
            if not sku:
                continue
            basket.append({
                "sku_id": sku_id,
                "qty": max(1, item.get("qty", 1)),
                "unit_price": sku.base_price_thb,
                "is_impulse": sku.is_impulse,
                "storage_type": sku.storage_type,
                "unit_volume_L": sku.unit_volume_L or 0.5,
                "category": sku.category,
                "priority": 5,
                "responded_to_promo": item.get("responded_to_promo", False),
            })
        return basket

    def _record_stay_home(self, hh, day, cal, score, llm_called=False):
        self.db.insert("resident_days", {
            "rd_id": f"RD_{hh.household_id}_{day:+05d}",
            "household_id": hh.household_id,
            "day": day,
            "lifecycle_state": hh.lifecycle_state,
            "decision_type": "stay_home",
            "stores_visited": None,
            "p_visit_score": round(score, 4),
            "llm_called": 1 if llm_called else 0,
            "pantry_urgency": round(hh.pantry_urgency, 4),
            "mood": hh.mood,
            "mood_modifier": round(hh.mood_modifier, 4),
            "calendar_multiplier": cal.demand_multiplier,
            "received_winback_offer": 0,
            "winback_offer_id": None,
            "word_of_mouth_spread": 0,
        })

    def _record_visit(self, hh, day, cal, score, llm_called=False):
        self.db.insert("resident_days", {
            "rd_id": f"RD_{hh.household_id}_{day:+05d}",
            "household_id": hh.household_id,
            "day": day,
            "lifecycle_state": hh.lifecycle_state,
            "decision_type": "visit_our_store",
            "stores_visited": json.dumps([self.config.primary_business]),
            "p_visit_score": round(score, 4),
            "llm_called": 1 if llm_called else 0,
            "pantry_urgency": round(hh.pantry_urgency, 4),
            "mood": hh.mood,
            "mood_modifier": round(hh.mood_modifier, 4),
            "calendar_multiplier": cal.demand_multiplier,
            "received_winback_offer": 0,
            "winback_offer_id": None,
            "word_of_mouth_spread": 0,
        })


def run_live_sync(
    db: VillageDB,
    world: WorldState,
    llm: OllamaClient,
    config: SimConfig,
    days: int,
    progress_callback: Callable | None = None,
) -> dict:
    """Synchronous wrapper for live simulation."""
    runner = LiveSimRunner(db, world, llm, config)
    return asyncio.run(runner.run(days, progress_callback))
