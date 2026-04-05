"""Analytics Village — Data exploration routes for the UI."""
from __future__ import annotations

import json
import os

from fastapi import APIRouter, HTTPException, Query

from .facilitator_db import FacilitatorDB

router = APIRouter(prefix="/api/data", tags=["data"])


def _get_village_db(episode_id: str = None):
    """Find and open the village.db for an episode."""
    from simulation.database import VillageDB

    fdb = FacilitatorDB("facilitator.db")
    if episode_id:
        ep = fdb.get_episode(episode_id)
    else:
        eps = fdb.list_episodes()
        ep = eps[0] if eps else None
    fdb.close()

    if not ep:
        raise HTTPException(404, "No episode found")

    db_path = ep.get("village_db_path")
    if not db_path or not os.path.exists(db_path):
        # Try data/ directory
        eid = ep["episode_id"]
        alt_paths = [
            f"data/{eid}/village.db",
            f"data/{eid}/{eid}_village.db",
            f"output/{eid}/{eid}_village.db",
        ]
        for p in alt_paths:
            if os.path.exists(p):
                db_path = p
                break
        if not db_path or not os.path.exists(db_path):
            raise HTTPException(404, f"Village DB not found for {eid}")

    return VillageDB(db_path, read_only=True), ep


@router.get("/daily-revenue")
def daily_revenue(episode_id: str = None, business_id: str = "supermarket"):
    """Daily revenue time series for charts."""
    db, ep = _get_village_db(episode_id)
    try:
        rows = db.fetchall(
            """SELECT day, day_of_week, is_payday_week,
                      COUNT(DISTINCT transaction_id) AS transactions,
                      COUNT(DISTINCT household_id) AS unique_customers,
                      COALESCE(SUM(total_value_thb), 0) AS revenue,
                      COALESCE(AVG(total_value_thb), 0) AS avg_basket
               FROM transactions
               WHERE business_id = ?
               GROUP BY day ORDER BY day""",
            (business_id,)
        )
        return rows
    finally:
        db.close()


@router.get("/customer-summary")
def customer_summary(episode_id: str = None, business_id: str = "supermarket"):
    """Customer-level aggregated metrics."""
    db, ep = _get_village_db(episode_id)
    try:
        rows = db.fetchall(
            """SELECT h.household_id, h.household_size, h.income_bracket,
                      h.location_zone,
                      COUNT(DISTINCT t.transaction_id) AS total_visits,
                      COALESCE(SUM(t.total_value_thb), 0) AS total_spend,
                      COALESCE(AVG(t.total_value_thb), 0) AS avg_basket,
                      MAX(t.day) AS last_visit_day,
                      MIN(t.day) AS first_visit_day,
                      COALESCE(AVG(t.satisfaction_score), 0) AS avg_satisfaction
               FROM households h
               LEFT JOIN transactions t ON h.household_id = t.household_id
                   AND t.business_id = ?
               GROUP BY h.household_id
               ORDER BY total_spend DESC""",
            (business_id,)
        )
        return rows
    finally:
        db.close()


@router.get("/top-skus")
def top_skus(episode_id: str = None, business_id: str = "supermarket", limit: int = 15):
    """Top SKUs by revenue."""
    db, ep = _get_village_db(episode_id)
    try:
        rows = db.fetchall(
            """SELECT s.sku_id, s.sku_name, s.category,
                      COALESCE(SUM(bi.qty_sold), 0) AS units_sold,
                      COALESCE(SUM(bi.line_value_thb), 0) AS revenue,
                      SUM(bi.stockout_flag) AS stockouts
               FROM skus s
               LEFT JOIN basket_items bi ON s.sku_id = bi.sku_id
               LEFT JOIN transactions t ON bi.transaction_id = t.transaction_id
                   AND t.business_id = ?
               WHERE s.business_id = ?
               GROUP BY s.sku_id
               ORDER BY revenue DESC
               LIMIT ?""",
            (business_id, business_id, limit)
        )
        return rows
    finally:
        db.close()


