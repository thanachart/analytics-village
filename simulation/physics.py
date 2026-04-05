"""
Analytics Village — Household physics engine.
Pure functions: pantry depletion, capacity constraints, budget pruning, visit scoring.
"""
from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .world import CalendarDay, HouseholdState

# ══════════════════════════════════════════════════════════════
# Constants
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
    "monday": 0.85, "tuesday": 0.80, "wednesday": 0.85,
    "thursday": 0.90, "friday": 1.10,
    "saturday": 1.30, "sunday": 1.15,
}

DEPLETION_RATES = {
    "fridge":  0.08,   # ~12 day full cycle — faster depletion
    "pantry":  0.035,  # ~28 day full cycle
    "freezer": 0.02,
}


# ══════════════════════════════════════════════════════════════
# Pantry
# ══════════════════════════════════════════════════════════════

def pantry_tick(hh: HouseholdState) -> float:
    """Daily passive depletion. Returns pantry_urgency (0-1)."""
    people = max(hh.household_size, 1)
    rate_mult = 0.5 + people * 0.25  # 1-person=0.75x, 4-person=1.5x, 6-person=2.0x

    hh.fridge_pct = max(0.0, hh.fridge_pct - DEPLETION_RATES["fridge"] * rate_mult)
    hh.pantry_pct = max(0.0, hh.pantry_pct - DEPLETION_RATES["pantry"] * rate_mult)
    hh.freezer_pct = max(0.0, hh.freezer_pct - DEPLETION_RATES["freezer"] * rate_mult)

    fridge_urg = 1.0 - hh.fridge_pct
    pantry_urg = 1.0 - hh.pantry_pct
    freezer_urg = (1.0 - hh.freezer_pct) if hh.freezer_capacity_L > 0 else 0.0

    urgency = fridge_urg * 0.50 + pantry_urg * 0.35 + freezer_urg * 0.15
    hh.pantry_urgency = min(1.0, max(0.0, urgency))
    return hh.pantry_urgency


def replenish_pantry(hh: HouseholdState, items: list[dict]) -> None:
    """After a purchase, replenish household storage."""
    for item in items:
        stype = item.get("storage_type", "ambient")
        qty = item.get("qty", 1)
        vol = item.get("unit_volume_L", 0.5) * qty

        if stype == "cold" and hh.fridge_capacity_L > 0:
            hh.fridge_pct = min(1.0, hh.fridge_pct + vol / hh.fridge_capacity_L)
        elif stype == "frozen" and hh.freezer_capacity_L > 0:
            hh.freezer_pct = min(1.0, hh.freezer_pct + vol / hh.freezer_capacity_L)
        else:
            if hh.pantry_capacity_units > 0:
                hh.pantry_pct = min(1.0, hh.pantry_pct + qty / hh.pantry_capacity_units)


# ══════════════════════════════════════════════════════════════
# Visit probability — REALISTIC: 2-4 visits per week for most HH
# ══════════════════════════════════════════════════════════════

def fast_score(
    hh: HouseholdState,
    cal: CalendarDay,
    days_since_last_visit: int | None,
    stock_signal: float = 0.0,
) -> float:
    """
    Compute visit probability.
    Target: ~40-60% chance per day → 2.8-4.2 visits per week.
    """
    # Base visit rate: most people shop frequently
    base = 0.45  # ~3.1 visits per week

    # Pantry urgency boost (low pantry → must shop)
    pantry_boost = hh.pantry_urgency * 0.35  # up to +0.35

    # Routine: habitual shoppers visit on their preferred days
    dow_weight = WEEKDAY_WEIGHTS.get(cal.day_of_week, 0.85)
    routine_effect = (dow_weight - 1.0) * hh.routine_strength * 0.5  # ±0.15

    # Calendar effects (payday, weekend, holidays)
    cal_effect = (cal.demand_multiplier - 1.0) * 0.3
    if cal.is_payday_week:
        cal_effect += 0.10

    # Recency: just visited yesterday → less likely, absent 5+ days → more likely
    recency = 0.0
    if days_since_last_visit is not None:
        if days_since_last_visit == 0:
            recency = -0.30  # just went today
        elif days_since_last_visit == 1:
            recency = -0.15
        elif days_since_last_visit >= 5:
            recency = min(0.25, (days_since_last_visit - 4) * 0.08)
        elif days_since_last_visit >= 3:
            recency = 0.05

    # Income effect: higher income → slightly more frequent
    income_boost = {"low": -0.05, "medium": 0.0, "high": 0.08}.get(hh.income_bracket, 0)

    # Mood
    mood_effect = hh.mood_modifier * 0.3

    # Combine
    p = base + pantry_boost + routine_effect + cal_effect + recency + income_boost + mood_effect

    # Clamp to realistic range
    return max(0.05, min(0.85, p))


# ══════════════════════════════════════════════════════════════
# Capacity constraints
# ══════════════════════════════════════════════════════════════

