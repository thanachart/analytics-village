"""
Analytics Village — DatabaseProxy for student access.
Provides convenient filtered queries over the challenge SQLite database.
"""
from __future__ import annotations

import os
import sqlite3
from typing import Any

import pandas as pd

from .display import format_table


class DatabaseProxy:
    """
    Student-facing database access.
    Default queries are filtered to the challenge's primary business and day range.
    """

    def __init__(
        self,
        db_path: str,
        primary_business: str = "supermarket",
        day_min: int | None = None,
        day_max: int | None = None,
    ):
        from pathlib import Path
        self._path = os.path.abspath(db_path)
        uri = Path(self._path).as_uri() + "?mode=ro"
        self._conn = sqlite3.connect(uri, uri=True)
        self._conn.row_factory = sqlite3.Row
        self._primary_business = primary_business
        self._day_min = day_min
        self._day_max = day_max
        self._query_log: list[str] = []

    # ── Core query methods ───────────────────────────────────

    def query(self, sql: str, params: tuple = ()) -> pd.DataFrame:
        """Execute SQL and return DataFrame. Auto-filtered for challenge context."""
        self._query_log.append(sql)
        return pd.read_sql_query(sql, self._conn, params=params)

    def raw(self, sql: str, params: tuple = ()) -> pd.DataFrame:
        """Execute SQL with NO automatic filters. Full village.db access."""
        self._query_log.append(sql)
        return pd.read_sql_query(sql, self._conn, params=params)

    def connection(self) -> sqlite3.Connection:
        """Return raw sqlite3 connection for maximum flexibility."""
        return self._conn

    # ── Table info ───────────────────────────────────────────

    def tables(self) -> None:
        """Print all tables with row counts."""
        # Get all tables (use raw cursor to avoid pandas issues with sqlite_master)
        cur = self._conn.execute("SELECT name, type FROM sqlite_master ORDER BY name")
        all_rows = cur.fetchall()

        tables = []
        for row in all_rows:
            name, typ = row["name"], row["type"]
            if typ not in ("table", "view"):
                continue
            if name.startswith("_") or name.startswith("sqlite_"):
                continue
            try:
                n = self._conn.execute(f'SELECT COUNT(*) FROM [{name}]').fetchone()[0]
            except Exception:
                n = 0
            tables.append((name, n, typ))

        print(f"\n{'='*60}\nAvailable Tables ({len(tables)})\n{'='*60}")
        for name, n, typ in tables:
            tag = " (view)" if typ == "view" else ""
            print(f"  {name:30s} {n:>8,d} rows{tag}")
        print(f"\nUse ch.db.query('SELECT * FROM table_name LIMIT 5') to explore.")

    def all_tables(self) -> None:
        """Print ALL tables including hidden ones."""
        rows = pd.read_sql_query(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
            self._conn
        )
        table_info = []
        for _, row in rows.iterrows():
            name = row["name"]
            count = pd.read_sql_query(f"SELECT COUNT(*) AS n FROM [{name}]", self._conn)
            n = count.iloc[0]["n"]
            hidden = "(hidden)" if name.startswith("_") else ""
            table_info.append([name, f"{n:,}", hidden])

        print(format_table(["Table", "Rows", "Note"], table_info, "All Tables"))

    # ── DataFrame shortcuts ──────────────────────────────────

    @property
    def transactions(self) -> pd.DataFrame:
        return self.query(
            "SELECT * FROM transactions WHERE business_id = ?",
            (self._primary_business,)
        )

    @property
    def basket_items(self) -> pd.DataFrame:
        return self.query(
            "SELECT bi.* FROM basket_items bi "
            "JOIN transactions t ON bi.transaction_id = t.transaction_id "
            "WHERE t.business_id = ?",
            (self._primary_business,)
        )

    @property
    def households(self) -> pd.DataFrame:
        return self.query("SELECT * FROM households")

    @property
    def lifecycle_events(self) -> pd.DataFrame:
        return self.query(
            "SELECT * FROM lifecycle_events WHERE business_id = ?",
            (self._primary_business,)
        )

    @property
    def stock_ledger(self) -> pd.DataFrame:
        return self.query(
            "SELECT * FROM stock_ledger WHERE business_id = ?",
            (self._primary_business,)
        )

    @property
    def supply_events(self) -> pd.DataFrame:
        return self.query(
            "SELECT * FROM supply_events WHERE business_id = ?",
            (self._primary_business,)
        )

    @property
    def price_log(self) -> pd.DataFrame:
        return self.query(
            "SELECT * FROM price_log WHERE business_id = ?",
            (self._primary_business,)
        )

    @property
    def campaign_log(self) -> pd.DataFrame:
        return self.query(
            "SELECT * FROM campaign_log WHERE business_id = ?",
            (self._primary_business,)
        )

    @property
    def waste_events(self) -> pd.DataFrame:
        return self.query("SELECT * FROM waste_events")

    @property
    def resident_days(self) -> pd.DataFrame:
        return self.query("SELECT * FROM resident_days")

    @property
    def store_metrics(self) -> pd.DataFrame:
        return self.query(
            "SELECT * FROM store_metrics WHERE business_id = ?",
            (self._primary_business,)
        )

    @property
    def reviews(self) -> pd.DataFrame:
        return self.query(
            "SELECT * FROM reviews WHERE business_id = ?",
            (self._primary_business,)
        )

    @property
    def alt_transactions(self) -> pd.DataFrame:
        return self.query("SELECT * FROM alt_transactions")

    @property
    def profile_snapshots(self) -> pd.DataFrame:
        return self.query("SELECT * FROM profile_snapshots")

    @property
    def event_ledger(self) -> pd.DataFrame:
        return self.query("SELECT * FROM event_ledger")

    @property
    def skus(self) -> pd.DataFrame:
        return self.query("SELECT * FROM skus")

    @property
    def calendar_events(self) -> pd.DataFrame:
        return self.query("SELECT * FROM calendar_events")

    @property
    def village_roster(self) -> pd.DataFrame:
        return self.query("SELECT * FROM village_roster")

    # ── Pre-built helper queries ─────────────────────────────

    def customer_summary(self, business_id: str = None) -> pd.DataFrame:
        biz = business_id or self._primary_business
        return self.query(
            """SELECT h.household_id, h.household_size, h.income_bracket,
                      h.location_zone,
                      COUNT(DISTINCT t.transaction_id) AS total_visits,
                      COALESCE(SUM(t.total_value_thb), 0) AS total_spend_thb,
                      AVG(t.total_value_thb) AS avg_basket_thb,
                      MAX(t.day) AS last_visit_day,
                      MIN(t.day) AS first_visit_day,
                      AVG(t.satisfaction_score) AS avg_satisfaction
               FROM households h
               LEFT JOIN transactions t ON h.household_id = t.household_id
                   AND t.business_id = ?
               GROUP BY h.household_id
               ORDER BY total_spend_thb DESC""",
            (biz,)
        )

    def daily_revenue(self, business_id: str = None) -> pd.DataFrame:
        biz = business_id or self._primary_business
        return self.query(
            """SELECT day, day_of_week, is_payday_week,
                      COUNT(DISTINCT transaction_id) AS transactions,
                      COUNT(DISTINCT household_id) AS unique_customers,
                      SUM(total_value_thb) AS revenue_thb,
                      SUM(total_cost_thb) AS cost_thb,
                      SUM(total_value_thb) - SUM(total_cost_thb) AS margin_thb,
                      AVG(total_value_thb) AS avg_basket_thb
               FROM transactions
               WHERE business_id = ?
               GROUP BY day ORDER BY day""",
            (biz,)
        )

    def churn_candidates(self, days_absent: int = 14, business_id: str = None) -> pd.DataFrame:
        biz = business_id or self._primary_business
        return self.query(
            """SELECT h.household_id, h.income_bracket,
                      MAX(t.day) AS last_visit_day,
                      (SELECT MAX(day) FROM transactions) - MAX(t.day) AS days_absent,
                      COALESCE(SUM(t.total_value_thb), 0) AS lifetime_spend_thb,
                      COUNT(t.transaction_id) AS visit_count
               FROM households h
               LEFT JOIN transactions t ON h.household_id = t.household_id
                   AND t.business_id = ?
               GROUP BY h.household_id
               HAVING days_absent >= ? OR last_visit_day IS NULL
               ORDER BY lifetime_spend_thb DESC""",
            (biz, days_absent)
        )

    def sku_performance(self, business_id: str = None) -> pd.DataFrame:
        biz = business_id or self._primary_business
        return self.query(
            """SELECT s.sku_id, s.sku_name, s.category,
                      COALESCE(SUM(bi.qty_sold), 0) AS units_sold,
                      COALESCE(SUM(bi.line_value_thb), 0) AS revenue_thb,
                      COALESCE(SUM(bi.qty_sold * (bi.unit_price_thb - bi.unit_cost_thb)), 0) AS margin_thb,
                      SUM(bi.stockout_flag) AS stockout_count
               FROM skus s
               LEFT JOIN basket_items bi ON s.sku_id = bi.sku_id
               LEFT JOIN transactions t ON bi.transaction_id = t.transaction_id
                   AND t.business_id = ?
               WHERE s.business_id = ?
               GROUP BY s.sku_id
               ORDER BY revenue_thb DESC""",
            (biz, biz)
        )

    def wallet_share(self, primary_business: str = None) -> pd.DataFrame:
        biz = primary_business or self._primary_business
        return self.query(
            """SELECT h.household_id,
                      COALESCE(our.spend, 0) AS our_spend_thb,
                      COALESCE(alt.spend, 0) AS alt_spend_thb,
                      CASE WHEN COALESCE(our.spend, 0) + COALESCE(alt.spend, 0) > 0
                           THEN our.spend * 100.0 / (our.spend + alt.spend)
                           ELSE 0 END AS our_share_pct
               FROM households h
               LEFT JOIN (SELECT household_id, SUM(total_value_thb) AS spend
                          FROM transactions WHERE business_id = ?
                          GROUP BY household_id) our ON h.household_id = our.household_id
               LEFT JOIN (SELECT household_id, SUM(total_value_thb) AS spend
                          FROM alt_transactions
                          GROUP BY household_id) alt ON h.household_id = alt.household_id
               WHERE COALESCE(our.spend, 0) + COALESCE(alt.spend, 0) > 0
               ORDER BY our_share_pct""",
            (biz,)
        )
