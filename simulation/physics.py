"""
Analytics Village — Household physics engine.
Pure functions: pantry depletion, capacity constraints, budget pruning, visit scoring.
No LLM calls. No DB writes. Deterministic given RNG state.
"""
from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .world import CalendarDay, HouseholdState, SKUState

# ══════════════════════════════════════════════════════════════
# Constants from spec
# ══════════════════════════════════════════════════════════════

INCOME_BRACKETS = {
    "low":    {"weekly_min": 400,  "weekly_max": 900},
    "medium": {"weekly_min": 900,  "weekly_max": 2200},
    "high":   {"weekly_min": 2200, "weekly_max": 3500},
}

DWELLING_STORAGE = {
    "studio":          {"fridge_L": 15,  "pantry_units": 10, "freezer_L": 0},
    "apartment_small": {"fridge_L": 40,  "pantry_units": 25, "freezer_L": 5},
    "apartment_large": {"fridge_L": 80,  "pantry_units": 50, "freezer_L": 15},
    "house":           {"fridge_L": 120, "pantry_units": 80, "freezer_L": 30},
}

WEEKDAY_WEIGHTS = {
    "monday": 0.80, "tuesday": 0.75, "wednesday": 0.85,
    "thursday": 0.90, "friday": 1.05,
    "saturday": 1.25, "sunday": 1.10,
}

# Pantry depletion rate per person per day (fraction of capacity)
DEPLETION_RATES = {
    "fridge":  0.06,  # ~17 day full cycle
    "pantry":  0.03,  # ~33 day full cycle
    "freezer": 0.02,  # ~50 day full cycle
}

# Satisfaction from shopping experience
SATISFACTION_THRESHOLDS = {
    "happy": 0.7,       # score >= 0.7
    "neutral": 0.3,     # 0.3 <= score < 0.7
    "frustrated": 0.0,  # score < 0.3
}


# ══════════════════════════════════════════════════════════════
# Pantry management
# ══════════════════════════════════════════════════════════════


def pantry_tick(hh: HouseholdState) -> float:
    """
    Daily passive depletion of household storage.
    Returns pantry_urgency (0.0-1.0) — how urgently the household needs to shop.
    """
    people = max(hh.household_size, 1)
    rate_mult = people * 0.6 + 0.4  # scale with household size

    # Deplete each storage type
    hh.fridge_pct = max(0.0, hh.fridge_pct - DEPLETION_RATES["fridge"] * rate_mult)
    hh.pantry_pct = max(0.0, hh.pantry_pct - DEPLETION_RATES["pantry"] * rate_mult)
    hh.freezer_pct = max(0.0, hh.freezer_pct - DEPLETION_RATES["freezer"] * rate_mult)

    # Compute urgency: weighted average of how empty storage is
    fridge_urgency = 1.0 - hh.fridge_pct
    pantry_urgency = 1.0 - hh.pantry_pct
    freezer_urgency = 1.0 - hh.freezer_pct if hh.freezer_capacity_L > 0 else 0.0

    # Fridge matters most (perishables), then pantry, then freezer
    urgency = (fridge_urgency * 0.5 + pantry_urgency * 0.35 + freezer_urgency * 0.15)
    hh.pantry_urgency = min(1.0, max(0.0, urgency))
    return hh.pantry_urgency


def replenish_pantry(hh: HouseholdState, items: list[dict]) -> None:
    """
    After a purchase, replenish household storage based on items bought.
    items: list of {storage_type, unit_volume_L, qty}
    """
    for item in items:
        stype = item.get("storage_type", "ambient")
        qty = item.get("qty", 1)
        vol = item.get("unit_volume_L", 0.5) * qty

        if stype == "cold" and hh.fridge_capacity_L > 0:
            hh.fridge_pct = min(1.0, hh.fridge_pct + vol / hh.fridge_capacity_L)
        elif stype == "frozen" and hh.freezer_capacity_L > 0:
            hh.freezer_pct = min(1.0, hh.freezer_pct + vol / hh.freezer_capacity_L)
        else:
            # ambient → pantry
            if hh.pantry_capacity_units > 0:
                hh.pantry_pct = min(
                    1.0, hh.pantry_pct + qty / hh.pantry_capacity_units
                )


# ══════════════════════════════════════════════════════════════
# Visit probability (fast_score)
# ══════════════════════════════════════════════════════════════


