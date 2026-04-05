"""
Analytics Village — World State and Configuration.
Shared state accessible by all agents every simulation day.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .database import VillageDB


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════


class LifecycleState(str, Enum):
    UNAWARE = "unaware"
    AWARE = "aware"
    NEW_ACQUISITION = "new_acquisition"
    RETAINED = "retained"
    AT_RISK = "at_risk"
    CHURNED = "churned"
    WINBACK_CANDIDATE = "winback_candidate"
    DORMANT = "dormant"
    REMOVED = "removed"


class DecisionType(str, Enum):
    STAY_HOME = "stay_home"
    VISIT_OUR_STORE = "visit_our_store"
    VISIT_ALTERNATIVE = "visit_alternative"
    SPLIT_SHOP = "split_shop"
    WINBACK_ACCEPT = "winback_accept"
    WINBACK_REJECT = "winback_reject"


class Satisfaction(str, Enum):
    HAPPY = "happy"
    NEUTRAL = "neutral"
    FRUSTRATED = "frustrated"


class EventType(str, Enum):
    CAMPAIGN_LAUNCHED = "campaign_launched"
    VISIT = "visit"
    PURCHASE = "purchase"
    STOCKOUT_HIT = "stockout_hit"
    SUBSTITUTION = "substitution"
    STAY_HOME = "stay_home"
    SWITCH_STORE = "switch_store"
    WINBACK_SENT = "winback_sent"
    WINBACK_ACCEPTED = "winback_accepted"
    WINBACK_REJECTED = "winback_rejected"
    FIRST_PURCHASE = "first_purchase"
    AT_RISK_FLAGGED = "at_risk_flagged"
    CHURNED = "churned"
    PROFILE_DRIFTED = "profile_drifted"
    STRATEGY_SHIFTED = "strategy_shifted"
    PO_PLACED = "po_placed"
    PO_DELIVERED = "po_delivered"
    STOCK_ARRIVED = "stock_arrived"
    WORD_OF_MOUTH = "word_of_mouth"
    MOVE_IN = "move_in"
    MOVE_OUT = "move_out"
    WASTE_EXPIRED = "waste_expired"
    PROMO_NOTICED = "promo_noticed"


# ══════════════════════════════════════════════════════════════
# Data classes
# ══════════════════════════════════════════════════════════════

DAYS_OF_WEEK = ["monday", "tuesday", "wednesday", "thursday",
                "friday", "saturday", "sunday"]


@dataclass
class SimConfig:
    """Full simulation configuration — loaded from YAML."""
    # Village
    num_households: int = 150
    random_seed: int = 42
    history_days: int = 90
    live_days: int = 30

    # Demographics
    household_size_small_pct: float = 0.40
    household_size_medium_pct: float = 0.45
    household_size_large_pct: float = 0.15
    income_low_pct: float = 0.30
    income_medium_pct: float = 0.55
    income_high_pct: float = 0.15
    monthly_move_in_rate: float = 0.02
    monthly_move_out_rate: float = 0.02

    # Calendar
    payday_day: int = 28
    enable_weather: bool = True

    # Lifecycle targets at day 0
    target_unaware: float = 0.10
    target_aware: float = 0.15
    target_new_acquisition: float = 0.08
    target_retained: float = 0.42
    target_at_risk: float = 0.10
    target_churned: float = 0.12
    target_winback_candidate: float = 0.03

    # Scenario
    scenario: str = "declining"  # growing, declining, stable, recovering, crisis

    # Episode
    episode_id: str = "ep01"
    episode_number: int = 1
    primary_business: str = "supermarket"

    # LLM
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "gemma4:e2b"
    consumer_temp_min: float = 0.3
    consumer_temp_max: float = 0.9
    store_temp: float = 0.5
    qa_temp: float = 0.7
    persona_temp: float = 0.6
    max_concurrent_llm: int = 8
    llm_timeout_s: int = 90

    # Routing thresholds
    llm_skip_threshold: float = 0.15
    llm_rule_threshold: float = 0.85

    # Suppliers
    primary_fill_rate: float = 0.88
    backup_fill_rate: float = 0.72
    enable_adaptive_pricing: bool = True
    enable_partial_delivery: bool = True

    @classmethod
    def from_yaml(cls, path: str) -> SimConfig:
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        config = cls()
        # Flatten nested YAML structure into flat config
        for section in (data.get("village", {}),
                        data.get("village", {}).get("demographics", {}),
                        data.get("village", {}).get("calendar", {}),
                        data.get("village", {}).get("lifecycle_targets", {}),
                        data.get("episode", {}),
                        data.get("llm", {}),
                        data.get("businesses", {}).get("suppliers", {})):
            if isinstance(section, dict):
                for k, v in section.items():
                    attr = k.replace("-", "_")
                    if hasattr(config, attr):
                        setattr(config, attr, v)
        return config


@dataclass
class CalendarDay:
    """External events for a single simulation day."""
    day: int
    day_of_week: str  # 'monday' ... 'sunday'
    day_of_month: int  # 1-31
    week_of_month: int  # 1-5
    month: int  # 1-12
    is_payday_week: bool
    demand_multiplier: float = 1.0
    category_effects: dict[str, float] = field(default_factory=dict)
    events: list[str] = field(default_factory=list)

    @staticmethod
    def compute_day_of_week(day: int, seed_offset: int = 0) -> str:
        """Map simulation day to day of week. Day 0 = Monday by convention."""
        idx = (day + seed_offset) % 7
        return DAYS_OF_WEEK[idx]

    @staticmethod
    def compute_day_of_month(day: int, seed_offset: int = 1) -> int:
        """Approximate day-of-month (30-day months)."""
        return ((day + seed_offset - 1) % 30) + 1

    @staticmethod
    def compute_month(day: int) -> int:
        return ((day - 1) // 30) % 12 + 1

    @staticmethod
    def compute_week_of_month(day_of_month: int) -> int:
        return min((day_of_month - 1) // 7 + 1, 5)


@dataclass
class HouseholdState:
    """Runtime state for one household during simulation."""
    household_id: str
    household_size: int
    dwelling_type: str
    location_zone: str
    income_bracket: str
    weekly_budget_thb: float
    budget_variance_pct: float
    is_active: bool

    # Storage capacities
    fridge_capacity_L: float
    pantry_capacity_units: float
    freezer_capacity_L: float

    # Persona weights (0-1)
    price_sensitivity: float
    routine_strength: float
    health_orientation: float
    brand_loyalty: float
    stock_anxiety: float
    social_timing: float
    llm_temperature: float

    # Runtime
    lifecycle_state: str = LifecycleState.UNAWARE.value
    lifecycle_flag_day: int | None = None  # day when at_risk was set
    last_visit_day: int | None = None
    budget_remaining_thb: float = 0.0
    pantry_urgency: float = 0.5
    mood: str = "neutral"
    mood_modifier: float = 0.0

    # Pantry levels (0.0 - 1.0, fraction of capacity)
    fridge_pct: float = 0.5
    pantry_pct: float = 0.5
    freezer_pct: float = 0.5

    # Tracking
    total_visits: int = 0
    total_spend_thb: float = 0.0
    first_visit_day: int | None = None


@dataclass
class BusinessState:
    """Runtime state for one business during simulation."""
    business_id: str
    owner_id: str
    business_name: str
    business_type: str
    location_zone: str
    is_active: bool

    # Capacity
    shelf_capacity: int = 500  # total units
    warehouse_capacity: int = 2000
    cold_storage_capacity_L: float = 400.0
    po_budget_weekly_thb: float = 50000.0
    po_budget_remaining_thb: float = 50000.0
    staff_restock_cap: int = 200  # unit-movements per morning

    # Current stock snapshot {sku_id: shelf_units}
    current_stock: dict[str, int] = field(default_factory=dict)

    # Current prices {sku_id: sale_price_thb}
    current_prices: dict[str, float] = field(default_factory=dict)

    # Active promos [{sku_id, discount_pct, end_day}]
    active_promos: list[dict] = field(default_factory=list)


@dataclass
class SKUState:
    """Product catalogue entry."""
    sku_id: str
    business_id: str
    sku_name: str
    category: str
    subcategory: str | None
    storage_type: str
    shelf_life_days: int | None
    base_cost_thb: float
    base_price_thb: float
    is_elastic: bool
    is_impulse: bool
    unit_volume_L: float | None
    typical_daily_consume_per_person: float | None
    typical_daily_consume_per_household: float | None


@dataclass
class SupplierState:
    """Supplier runtime state."""
    supplier_id: str
    supplier_name: str
    reliability_score: float
    base_lead_time_days: int
    max_lead_time_days: int
    min_order_qty: int
    price_tier: str
    supplies_skus: list[str]
    is_backup: bool
    adaptive_price_threshold: int
    recent_orders: list[int] = field(default_factory=list)  # days of recent orders


# ══════════════════════════════════════════════════════════════
# World State
# ══════════════════════════════════════════════════════════════


@dataclass
class WorldState:
    """Shared simulation state accessible by all agents each day."""
    config: SimConfig
    current_day: int = 0

    # Entities
    households: dict[str, HouseholdState] = field(default_factory=dict)
    businesses: dict[str, BusinessState] = field(default_factory=dict)
    skus: dict[str, SKUState] = field(default_factory=dict)
    suppliers: dict[str, SupplierState] = field(default_factory=dict)

    # Calendar
    calendar: dict[int, CalendarDay] = field(default_factory=dict)

    # Day events queue — flushed to DB at end of day
    day_events: list[dict] = field(default_factory=list)

    # Counters
    _event_counter: int = 0
    _txn_counter: int = 0
    _item_counter: int = 0

    def next_event_id(self) -> str:
        self._event_counter += 1
        return f"EVT_{self.current_day:+05d}_{self._event_counter:06d}"

    def next_txn_id(self, household_id: str, business_id: str) -> str:
        self._txn_counter += 1
        return f"TXN_{self.current_day:+05d}_{household_id}_{business_id}_{self._txn_counter:04d}"

    def next_item_id(self, txn_id: str) -> str:
        self._item_counter += 1
        return f"ITEM_{txn_id}_{self._item_counter:04d}"

    def get_calendar_day(self, day: int) -> CalendarDay:
        if day in self.calendar:
            return self.calendar[day]
        # Generate on the fly
        dow = CalendarDay.compute_day_of_week(day)
        dom = CalendarDay.compute_day_of_month(day)
        wom = CalendarDay.compute_week_of_month(dom)
        month = CalendarDay.compute_month(day)
        is_payday = abs(dom - self.config.payday_day) <= 2 or dom >= 28
        return CalendarDay(
            day=day, day_of_week=dow, day_of_month=dom,
            week_of_month=wom, month=month, is_payday_week=is_payday,
        )

    def add_event(self, event_type: str, actor_type: str, actor_id: str,
                  payload: dict, target_type: str = None,
                  target_id: str = None) -> None:
        self.day_events.append({
            "event_id": self.next_event_id(),
            "day": self.current_day,
            "timestamp_ms": int(time.time() * 1000),
            "event_type": event_type,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "target_type": target_type,
            "target_id": target_id,
            "payload": json.dumps(payload, ensure_ascii=False),
        })

    def start_day(self, day: int) -> None:
        """Advance to a new simulation day."""
        self.current_day = day
        self.day_events.clear()
        self._event_counter = 0
        self._txn_counter = 0
        self._item_counter = 0

    def flush_events(self, db: VillageDB) -> int:
        """Write accumulated events to event_ledger. Returns count."""
        if not self.day_events:
            return 0
        db.insert_many("event_ledger", self.day_events)
        count = len(self.day_events)
        self.day_events.clear()
        return count

    def active_households(self) -> list[HouseholdState]:
        return [h for h in self.households.values() if h.is_active]

    def active_businesses(self) -> list[BusinessState]:
        return [b for b in self.businesses.values() if b.is_active]

    @classmethod
    def from_db(cls, db: VillageDB, config: SimConfig) -> WorldState:
        """Load world state from an existing village.db."""
        world = cls(config=config)

        # Load households
        for row in db.fetchall("SELECT * FROM households WHERE is_active = 1"):
            world.households[row["household_id"]] = HouseholdState(
                household_id=row["household_id"],
                household_size=row["household_size"],
                dwelling_type=row["dwelling_type"],
                location_zone=row["location_zone"],
                income_bracket=row["income_bracket"],
                weekly_budget_thb=row["weekly_budget_thb"],
                budget_variance_pct=row["budget_variance_pct"],
                is_active=bool(row["is_active"]),
                fridge_capacity_L=row["fridge_capacity_L"],
                pantry_capacity_units=row["pantry_capacity_units"],
                freezer_capacity_L=row["freezer_capacity_L"],
                price_sensitivity=row["price_sensitivity"],
                routine_strength=row["routine_strength"],
                health_orientation=row["health_orientation"],
                brand_loyalty=row["brand_loyalty"],
                stock_anxiety=row["stock_anxiety"],
                social_timing=row["social_timing"],
                llm_temperature=row["llm_temperature"],
            )

        # Load businesses
        for row in db.fetchall("SELECT * FROM businesses WHERE is_active = 1"):
            world.businesses[row["business_id"]] = BusinessState(
                business_id=row["business_id"],
                owner_id=row["owner_id"],
                business_name=row["business_name"],
                business_type=row["business_type"],
                location_zone=row["location_zone"],
                is_active=bool(row["is_active"]),
            )

        # Load SKUs
        for row in db.fetchall("SELECT * FROM skus WHERE is_active = 1"):
            world.skus[row["sku_id"]] = SKUState(
                sku_id=row["sku_id"],
                business_id=row["business_id"],
                sku_name=row["sku_name"],
                category=row["category"],
                subcategory=row.get("subcategory"),
                storage_type=row["storage_type"],
                shelf_life_days=row.get("shelf_life_days"),
                base_cost_thb=row["base_cost_thb"],
                base_price_thb=row["base_price_thb"],
                is_elastic=bool(row["is_elastic"]),
                is_impulse=bool(row["is_impulse"]),
                unit_volume_L=row.get("unit_volume_L"),
                typical_daily_consume_per_person=row.get(
                    "typical_daily_consume_per_person"
                ),
                typical_daily_consume_per_household=row.get(
                    "typical_daily_consume_per_household"
                ),
            )

        # Load suppliers
        for row in db.fetchall("SELECT * FROM suppliers"):
            world.suppliers[row["supplier_id"]] = SupplierState(
                supplier_id=row["supplier_id"],
                supplier_name=row["supplier_name"],
                reliability_score=row["reliability_score"],
                base_lead_time_days=row["base_lead_time_days"],
                max_lead_time_days=row["max_lead_time_days"],
                min_order_qty=row["min_order_qty"],
                price_tier=row["price_tier"],
                supplies_skus=json.loads(row["supplies_skus"]),
                is_backup=bool(row["is_backup"]),
                adaptive_price_threshold=row["adaptive_price_threshold"],
            )

        return world

    def checkpoint(self, db: VillageDB, name: str) -> None:
        """Save checkpoint to simulation metadata."""
        db.set_meta_json(f"checkpoint_{name}", {
            "day": self.current_day,
            "timestamp": time.time(),
            "households": len(self.households),
            "businesses": len(self.businesses),
            "skus": len(self.skus),
        })
        db.commit()
