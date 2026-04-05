"""
Analytics Village — Transaction Engine.
Processes basket decisions into transactions, handling stock checks,
partial fills, substitutions, and stockouts.
"""
from __future__ import annotations

import json
import random
from datetime import datetime
from typing import TYPE_CHECKING

from .physics import (
    capacity_constrain, budget_prune, compute_satisfaction,
    update_mood, replenish_pantry,
)
from .world import CalendarDay, EventType

if TYPE_CHECKING:
    from .database import VillageDB
    from .world import WorldState, HouseholdState, BusinessState, SKUState


class TransactionEngine:
    """
    Processes one household visit into database records.
    Handles: stock check, partial fill, substitution, stockout, waste.
    """

    def __init__(self, db: VillageDB, world: WorldState, rng: random.Random):
        self.db = db
        self.world = world
        self.rng = rng
        # Stock cache: {(business_id, sku_id): shelf_units} for current day
        self._stock_cache: dict[tuple[str, str], int] = {}

    def load_stock_cache(self, business_id: str, day: int) -> None:
        """Load current shelf stock for a business from the latest ledger."""
        rows = self.db.fetchall(
            "SELECT sku_id, shelf_close FROM stock_ledger "
            "WHERE business_id = ? AND day = ? ",
            (business_id, day - 1)
        )
        for row in rows:
            self._stock_cache[(business_id, row["sku_id"])] = row["shelf_close"]

        # If no prior day data, use initial stock
        if not rows:
            rows = self.db.fetchall(
                "SELECT sku_id, shelf_close FROM stock_ledger "
                "WHERE business_id = ? ORDER BY day DESC",
                (business_id,)
            )
            seen = set()
            for row in rows:
                key = (business_id, row["sku_id"])
                if key not in seen:
                    self._stock_cache[key] = row["shelf_close"]
                    seen.add(key)

    def get_shelf_stock(self, business_id: str, sku_id: str) -> int:
        return self._stock_cache.get((business_id, sku_id), 0)

    def deduct_stock(self, business_id: str, sku_id: str, qty: int) -> None:
        key = (business_id, sku_id)
        current = self._stock_cache.get(key, 0)
        self._stock_cache[key] = max(0, current - qty)

    def process_transaction(
        self,
        hh: HouseholdState,
        business_id: str,
        basket_request: list[dict],
        day: int,
        decision_type: str = "rule_decided",
        llm_reasoning: str | None = None,
        also_visited: list[str] | None = None,
    ) -> dict | None:
        """
        Process one household visit into a transaction.

        basket_request: list of dicts with:
            sku_id, qty, unit_price (optional), is_impulse, storage_type,
            unit_volume_L, category, priority

        Returns transaction dict if purchase made, None if empty-handed.
        """
        cal = self.world.get_calendar_day(day)
        business = self.world.businesses.get(business_id)
        if not business:
            return None

        # Step 1: Capacity constrain (storage limits)
        basket = capacity_constrain(basket_request, hh)

        # Step 2: Budget prune
        basket = budget_prune(basket, hh.budget_remaining_thb)

        # Step 3: Process each item against stock
        result_items = []
        total_value = 0.0
        total_cost = 0.0
        items_wanted = 0
        items_got = 0
        stockouts = 0
        budget_pruned_count = 0
        promo_responded = False
        noticed_promo = False

        for item in basket:
            sku_id = item["sku_id"]
            qty_wanted = item.get("qty", 0)
            if qty_wanted <= 0:
                if item.get("budget_pruned"):
                    budget_pruned_count += 1
                continue

            items_wanted += qty_wanted
            sku = self.world.skus.get(sku_id)
            if not sku:
                continue

            # Check stock
            shelf = self.get_shelf_stock(business_id, sku_id)
            unit_price = item.get("unit_price", sku.base_price_thb)
            unit_cost = sku.base_cost_thb

            # Check if promo active
            promo_applied = 0
            promo_discount = None
            for promo in business.active_promos:
                if promo.get("sku_id") == sku_id:
                    noticed_promo = True
                    discount = promo.get("discount_pct", 0)
                    unit_price = unit_price * (1.0 - discount / 100.0)
                    promo_applied = 1
                    promo_discount = discount
                    if item.get("responded_to_promo"):
                        promo_responded = True
                    break

            if shelf >= qty_wanted:
                # Full fill
                qty_sold = qty_wanted
                self.deduct_stock(business_id, sku_id, qty_sold)
                items_got += qty_sold
                result_items.append(self._make_basket_item(
                    sku_id=sku_id, qty_wanted=qty_wanted, qty_sold=qty_sold,
                    unit_price=unit_price, unit_cost=unit_cost,
                    promo_applied=promo_applied, promo_discount=promo_discount,
                ))
            elif shelf > 0:
                # Partial fill
                qty_sold = shelf
                self.deduct_stock(business_id, sku_id, qty_sold)
                items_got += qty_sold
                result_items.append(self._make_basket_item(
                    sku_id=sku_id, qty_wanted=qty_wanted, qty_sold=qty_sold,
                    unit_price=unit_price, unit_cost=unit_cost,
                    partial_fill=1, stockout_flag=1,
                    promo_applied=promo_applied, promo_discount=promo_discount,
                ))
                stockouts += 1
            else:
                # Out of stock — try substitution
                sub_sku = self._try_substitution(
                    sku_id, business_id, hh, unit_price
                )
                if sub_sku:
                    sub = self.world.skus[sub_sku]
                    sub_shelf = self.get_shelf_stock(business_id, sub_sku)
                    qty_sold = min(qty_wanted, sub_shelf)
                    self.deduct_stock(business_id, sub_sku, qty_sold)
                    items_got += qty_sold
                    result_items.append(self._make_basket_item(
                        sku_id=sub_sku, qty_wanted=qty_wanted, qty_sold=qty_sold,
                        unit_price=sub.base_price_thb, unit_cost=sub.base_cost_thb,
                        substitution=1, substituted_for_sku=sku_id,
                    ))
                else:
                    # Unresolved stockout
                    result_items.append(self._make_basket_item(
                        sku_id=sku_id, qty_wanted=qty_wanted, qty_sold=0,
                        unit_price=unit_price, unit_cost=unit_cost,
                        stockout_flag=1, unresolved_stockout=1,
                    ))
                    stockouts += 1

            line_val = result_items[-1]["qty_sold"] * result_items[-1]["unit_price_thb"]
            line_cost = result_items[-1]["qty_sold"] * result_items[-1]["unit_cost_thb"]
            result_items[-1]["line_value_thb"] = round(line_val, 2)
            total_value += line_val
            total_cost += line_cost

        # If nothing was actually sold, household leaves empty-handed
        if items_got == 0:
            return None

        # Compute satisfaction
        satisfaction, sat_score = compute_satisfaction(
            items_wanted, items_got, stockouts, budget_pruned_count, promo_responded
        )
        update_mood(hh, satisfaction)

        # Update household state
        hh.budget_remaining_thb -= total_value
        hh.last_visit_day = day
        hh.total_visits += 1
        hh.total_spend_thb += total_value
        if hh.first_visit_day is None:
            hh.first_visit_day = day

        # Replenish pantry
        replenish_items = []
        for ri in result_items:
            if ri["qty_sold"] > 0:
                sku = self.world.skus.get(ri["sku_id"])
                if sku:
                    replenish_items.append({
                        "storage_type": sku.storage_type,
                        "unit_volume_L": sku.unit_volume_L or 0.5,
                        "qty": ri["qty_sold"],
                    })
        replenish_pantry(hh, replenish_items)

        # Build transaction record
        txn_id = self.world.next_txn_id(hh.household_id, business_id)
        txn = {
            "transaction_id": txn_id,
            "business_id": business_id,
            "household_id": hh.household_id,
            "day": day,
            "day_of_week": cal.day_of_week,
            "week_of_month": cal.week_of_month,
            "is_payday_week": 1 if cal.is_payday_week else 0,
            "total_value_thb": round(total_value, 2),
            "total_cost_thb": round(total_cost, 2),
            "item_count": items_got,
            "satisfaction": satisfaction,
            "satisfaction_score": round(sat_score, 3),
            "visited_also": json.dumps(also_visited) if also_visited else None,
            "noticed_promotion": 1 if noticed_promo else 0,
            "responded_to_promotion": 1 if promo_responded else 0,
            "decision_type": decision_type,
            "llm_reasoning": llm_reasoning,
            "budget_at_visit_thb": round(hh.budget_remaining_thb + total_value, 2),
            "budget_pruned": 1 if budget_pruned_count > 0 else 0,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Write to DB
        self.db.insert("transactions", txn)

        # Write basket items
        for ri in result_items:
            ri["item_id"] = self.world.next_item_id(txn_id)
            ri["transaction_id"] = txn_id
            self.db.insert("basket_items", ri)

        # Log event
        self.world.add_event(
            EventType.PURCHASE.value, "household", hh.household_id,
            {"transaction_id": txn_id, "value": total_value, "items": items_got},
            target_type="store", target_id=business_id,
        )

        if stockouts > 0:
            self.world.add_event(
                EventType.STOCKOUT_HIT.value, "household", hh.household_id,
                {"stockouts": stockouts, "transaction_id": txn_id},
                target_type="store", target_id=business_id,
            )

        return txn

    def _make_basket_item(self, **kwargs) -> dict:
        """Create a basket_item dict with all required fields."""
        return {
            "item_id": "",  # filled later
            "transaction_id": "",  # filled later
            "sku_id": kwargs.get("sku_id", ""),
            "qty_wanted": kwargs.get("qty_wanted", 0),
            "qty_sold": kwargs.get("qty_sold", 0),
            "unit_price_thb": round(kwargs.get("unit_price", 0), 2),
            "unit_cost_thb": round(kwargs.get("unit_cost", 0), 2),
            "line_value_thb": 0.0,  # computed later
            "promo_applied": kwargs.get("promo_applied", 0),
            "promo_discount_pct": kwargs.get("promo_discount"),
            "stockout_flag": kwargs.get("stockout_flag", 0),
            "partial_fill": kwargs.get("partial_fill", 0),
            "substitution": kwargs.get("substitution", 0),
            "substituted_for_sku": kwargs.get("substituted_for_sku"),
            "unresolved_stockout": kwargs.get("unresolved_stockout", 0),
            "responded_to_promo": kwargs.get("responded_to_promo", 0),
            "budget_pruned": kwargs.get("budget_pruned", 0),
            "storage_blocked": kwargs.get("storage_blocked", 0),
        }

    def _try_substitution(
        self,
        original_sku_id: str,
        business_id: str,
        hh: HouseholdState,
        original_price: float,
    ) -> str | None:
        """
        Find a substitute for an OOS item. One level deep only.
        Returns substitute sku_id or None.
        """
        original = self.world.skus.get(original_sku_id)
        if not original:
            return None

        # Never substitute medicines or baby items
        if original.category in ("medicine", "baby", "device", "first_aid"):
            return None

        # High brand loyalty → less likely to substitute
        if hh.brand_loyalty > 0.7 and self.rng.random() > 0.3:
            return None
        elif hh.brand_loyalty > 0.3 and self.rng.random() > 0.6:
            return None

        # Find candidates: same category, similar price (±20%), in stock
        candidates = []
        for sku_id, sku in self.world.skus.items():
            if sku_id == original_sku_id:
                continue
            if sku.business_id != business_id:
                continue
            if sku.category != original.category:
                continue
            price_ratio = sku.base_price_thb / max(original_price, 0.01)
            if not (0.8 <= price_ratio <= 1.2):
                continue
            shelf = self.get_shelf_stock(business_id, sku_id)
            if shelf <= 0:
                continue
            candidates.append(sku_id)

        if candidates:
            return self.rng.choice(candidates)
        return None

    def build_rule_basket(
        self,
        hh: HouseholdState,
        business_id: str,
        day: int,
    ) -> list[dict]:
        """
        Generate a realistic basket. Target: 5-12 items, 150-500 THB per visit.
        Thai grocery shopping: rice, veg, meat, eggs, milk, snacks, drinks.
        """
        business = self.world.businesses.get(business_id)
        if not business:
            return []

        biz_skus = [s for s in self.world.skus.values()
                     if s.business_id == business_id]
        if not biz_skus:
            return []

        # For coffee shop: just 1-3 items
        if business.business_type == "food_beverage":
            self.rng.shuffle(biz_skus)
            n = self.rng.randint(1, 3)
            return [self._sku_to_basket_item(s, 1) for s in biz_skus[:n]]

        basket = []
        by_cat = {}
        for s in biz_skus:
            by_cat.setdefault(s.category, []).append(s)

        # Determine basket size based on household size and urgency
        base_items = 3 + hh.household_size  # 4-9 items base
        if hh.pantry_urgency > 0.7:
            base_items += self.rng.randint(2, 5)  # big shop when pantry is low
        elif hh.pantry_urgency > 0.4:
            base_items += self.rng.randint(1, 3)

        # Budget target: spend ~25-40% of weekly budget per visit
        target_spend = hh.budget_remaining_thb * self.rng.uniform(0.25, 0.45)

        # === CORE STAPLES (always buy some) ===
        # Fresh produce (2-4 items) — Thai cooking essential
        if "fresh_produce" in by_cat:
            n = self.rng.randint(2, min(4, len(by_cat["fresh_produce"])))
            picks = self.rng.sample(by_cat["fresh_produce"], n)
            for s in picks:
                basket.append(self._sku_to_basket_item(s, self.rng.randint(1, 2)))

        # Meat/protein (1-2 items)
        if "meat" in by_cat:
            n = self.rng.randint(1, min(2, len(by_cat["meat"])))
            picks = self.rng.sample(by_cat["meat"], n)
            for s in picks:
                basket.append(self._sku_to_basket_item(s, 1))

        # Dairy (1-2 items)
        if "dairy" in by_cat:
            n = self.rng.randint(1, min(2, len(by_cat["dairy"])))
            picks = self.rng.sample(by_cat["dairy"], n)
            for s in picks:
                basket.append(self._sku_to_basket_item(s, 1))

        # Dry goods (0-2 items — rice, noodles, oil, sauce)
        if "dry_goods" in by_cat and self.rng.random() < 0.6:
            n = self.rng.randint(1, min(2, len(by_cat["dry_goods"])))
            picks = self.rng.sample(by_cat["dry_goods"], n)
            for s in picks:
                basket.append(self._sku_to_basket_item(s, 1))

        # === REGULAR ADDITIONS ===
        # Beverages (very common — water, coffee, tea)
        if "beverage" in by_cat and self.rng.random() < 0.65:
            sku = self.rng.choice(by_cat["beverage"])
            basket.append(self._sku_to_basket_item(sku, 1))

        # Household items (20% chance per trip)
        if "household" in by_cat and self.rng.random() < 0.20:
            sku = self.rng.choice(by_cat["household"])
            basket.append(self._sku_to_basket_item(sku, 1))

        # Frozen (15% chance)
        if "frozen" in by_cat and self.rng.random() < 0.15:
            sku = self.rng.choice(by_cat["frozen"])
            basket.append(self._sku_to_basket_item(sku, 1))

        # === IMPULSE ===
        # Snacks (30-50% chance depending on income)
        impulse_prob = {"low": 0.25, "medium": 0.40, "high": 0.55}.get(hh.income_bracket, 0.35)
        if "snacks" in by_cat and self.rng.random() < impulse_prob:
            n = self.rng.randint(1, 2)
            picks = self.rng.sample(by_cat["snacks"], min(n, len(by_cat["snacks"])))
            for s in picks:
                basket.append(self._sku_to_basket_item(s, 1, impulse=True))

        # === LARGER HOUSEHOLDS buy more quantities ===
        if hh.household_size >= 4:
            for item in basket:
                if item["category"] in ("dairy", "fresh_produce", "meat") and self.rng.random() < 0.4:
                    item["qty"] = min(item["qty"] + 1, 3)

        return basket

    def _sku_to_basket_item(self, sku, qty, impulse=False):
        return {
            "sku_id": sku.sku_id,
            "qty": qty,
            "unit_price": sku.base_price_thb,
            "is_impulse": impulse or sku.is_impulse,
            "storage_type": sku.storage_type,
            "unit_volume_L": sku.unit_volume_L or 0.5,
            "category": sku.category,
            "priority": 10 if (impulse or sku.is_impulse) else 1,
        }

        return basket

    def write_stock_ledger_day(self, business_id: str, day: int) -> None:
        """
        Write end-of-day stock_ledger entries for all SKUs of a business.
        Must be called after all transactions for the day are processed.
        """
        biz_skus = [s for s in self.world.skus.values()
                     if s.business_id == business_id]

        # Get previous day's closing stock
        prev_rows = {
            r["sku_id"]: r
            for r in self.db.fetchall(
                "SELECT * FROM stock_ledger WHERE business_id = ? AND day = ?",
                (business_id, day - 1)
            )
        }

        for sku in biz_skus:
            prev = prev_rows.get(sku.sku_id)
            if prev:
                shelf_open = prev["shelf_close"]
                warehouse_open = prev["warehouse_close"]
            else:
                shelf_open = self.get_shelf_stock(business_id, sku.sku_id)
                warehouse_open = 0

            # Current shelf stock (after all transactions)
            shelf_current = self.get_shelf_stock(business_id, sku.sku_id)
            units_sold = max(0, shelf_open - shelf_current)

            # Morning restock from warehouse → shelf
            shelf_replenished = 0
            if shelf_current < 20 and warehouse_open > 0:
                restock = min(warehouse_open, 30)
                shelf_replenished = restock
                shelf_current += restock
                warehouse_open -= restock

            # Daily supplier delivery: auto-replenish warehouse when total stock is low
            # This simulates regular ordering — store keeps ~50-100 units per SKU
            units_delivered = 0
            target_stock = self.rng.randint(40, 80)  # target per SKU
            total_current = shelf_current + warehouse_open
            if total_current < target_stock:
                # Delivery arrives (with some randomness in fill)
                order_qty = target_stock - total_current + self.rng.randint(0, 15)
                # Supplier reliability: sometimes partial delivery
                fill = self.rng.uniform(0.75, 1.0)
                units_delivered = max(1, int(order_qty * fill))
                warehouse_open += units_delivered

            # Morning restock again after delivery
            if shelf_current < 15 and warehouse_open > 0:
                extra = min(warehouse_open, 20)
                shelf_replenished += extra
                shelf_current += extra
                warehouse_open -= extra

            # Expiry check (perishables only)
            units_expired = 0
            if sku.shelf_life_days and sku.shelf_life_days < 14:
                if self.rng.random() < 0.08:
                    expire_qty = self.rng.randint(1, 4)
                    expire_qty = min(expire_qty, shelf_current)
                    units_expired = expire_qty
                    shelf_current -= expire_qty

            shelf_close = max(0, shelf_current)
            warehouse_close = max(0, warehouse_open)
            stockout = 1 if shelf_close == 0 and units_sold > 0 else 0

            entry = {
                "ledger_id": f"STK_{sku.sku_id}_{day:+05d}",
                "business_id": business_id,
                "sku_id": sku.sku_id,
                "day": day,
                "shelf_open": shelf_open,
                "warehouse_open": prev["warehouse_close"] if prev else 0,
                "shelf_replenished": shelf_replenished,
                "units_sold": units_sold,
                "units_expired": units_expired,
                "units_shrinkage": 0,
                "units_delivered": 0,
                "shelf_close": shelf_close,
                "warehouse_close": warehouse_close,
                "total_stock_close": shelf_close + warehouse_close,
                "stockout_occurred": stockout,
                "near_expiry_flag": 0,
                "near_expiry_units": 0,
                "reorder_triggered": 1 if shelf_close + warehouse_close < 15 else 0,
            }
            self.db.upsert("stock_ledger", entry, "ledger_id")

            # Update stock cache
            self._stock_cache[(business_id, sku.sku_id)] = shelf_close

            # Waste event for expired items
            if units_expired > 0:
                self.db.insert("waste_events", {
                    "waste_id": f"WST_{sku.sku_id}_{day:+05d}",
                    "day": day,
                    "actor_type": "store",
                    "actor_id": business_id,
                    "sku_id": sku.sku_id,
                    "qty_wasted": units_expired,
                    "waste_reason": "store_expiry",
                    "estimated_cost_thb": round(units_expired * sku.base_cost_thb, 2),
                    "days_held_before_waste": sku.shelf_life_days,
                    "triggered_satisfaction_drop": 0,
                })

    def write_store_metrics_day(self, business_id: str, day: int) -> None:
        """Aggregate and write daily store_metrics for a business."""
        # Count transactions
        txn_stats = self.db.fetchone(
            """SELECT COUNT(DISTINCT transaction_id) AS txns,
                      COUNT(DISTINCT household_id) AS visitors,
                      COALESCE(SUM(total_value_thb), 0) AS revenue,
                      COALESCE(SUM(total_cost_thb), 0) AS cost,
                      AVG(total_value_thb) AS avg_basket,
                      AVG(item_count) AS avg_items
               FROM transactions
               WHERE business_id = ? AND day = ?""",
            (business_id, day)
        )

        # Stockout count
        stockout_row = self.db.fetchone(
            "SELECT COUNT(*) AS n FROM stock_ledger "
            "WHERE business_id = ? AND day = ? AND stockout_occurred = 1",
            (business_id, day)
        )

        # Waste value
        waste_row = self.db.fetchone(
            "SELECT COALESCE(SUM(estimated_cost_thb), 0) AS waste "
            "FROM waste_events WHERE actor_id = ? AND day = ?",
            (business_id, day)
        )

        total_hh = len(self.world.households)
        active_hh = len([h for h in self.world.households.values()
                         if h.is_active and h.last_visit_day is not None
                         and day - h.last_visit_day <= 30])

        self.db.insert("store_metrics", {
            "metric_id": f"MET_{business_id}_{day:+05d}",
            "business_id": business_id,
            "day": day,
            "unique_visitors": txn_stats["visitors"] if txn_stats else 0,
            "new_acquisitions": 0,  # computed by lifecycle scanner
            "active_customers_30d": active_hh,
            "retained_count": 0,
            "at_risk_count": 0,
            "churned_count": 0,
            "winback_sent_today": 0,
            "winback_accepted_today": 0,
            "gross_revenue_thb": round(txn_stats["revenue"], 2) if txn_stats else 0,
            "gross_margin_thb": round(
                (txn_stats["revenue"] or 0) - (txn_stats["cost"] or 0), 2
            ) if txn_stats else 0,
            "avg_basket_value_thb": round(txn_stats["avg_basket"], 2) if txn_stats and txn_stats["avg_basket"] else None,
            "avg_items_per_basket": round(txn_stats["avg_items"], 1) if txn_stats and txn_stats["avg_items"] else None,
            "stockout_incidents": stockout_row["n"] if stockout_row else 0,
            "stockout_rate": 0.0,
            "waste_value_thb": round(waste_row["waste"], 2) if waste_row else 0,
            "po_budget_remaining_thb": None,
            "village_total_households": total_hh,
            "village_active_households": active_hh,
        })