def fast_score(
    hh: HouseholdState,
    cal: CalendarDay,
    days_since_last_visit: int | None,
    stock_signal: float = 0.0,
) -> float:
    """
    Compute visit probability from persona weights + calendar.
    No LLM. Pure math.

    P(visit) = sigmoid(
        pantry_urgency * 2.0
        + routine_strength * day_of_week_match * 1.5
        + calendar_multiplier
        + stock_anxiety * stock_signal
        + mood_modifier
        - 0.5  # base offset
    )

    Returns float 0.0-1.0.
    """
    # Pantry urgency component (strongest driver)
    pantry_component = hh.pantry_urgency * 2.0

    # Routine component: some people shop on specific days
    dow_weight = WEEKDAY_WEIGHTS.get(cal.day_of_week, 0.85)
    routine_component = hh.routine_strength * dow_weight * 1.5

    # Calendar multiplier (holidays, weather, payday)
    cal_component = (cal.demand_multiplier - 1.0)  # centered at 0
    if cal.is_payday_week:
        cal_component += 0.3

    # Stock anxiety: worried about running out
    stock_component = hh.stock_anxiety * stock_signal

    # Recency: longer absence → more likely to visit
    recency_boost = 0.0
    if days_since_last_visit is not None:
        if days_since_last_visit > 7:
            recency_boost = min(0.3, (days_since_last_visit - 7) * 0.05)
        elif days_since_last_visit < 2:
            recency_boost = -0.2  # just went recently

    # Combine
    raw = (
        pantry_component
        + routine_component
        + cal_component
        + stock_component
        + recency_boost
        + hh.mood_modifier
        - 0.5  # base offset — not everyone shops every day
    )

    return _sigmoid(raw)


def _sigmoid(x: float) -> float:
    """Logistic sigmoid clamped to avoid overflow."""
    x = max(-10.0, min(10.0, x))
    return 1.0 / (1.0 + math.exp(-x))


# ══════════════════════════════════════════════════════════════
# Capacity constraints
# ══════════════════════════════════════════════════════════════


def capacity_constrain(
    basket: list[dict],
    hh: HouseholdState,
) -> list[dict]:
    """
    Remove/reduce items that won't fit in household storage.

    basket items: list of dicts with keys:
        sku_id, qty, storage_type, unit_volume_L, is_impulse, category, priority

    Returns filtered basket with storage_blocked flag set on removed items.
    Priority: staples first (low is_impulse), impulse items cut first.
    """
    # Sort: staples first, impulse last (impulse gets cut first)
    basket_sorted = sorted(basket, key=lambda x: (x.get("is_impulse", 0),
                                                   -x.get("priority", 5)))

    remaining_fridge = hh.fridge_capacity_L * (1.0 - hh.fridge_pct)
    remaining_pantry = hh.pantry_capacity_units * (1.0 - hh.pantry_pct)
    remaining_freezer = hh.freezer_capacity_L * (1.0 - hh.freezer_pct)

    result = []
    for item in basket_sorted:
        stype = item.get("storage_type", "ambient")
        vol_per_unit = item.get("unit_volume_L", 0.5)
        qty = item["qty"]

        if stype == "cold":
            fits = int(remaining_fridge / vol_per_unit) if vol_per_unit > 0 else qty
            actual_qty = min(qty, max(0, fits))
            remaining_fridge -= actual_qty * vol_per_unit
        elif stype == "frozen":
            fits = int(remaining_freezer / vol_per_unit) if vol_per_unit > 0 else qty
            actual_qty = min(qty, max(0, fits))
            remaining_freezer -= actual_qty * vol_per_unit
        else:  # ambient → pantry
            actual_qty = min(qty, max(0, int(remaining_pantry)))
            remaining_pantry -= actual_qty

        if actual_qty > 0:
            item_copy = dict(item)
            item_copy["qty"] = actual_qty
            if actual_qty < qty:
                item_copy["storage_blocked"] = True
            result.append(item_copy)
        else:
            blocked = dict(item)
            blocked["qty"] = 0
            blocked["storage_blocked"] = True
            result.append(blocked)

    return result


# ══════════════════════════════════════════════════════════════
# Budget pruning
# ══════════════════════════════════════════════════════════════