@router.get("/lifecycle-summary")
def lifecycle_summary(episode_id: str = None, business_id: str = "supermarket"):
    """Lifecycle state distribution and recent transitions."""
    db, ep = _get_village_db(episode_id)
    try:
        # Current state counts from latest resident_days
        max_day = db.fetchone("SELECT MAX(day) AS d FROM resident_days")
        day = max_day["d"] if max_day and max_day["d"] is not None else 0

        states = db.fetchall(
            """SELECT lifecycle_state, COUNT(*) AS count
               FROM resident_days
               WHERE day = ?
               GROUP BY lifecycle_state""",
            (day,)
        )

        # Recent transitions
        transitions = db.fetchall(
            """SELECT from_state, to_state, trigger_type, COUNT(*) AS count
               FROM lifecycle_events
               WHERE business_id = ?
               GROUP BY from_state, to_state, trigger_type
               ORDER BY count DESC
               LIMIT 10""",
            (business_id,)
        )

        return {"day": day, "states": states, "transitions": transitions}
    finally:
        db.close()


@router.get("/stockout-impact")
def stockout_impact(episode_id: str = None, business_id: str = "supermarket"):
    """SKUs with most stockout impact."""
    db, ep = _get_village_db(episode_id)
    try:
        rows = db.fetchall(
            """SELECT bi.sku_id, s.sku_name,
                      COUNT(*) AS stockout_events,
                      SUM(bi.qty_wanted - bi.qty_sold) AS units_lost,
                      SUM((bi.qty_wanted - bi.qty_sold) * bi.unit_price_thb) AS revenue_lost,
                      COUNT(DISTINCT bi.transaction_id) AS customers_affected
               FROM basket_items bi
               JOIN skus s ON bi.sku_id = s.sku_id
               WHERE bi.stockout_flag = 1
               GROUP BY bi.sku_id
               ORDER BY revenue_lost DESC
               LIMIT 10""",
        )
        return rows
    finally:
        db.close()


@router.get("/day-of-week")
def day_of_week_analysis(episode_id: str = None, business_id: str = "supermarket"):
    """Revenue and traffic by day of week."""
    db, ep = _get_village_db(episode_id)
    try:
        rows = db.fetchall(
            """SELECT day_of_week,
                      COUNT(DISTINCT transaction_id) AS transactions,
                      COALESCE(SUM(total_value_thb), 0) AS revenue,
                      COALESCE(AVG(total_value_thb), 0) AS avg_basket,
                      COUNT(DISTINCT household_id) AS unique_customers
               FROM transactions
               WHERE business_id = ?
               GROUP BY day_of_week""",
            (business_id,)
        )
        # Sort by proper day order
        day_order = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                     'friday': 4, 'saturday': 5, 'sunday': 6}
        rows.sort(key=lambda r: day_order.get(r['day_of_week'], 7))
        return rows
    finally:
        db.close()


@router.get("/table-preview/{table_name}")
def table_preview(table_name: str, episode_id: str = None, limit: int = 50):
    """Preview rows from any table."""
    # Whitelist tables
    allowed = [
        "transactions", "basket_items", "households", "skus", "stock_ledger",
        "supply_events", "suppliers", "price_log", "campaign_log", "waste_events",
        "capacity_log", "store_metrics", "reviews", "alt_transactions",
        "profile_snapshots", "village_roster", "event_ledger", "calendar_events",
        "resident_days", "lifecycle_events", "businesses", "owners",
    ]
    if table_name not in allowed:
        raise HTTPException(400, f"Table '{table_name}' not available for preview")

    db, ep = _get_village_db(episode_id)
    try:
        rows = db.fetchall(f"SELECT * FROM [{table_name}] LIMIT ?", (limit,))
        count = db.count(table_name)
        return {"table": table_name, "total_rows": count, "rows": rows}
    finally:
        db.close()


@router.get("/tables")
def list_tables(episode_id: str = None):
    """List all tables with row counts."""
    db, ep = _get_village_db(episode_id)
    try:
        tables = db.table_row_counts(include_hidden=False)
        return [{"name": k, "rows": v} for k, v in sorted(tables.items())]
    finally:
        db.close()
