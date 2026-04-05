"""
Analytics Village — Lifecycle Scanner.
Checks all households for state transitions each day.
Implements the exact lifecycle state machine from the spec.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .world import LifecycleState, EventType

if TYPE_CHECKING:
    from .database import VillageDB
    from .world import WorldState, HouseholdState


class LifecycleScanner:
    """
    Runs at end of each day. Checks all households for lifecycle transitions
    relative to a specific business.

    Transition rules (from spec):
      unaware          → aware              : received campaign or word-of-mouth
      aware            → new_acquisition    : made first purchase
      new_acquisition  → retained           : made 2nd purchase within 21 days
      retained         → at_risk            : absent 14d OR spend drop ≥40%
      at_risk          → retained           : visited and purchased
      at_risk          → churned            : 30 days since at_risk flag
      churned          → winback_candidate  : day 30-90 since churn
      winback_candidate→ retained           : accepted winback offer
      winback_candidate→ dormant            : day 90 since churn
      any              → removed            : move-out event
    """

    def scan_all(
        self,
        db: VillageDB,
        world: WorldState,
        business_id: str,
        day: int,
    ) -> list[dict]:
        """
        Scan all active households for lifecycle transitions.
        Returns list of transition event dicts.
        """
        transitions = []
        for hh in world.active_households():
            event = self.scan_household(db, world, hh, business_id, day)
            if event:
                transitions.append(event)
        return transitions

    def scan_household(
        self,
        db: VillageDB,
        world: WorldState,
        hh: HouseholdState,
        business_id: str,
        day: int,
    ) -> dict | None:
        """
        Check if this household's lifecycle state should transition today.
        Returns lifecycle_events dict if transition occurred, None otherwise.
        """
        current = hh.lifecycle_state
        new_state = None
        trigger_type = None
        trigger_detail = None

        # Days since last visit
        if hh.last_visit_day is not None:
            days_absent = day - hh.last_visit_day
        else:
            days_absent = None

        # Did they visit today?
        visited_today = self._visited_today(db, hh.household_id, business_id, day)

        # ── Transition: unaware → aware ──────────────────────────
        if current == LifecycleState.UNAWARE.value:
            # Becomes aware via word-of-mouth or campaign
            # For history runner: awareness spreads gradually
            pass  # handled by campaign/WOM events, not scanner

        # ── Transition: aware → new_acquisition ──────────────────
        elif current == LifecycleState.AWARE.value:
            if visited_today:
                new_state = LifecycleState.NEW_ACQUISITION.value
                trigger_type = "first_purchase"
                trigger_detail = f"First purchase at {business_id} on day {day}"
                hh.first_visit_day = day

        # ── Transition: new_acquisition → retained ───────────────
        elif current == LifecycleState.NEW_ACQUISITION.value:
            if visited_today and hh.first_visit_day is not None:
                days_since_first = day - hh.first_visit_day
                if days_since_first <= 21:
                    new_state = LifecycleState.RETAINED.value
                    trigger_type = "purchase_after_first"
                    trigger_detail = (
                        f"2nd purchase within 21 days "
                        f"(first: day {hh.first_visit_day}, now: day {day})"
                    )
            # If 21 days passed without 2nd purchase → revert to aware
            elif hh.first_visit_day and (day - hh.first_visit_day) > 21:
                new_state = LifecycleState.AWARE.value
                trigger_type = "acquisition_lapsed"
                trigger_detail = "No 2nd purchase within 21-day window"

        # ── Transition: retained → at_risk ───────────────────────
        elif current == LifecycleState.RETAINED.value:
            # Trigger A: absent 14+ consecutive days
            if days_absent is not None and days_absent >= 14:
                new_state = LifecycleState.AT_RISK.value
                trigger_type = "absence_14d"
                trigger_detail = f"No visit for {days_absent} days"
                hh.lifecycle_flag_day = day

            # Trigger B: 40% spend drop in rolling 21-day window
            elif days_absent is not None:
                spend_drop = self._compute_spend_drop(
                    db, hh.household_id, business_id, day
                )
                if spend_drop is not None and spend_drop <= -0.40:
                    new_state = LifecycleState.AT_RISK.value
                    trigger_type = "spend_drop_40pct"
                    trigger_detail = f"Spend dropped {spend_drop*100:.0f}% vs prior period"
                    hh.lifecycle_flag_day = day

        # ── Transition: at_risk → retained / churned ─────────────
        elif current == LifecycleState.AT_RISK.value:
            if visited_today:
                new_state = LifecycleState.RETAINED.value
                trigger_type = "purchase_after_atrisk"
                trigger_detail = f"Returned after at-risk period"
                hh.lifecycle_flag_day = None
            elif hh.lifecycle_flag_day is not None:
                days_since_flag = day - hh.lifecycle_flag_day
                if days_since_flag >= 30:
                    new_state = LifecycleState.CHURNED.value
                    trigger_type = "absence_30d"
                    trigger_detail = f"30 days since at_risk flag (flagged day {hh.lifecycle_flag_day})"
                    hh.lifecycle_flag_day = day  # reuse as churn date

        # ── Transition: churned → winback_candidate ──────────────
        elif current == LifecycleState.CHURNED.value:
            if visited_today:
                # Direct reactivation
                new_state = LifecycleState.RETAINED.value
                trigger_type = "reactivation"
                trigger_detail = "Purchased while in churned state"
                hh.lifecycle_flag_day = None
            elif hh.lifecycle_flag_day is not None:
                days_since_churn = day - hh.lifecycle_flag_day
                if 30 <= days_since_churn <= 90:
                    new_state = LifecycleState.WINBACK_CANDIDATE.value
                    trigger_type = "churn_30d_window"
                    trigger_detail = f"Entered winback window ({days_since_churn}d since churn)"

        # ── Transition: winback_candidate → retained / dormant ───
        elif current == LifecycleState.WINBACK_CANDIDATE.value:
            if visited_today:
                new_state = LifecycleState.RETAINED.value
                trigger_type = "winback_accepted"
                trigger_detail = "Accepted winback / returned on own"
                hh.lifecycle_flag_day = None
            elif hh.lifecycle_flag_day is not None:
                days_since_churn = day - hh.lifecycle_flag_day
                if days_since_churn > 90:
                    new_state = LifecycleState.DORMANT.value
                    trigger_type = "winback_expired"
                    trigger_detail = f"90 days since churn with no return"

        # ── No transition ────────────────────────────────────────
        if new_state is None:
            return None

        # Record transition
        hh.lifecycle_state = new_state

        # Compute context metrics
        stockout_30d = self._count_stockouts(db, hh.household_id, business_id, day, 30)
        alt_visits_30d = self._count_alt_visits(db, hh.household_id, day, 30)
        spend_21d = self._rolling_spend(db, hh.household_id, business_id, day, 21)

        event = {
            "event_id": world.next_event_id(),
            "household_id": hh.household_id,
            "business_id": business_id,
            "day": day,
            "from_state": current,
            "to_state": new_state,
            "trigger_type": trigger_type,
            "trigger_detail": trigger_detail,
            "days_since_last_visit": days_absent,
            "spend_last_21d_thb": spend_21d,
            "stockout_count_30d": stockout_30d,
            "alt_visits_30d": alt_visits_30d,
            "campaign_id": None,
        }
        db.insert("lifecycle_events", event)

        # Log to event_ledger
        world.add_event(
            new_state if new_state in ("at_risk", "churned") else "lifecycle_transition",
            "household", hh.household_id,
            {"from": current, "to": new_state, "trigger": trigger_type},
            target_type="store", target_id=business_id,
        )

        return event

    def _visited_today(
        self, db: VillageDB, household_id: str, business_id: str, day: int
    ) -> bool:
        row = db.fetchone(
            "SELECT 1 FROM transactions "
            "WHERE household_id = ? AND business_id = ? AND day = ?",
            (household_id, business_id, day)
        )
        return row is not None

    def _compute_spend_drop(
        self, db: VillageDB, household_id: str, business_id: str,
        day: int, window: int = 21,
    ) -> float | None:
        """
        Compute spend change: current window vs prior window.
        Returns fractional change (e.g., -0.4 = 40% drop). None if insufficient data.
        """
        current = db.fetchone(
            "SELECT COALESCE(SUM(total_value_thb), 0) AS spend FROM transactions "
            "WHERE household_id = ? AND business_id = ? AND day BETWEEN ? AND ?",
            (household_id, business_id, day - window, day)
        )
        prior = db.fetchone(
            "SELECT COALESCE(SUM(total_value_thb), 0) AS spend FROM transactions "
            "WHERE household_id = ? AND business_id = ? AND day BETWEEN ? AND ?",
            (household_id, business_id, day - 2 * window, day - window - 1)
        )
        if not prior or prior["spend"] == 0:
            return None
        return (current["spend"] - prior["spend"]) / prior["spend"]

    def _rolling_spend(
        self, db: VillageDB, household_id: str, business_id: str,
        day: int, window: int,
    ) -> float:
        row = db.fetchone(
            "SELECT COALESCE(SUM(total_value_thb), 0) AS spend FROM transactions "
            "WHERE household_id = ? AND business_id = ? AND day BETWEEN ? AND ?",
            (household_id, business_id, day - window, day)
        )
        return round(row["spend"], 2) if row else 0.0

    def _count_stockouts(
        self, db: VillageDB, household_id: str, business_id: str,
        day: int, window: int,
    ) -> int:
        row = db.fetchone(
            "SELECT COUNT(*) AS n FROM basket_items bi "
            "JOIN transactions t ON bi.transaction_id = t.transaction_id "
            "WHERE t.household_id = ? AND t.business_id = ? "
            "AND t.day BETWEEN ? AND ? AND bi.stockout_flag = 1",
            (household_id, business_id, day - window, day)
        )
        return row["n"] if row else 0

    def _count_alt_visits(
        self, db: VillageDB, household_id: str, day: int, window: int,
    ) -> int:
        row = db.fetchone(
            "SELECT COUNT(*) AS n FROM alt_transactions "
            "WHERE household_id = ? AND day BETWEEN ? AND ?",
            (household_id, day - window, day)
        )
        return row["n"] if row else 0


def assign_initial_lifecycle_states(
    world: WorldState,
    config,
    rng,
) -> None:
    """
    Assign initial lifecycle states to match target distribution at day 0.
    Called after history generation to set the starting state.
    """
    targets = {
        LifecycleState.UNAWARE.value: config.target_unaware,
        LifecycleState.AWARE.value: config.target_aware,
        LifecycleState.NEW_ACQUISITION.value: config.target_new_acquisition,
        LifecycleState.RETAINED.value: config.target_retained,
        LifecycleState.AT_RISK.value: config.target_at_risk,
        LifecycleState.CHURNED.value: config.target_churned,
        LifecycleState.WINBACK_CANDIDATE.value: config.target_winback_candidate,
    }

    hh_list = list(world.households.values())
    rng.shuffle(hh_list)
    n = len(hh_list)

    idx = 0
    for state, frac in targets.items():
        count = int(round(frac * n))
        for hh in hh_list[idx:idx + count]:
            hh.lifecycle_state = state
            if state == LifecycleState.AT_RISK.value:
                hh.lifecycle_flag_day = -rng.randint(1, 14)
            elif state == LifecycleState.CHURNED.value:
                hh.lifecycle_flag_day = -rng.randint(15, 45)
        idx += count

    # Remaining get assigned to retained
    for hh in hh_list[idx:]:
        hh.lifecycle_state = LifecycleState.RETAINED.value