def budget_prune(
    basket: list[dict],
    budget_remaining: float,
) -> list[dict]:
    """
    Trim basket to fit within remaining weekly budget.

    Pruning order (what gets cut first):
    1. Impulse items (highest price first)
    2. Treats/snacks/beverages
    3. Duplicate quantities of non-urgent staples
    Never prune: medicines, items with urgency > 0.8

    Sets budget_pruned=True on removed items.
    Returns all items (including pruned ones with qty=0 and budget_pruned=True).
    """
    # Categories that can be pruned
    PRUNE_CATEGORIES = {"snacks", "beverage", "treats", "impulse"}
    NEVER_PRUNE = {"medicine", "baby"}

    # Calculate total cost
    total = sum(i["qty"] * i.get("unit_price", 0) for i in basket if i["qty"] > 0)

    if total <= budget_remaining:
        return basket

    # Need to trim: sort by pruning priority (prune first = high priority number)
    def prune_priority(item):
        if item.get("category") in NEVER_PRUNE:
            return 0  # never prune
        if item.get("is_impulse"):
            return 100 + item.get("unit_price", 0)  # impulse first, expensive first
        if item.get("category") in PRUNE_CATEGORIES:
            return 50 + item.get("unit_price", 0)
        return 10  # staples: prune last

    # Process from most prunable to least
    items_by_priority = sorted(
        range(len(basket)), key=lambda i: prune_priority(basket[i]), reverse=True
    )

    remaining = budget_remaining
    keep_flags = [True] * len(basket)

    # First pass: figure out what we can keep
    for idx in sorted(range(len(basket)),
                      key=lambda i: prune_priority(basket[i])):
        item = basket[idx]
        cost = item["qty"] * item.get("unit_price", 0)
        if cost <= remaining:
            remaining -= cost
        else:
            # Try to keep partial quantity
            if item.get("unit_price", 0) > 0:
                can_afford = int(remaining / item["unit_price"])
                if can_afford > 0:
                    basket[idx] = dict(item)
                    basket[idx]["qty"] = can_afford
                    basket[idx]["budget_pruned"] = True
                    remaining -= can_afford * item["unit_price"]
                else:
                    basket[idx] = dict(item)
                    basket[idx]["qty"] = 0
                    basket[idx]["budget_pruned"] = True
            else:
                basket[idx] = dict(item)
                basket[idx]["qty"] = 0
                basket[idx]["budget_pruned"] = True

    return basket


# ══════════════════════════════════════════════════════════════
# Satisfaction scoring
# ══════════════════════════════════════════════════════════════


def compute_satisfaction(
    items_wanted: int,
    items_got: int,
    stockouts: int,
    budget_pruned_count: int,
    promo_responded: bool,
) -> tuple[str, float]:
    """
    Compute transaction satisfaction from shopping experience.
    Returns (satisfaction_label, satisfaction_score).
    """
    score = 1.0

    # Stockouts hurt satisfaction
    if items_wanted > 0:
        fill_rate = items_got / items_wanted
        score -= (1.0 - fill_rate) * 0.6

    # Each stockout is a direct frustration hit
    score -= stockouts * 0.15

    # Budget pruning is mildly frustrating
    score -= budget_pruned_count * 0.05

    # Promo response is a positive signal
    if promo_responded:
        score += 0.1

    score = max(0.0, min(1.0, score))

    if score >= 0.7:
        return "happy", score
    elif score >= 0.3:
        return "neutral", score
    else:
        return "frustrated", score


# ══════════════════════════════════════════════════════════════
# Mood update
# ══════════════════════════════════════════════════════════════


def update_mood(hh: HouseholdState, satisfaction: str) -> None:
    """
    Update household mood based on recent satisfaction.
    Mood affects next visit probability via mood_modifier.
    """
    if satisfaction == "happy":
        hh.mood = "positive"
        hh.mood_modifier = min(0.3, hh.mood_modifier + 0.1)
    elif satisfaction == "frustrated":
        hh.mood = "negative"
        hh.mood_modifier = max(-0.3, hh.mood_modifier - 0.15)
    else:
        # Decay toward neutral
        hh.mood = "neutral"
        hh.mood_modifier *= 0.8


# ══════════════════════════════════════════════════════════════
# Budget management
# ══════════════════════════════════════════════════════════════


def reset_weekly_budget(hh: HouseholdState, rng: random.Random) -> None:
    """Reset household weekly budget (called on Mondays)."""
    variance = hh.budget_variance_pct
    mult = rng.gauss(1.0, variance)
    mult = max(0.5, min(1.5, mult))
    hh.budget_remaining_thb = hh.weekly_budget_thb * mult


def apply_payday_boost(hh: HouseholdState) -> None:
    """Boost budget during payday week (days 25-30)."""
    hh.budget_remaining_thb *= 1.3