def capacity_constrain(basket: list[dict], hh: HouseholdState) -> list[dict]:
    """Remove/reduce items that won't fit in storage."""
    basket_sorted = sorted(basket, key=lambda x: (x.get("is_impulse", 0), -x.get("priority", 5)))

    remaining_fridge = hh.fridge_capacity_L * (1.0 - hh.fridge_pct)
    remaining_pantry = hh.pantry_capacity_units * (1.0 - hh.pantry_pct)
    remaining_freezer = hh.freezer_capacity_L * (1.0 - hh.freezer_pct)

    result = []
    for item in basket_sorted:
        stype = item.get("storage_type", "ambient")
        vol = item.get("unit_volume_L", 0.5)
        qty = item["qty"]

        if stype == "cold":
            fits = int(remaining_fridge / max(vol, 0.01))
            actual = min(qty, max(0, fits))
            remaining_fridge -= actual * vol
        elif stype == "frozen":
            fits = int(remaining_freezer / max(vol, 0.01))
            actual = min(qty, max(0, fits))
            remaining_freezer -= actual * vol
        else:
            actual = min(qty, max(0, int(remaining_pantry)))
            remaining_pantry -= actual

        item_copy = dict(item)
        if actual > 0:
            item_copy["qty"] = actual
            if actual < qty:
                item_copy["storage_blocked"] = True
        else:
            item_copy["qty"] = 0
            item_copy["storage_blocked"] = True
        result.append(item_copy)

    return result


# ══════════════════════════════════════════════════════════════
# Budget pruning
# ══════════════════════════════════════════════════════════════

def budget_prune(basket: list[dict], budget_remaining: float) -> list[dict]:
    """Trim basket to fit budget. Cut impulse items first."""
    total = sum(i["qty"] * i.get("unit_price", 0) for i in basket if i["qty"] > 0)
    if total <= budget_remaining:
        return basket

    # Sort: keep staples, cut impulse/snacks first
    items = list(enumerate(basket))
    items.sort(key=lambda x: (
        0 if x[1].get("category") in ("medicine", "baby") else
        100 + x[1].get("unit_price", 0) if x[1].get("is_impulse") else
        50 + x[1].get("unit_price", 0) if x[1].get("category") in ("snacks", "beverage") else
        10
    ), reverse=True)

    spent = 0
    keep = [True] * len(basket)
    # First pass: mark what fits
    for orig_idx, item in sorted(items, key=lambda x: x[0]):
        cost = item["qty"] * item.get("unit_price", 0)
        if spent + cost <= budget_remaining:
            spent += cost
        else:
            can_afford = int((budget_remaining - spent) / max(item.get("unit_price", 1), 0.01))
            if can_afford > 0:
                basket[orig_idx] = dict(item)
                basket[orig_idx]["qty"] = can_afford
                basket[orig_idx]["budget_pruned"] = True
                spent += can_afford * item.get("unit_price", 0)
            else:
                basket[orig_idx] = dict(item)
                basket[orig_idx]["qty"] = 0
                basket[orig_idx]["budget_pruned"] = True

    return basket


# ══════════════════════════════════════════════════════════════
# Satisfaction
# ══════════════════════════════════════════════════════════════

def compute_satisfaction(items_wanted, items_got, stockouts, budget_pruned, promo_responded):
    score = 1.0
    if items_wanted > 0:
        fill_rate = items_got / items_wanted
        score -= (1.0 - fill_rate) * 0.5
    score -= stockouts * 0.12
    score -= budget_pruned * 0.04
    if promo_responded:
        score += 0.08
    score = max(0.0, min(1.0, score))

    if score >= 0.65:
        return "happy", score
    elif score >= 0.35:
        return "neutral", score
    return "frustrated", score


def update_mood(hh: HouseholdState, satisfaction: str) -> None:
    if satisfaction == "happy":
        hh.mood = "positive"
        hh.mood_modifier = min(0.15, hh.mood_modifier + 0.05)
    elif satisfaction == "frustrated":
        hh.mood = "negative"
        hh.mood_modifier = max(-0.15, hh.mood_modifier - 0.08)
    else:
        hh.mood = "neutral"
        hh.mood_modifier *= 0.7


# ══════════════════════════════════════════════════════════════
# Budget management — FIXED: deterministic weekly reset
# ══════════════════════════════════════════════════════════════

def reset_weekly_budget(hh: HouseholdState, rng: random.Random) -> None:
    """Reset household weekly budget with variance."""
    variance = hh.budget_variance_pct
    mult = rng.gauss(1.0, variance)
    mult = max(0.7, min(1.3, mult))
    hh.budget_remaining_thb = hh.weekly_budget_thb * mult


def apply_payday_boost(hh: HouseholdState) -> None:
    """Boost remaining budget during payday week."""
    hh.budget_remaining_thb = max(hh.budget_remaining_thb, hh.weekly_budget_thb * 1.3)


def is_budget_reset_day(day: int) -> bool:
    """Budget resets every 7 days (modular, works with negative days)."""
    return day % 7 == 0
