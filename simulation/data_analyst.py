"""
Analytics Village — LLM Data Analyst.
Validates generated data for realism and generates key findings.
Uses Ollama to analyze simulation output.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .database import VillageDB
    from .llm_client import OllamaClient

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════
# Data Quality Checks (rule-based, no LLM needed)
# ══════════════════════════════════════════════════════════════

QUALITY_THRESHOLDS = {
    "min_transactions_per_day": 10,
    "max_transactions_per_day": 500,
    "min_avg_basket_thb": 100,
    "max_avg_basket_thb": 800,
    "min_days_with_txns_pct": 0.85,   # at least 85% of days should have transactions
    "max_churn_rate": 0.25,            # no more than 25% churned
    "min_unique_customers_pct": 0.30,  # at least 30% of HH should have visited
    "max_stockout_rate": 0.15,         # no more than 15% stockout rate
    "min_revenue_cv": 0.05,            # revenue should have some variance (not flat)
    "max_revenue_cv": 1.5,             # but not wildly volatile
    "min_categories_sold": 4,          # at least 4 product categories moving
}


def validate_data_quality(db: VillageDB) -> dict:
    """
    Run rule-based quality checks on generated data.
    Returns {passed: bool, checks: [{name, passed, value, threshold, message}]}
    """
    checks = []

    # 1. Transaction volume
    txn_stats = db.fetchone(
        "SELECT COUNT(*) AS n, COUNT(DISTINCT day) AS days FROM transactions"
    )
    total_txns = txn_stats["n"] if txn_stats else 0
    days_with_txns = txn_stats["days"] if txn_stats else 0

    total_days = db.fetchone(
        "SELECT COUNT(DISTINCT day) AS n FROM resident_days"
    )
    sim_days = total_days["n"] if total_days else 1

    txns_per_day = total_txns / max(sim_days, 1)
    checks.append(_check("txns_per_day", txns_per_day,
                          QUALITY_THRESHOLDS["min_transactions_per_day"],
                          QUALITY_THRESHOLDS["max_transactions_per_day"],
                          f"Avg {txns_per_day:.1f} txns/day"))

    # 2. Days coverage
    days_pct = days_with_txns / max(sim_days, 1)
    checks.append(_check_min("days_coverage", days_pct,
                              QUALITY_THRESHOLDS["min_days_with_txns_pct"],
                              f"{days_with_txns}/{sim_days} days have transactions ({days_pct:.0%})"))

    # 3. Avg basket
    basket = db.fetchone("SELECT AVG(total_value_thb) AS avg FROM transactions")
    avg_basket = basket["avg"] if basket and basket["avg"] else 0
    checks.append(_check("avg_basket", avg_basket,
                          QUALITY_THRESHOLDS["min_avg_basket_thb"],
                          QUALITY_THRESHOLDS["max_avg_basket_thb"],
                          f"Avg basket: {avg_basket:.0f} THB"))

    # 4. Unique customers
    cust = db.fetchone("SELECT COUNT(DISTINCT household_id) AS n FROM transactions")
    total_hh = db.fetchone("SELECT COUNT(*) AS n FROM households")
    cust_pct = (cust["n"] if cust else 0) / max(total_hh["n"] if total_hh else 1, 1)
    checks.append(_check_min("customer_coverage", cust_pct,
                              QUALITY_THRESHOLDS["min_unique_customers_pct"],
                              f"{cust['n'] if cust else 0}/{total_hh['n'] if total_hh else 0} households shopped ({cust_pct:.0%})"))

    # 5. Churn rate
    churned = db.fetchone(
        "SELECT COUNT(DISTINCT household_id) AS n FROM lifecycle_events WHERE to_state = 'churned'"
    )
    churn_rate = (churned["n"] if churned else 0) / max(total_hh["n"] if total_hh else 1, 1)
    checks.append(_check_max("churn_rate", churn_rate,
                              QUALITY_THRESHOLDS["max_churn_rate"],
                              f"Churn rate: {churn_rate:.1%}"))

    # 6. Revenue variance (not flat, not wild)
    rev_stats = db.fetchone(
        "SELECT AVG(rev) AS mean, "
        "CASE WHEN AVG(rev) > 0 THEN (SUM((rev - avg_rev) * (rev - avg_rev)) / COUNT(*)) END AS var "
        "FROM (SELECT day, SUM(total_value_thb) AS rev FROM transactions GROUP BY day) t, "
        "(SELECT AVG(total_value_thb_sum) AS avg_rev FROM "
        "(SELECT SUM(total_value_thb) AS total_value_thb_sum FROM transactions GROUP BY day)) a"
    )
    # Simpler approach
    daily_revs = db.fetchall(
        "SELECT SUM(total_value_thb) AS rev FROM transactions GROUP BY day"
    )
    if daily_revs and len(daily_revs) > 1:
        revs = [r["rev"] for r in daily_revs]
        mean_rev = sum(revs) / len(revs)
        if mean_rev > 0:
            import math
            variance = sum((r - mean_rev) ** 2 for r in revs) / len(revs)
            cv = math.sqrt(variance) / mean_rev
            checks.append(_check("revenue_cv", cv,
                                  QUALITY_THRESHOLDS["min_revenue_cv"],
                                  QUALITY_THRESHOLDS["max_revenue_cv"],
                                  f"Revenue CV: {cv:.2f} (variation is {'good' if 0.05 < cv < 1.0 else 'concerning'})"))

    # 7. Product diversity
    cats = db.fetchone(
        "SELECT COUNT(DISTINCT s.category) AS n "
        "FROM basket_items bi JOIN skus s ON bi.sku_id = s.sku_id WHERE bi.qty_sold > 0"
    )
    n_cats = cats["n"] if cats else 0
    checks.append(_check_min("category_diversity", n_cats,
                              QUALITY_THRESHOLDS["min_categories_sold"],
                              f"{n_cats} product categories sold"))

    # 8. Day-of-week pattern (weekend should be higher)
    dow = db.fetchall(
        "SELECT day_of_week, SUM(total_value_thb) AS rev "
        "FROM transactions GROUP BY day_of_week"
    )
    if dow:
        dow_map = {r["day_of_week"]: r["rev"] for r in dow}
        weekend = (dow_map.get("saturday", 0) + dow_map.get("sunday", 0)) / 2
        weekday = sum(dow_map.get(d, 0) for d in ["monday", "tuesday", "wednesday", "thursday"]) / 4
        if weekday > 0:
            ratio = weekend / weekday
            checks.append(_check("weekend_uplift", ratio, 0.9, 2.0,
                                  f"Weekend/weekday ratio: {ratio:.2f}x"))

    all_passed = all(c["passed"] for c in checks)
    return {
        "passed": all_passed,
        "checks": checks,
        "summary": f"{'All checks passed' if all_passed else 'Some checks failed'} ({sum(1 for c in checks if c['passed'])}/{len(checks)})",
    }


def _check(name, value, min_v, max_v, msg):
    passed = min_v <= value <= max_v
    return {"name": name, "passed": passed, "value": round(value, 3),
            "range": f"{min_v}-{max_v}", "message": msg}

def _check_min(name, value, min_v, msg):
    return {"name": name, "passed": value >= min_v, "value": round(value, 3),
            "range": f">={min_v}", "message": msg}

def _check_max(name, value, max_v, msg):
    return {"name": name, "passed": value <= max_v, "value": round(value, 3),
            "range": f"<={max_v}", "message": msg}


# ══════════════════════════════════════════════════════════════
# LLM Key Findings Generator
# ══════════════════════════════════════════════════════════════


def compute_data_summary(db: VillageDB) -> str:
    """Build a text summary of the generated data for LLM analysis."""
    lines = []

    # Basic stats
    txn = db.fetchone("SELECT COUNT(*) AS n, SUM(total_value_thb) AS rev, AVG(total_value_thb) AS avg FROM transactions")
    hh = db.fetchone("SELECT COUNT(*) AS n FROM households")
    days = db.fetchone("SELECT MIN(day) AS mn, MAX(day) AS mx, COUNT(DISTINCT day) AS n FROM transactions")
    lines.append(f"TRANSACTIONS: {txn['n']:,} total, {txn['rev']:,.0f} THB revenue, {txn['avg']:.0f} THB avg basket")
    lines.append(f"HOUSEHOLDS: {hh['n']}")
    lines.append(f"PERIOD: day {days['mn']} to {days['mx']} ({days['n']} active days)")

    # Revenue by day of week
    dow = db.fetchall("SELECT day_of_week, COUNT(*) AS txns, SUM(total_value_thb) AS rev FROM transactions GROUP BY day_of_week")
    lines.append("\nREVENUE BY DAY OF WEEK:")
    for r in dow:
        lines.append(f"  {r['day_of_week']:12s}: {r['txns']:5d} txns, {r['rev']:10,.0f} THB")

    # Top 10 SKUs
    top_skus = db.fetchall(
        "SELECT s.sku_name, SUM(bi.line_value_thb) AS rev, SUM(bi.qty_sold) AS qty "
        "FROM basket_items bi JOIN skus s ON bi.sku_id = s.sku_id "
        "GROUP BY s.sku_name ORDER BY rev DESC LIMIT 10"
    )
    lines.append("\nTOP 10 PRODUCTS:")
    for r in top_skus:
        lines.append(f"  {r['sku_name']:30s}: {r['rev']:10,.0f} THB ({r['qty']:,} units)")

    # Customer segments
    segments = db.fetchall(
        "SELECT income_bracket, COUNT(*) AS n, "
        "AVG(t.total_spend) AS avg_spend FROM households h "
        "LEFT JOIN (SELECT household_id, SUM(total_value_thb) AS total_spend FROM transactions GROUP BY household_id) t "
        "ON h.household_id = t.household_id GROUP BY income_bracket"
    )
    lines.append("\nCUSTOMER SEGMENTS:")
    for r in segments:
        lines.append(f"  {r['income_bracket']:10s}: {r['n']:3d} HH, avg spend {r['avg_spend'] or 0:,.0f} THB")

    # Lifecycle
    lc = db.fetchall(
        "SELECT to_state, COUNT(*) AS n FROM lifecycle_events GROUP BY to_state ORDER BY n DESC"
    )
    if lc:
        lines.append("\nLIFECYCLE TRANSITIONS:")
        for r in lc:
            lines.append(f"  -> {r['to_state']:20s}: {r['n']:4d}")

    # Stockouts
    so = db.fetchall(
        "SELECT s.sku_name, COUNT(*) AS events, SUM(bi.qty_wanted - bi.qty_sold) AS lost "
        "FROM basket_items bi JOIN skus s ON bi.sku_id = s.sku_id "
        "WHERE bi.stockout_flag = 1 GROUP BY s.sku_name ORDER BY lost DESC LIMIT 5"
    )
    if so:
        lines.append("\nTOP STOCKOUT ITEMS:")
        for r in so:
            lines.append(f"  {r['sku_name']:30s}: {r['events']} events, {r['lost']} units lost")

    # Satisfaction
    sat = db.fetchall("SELECT satisfaction, COUNT(*) AS n FROM transactions GROUP BY satisfaction")
    if sat:
        lines.append("\nSATISFACTION:")
        for r in sat:
            lines.append(f"  {r['satisfaction']:12s}: {r['n']:5d}")

    return "\n".join(lines)


async def generate_key_findings(
    llm: OllamaClient,
    db: VillageDB,
    seed_findings: str | None = None,
) -> list[dict]:
    """
    Use LLM to analyze the generated data and produce key findings.
    Returns list of {title, description, evidence, severity, category}.
    """
    summary = compute_data_summary(db)

    system = """You are a senior data analyst reviewing a simulated village economy dataset.
Analyze the data summary below and identify 5-8 key findings that would be interesting for students to discover.
Each finding should be:
- Specific and quantified (reference actual numbers from the data)
- Actionable (suggests what a business owner could do)
- Varied in difficulty (some obvious, some requiring deeper analysis)

Always respond with valid JSON only. No markdown, no prose."""

    seed_context = ""
    if seed_findings:
        seed_context = f"\n\nThe instructor wants these themes explored:\n{seed_findings}\n\nIncorporate these themes into your findings where the data supports them."

    user_prompt = f"""DATA SUMMARY:
{summary}
{seed_context}

Generate 5-8 key findings as JSON:
{{
  "findings": [
    {{
      "title": "Short finding headline",
      "description": "2-3 sentence explanation of the finding and its implications",
      "evidence": "Specific data points that support this finding",
      "severity": "high/medium/low",
      "category": "revenue/customers/operations/products/lifecycle"
    }}
  ],
  "data_quality_notes": "Any concerns about the data realism (empty string if data looks good)"
}}"""

    result = await llm.complete_json(system, user_prompt, temperature=0.5, max_tokens=1500)

    if result and isinstance(result, dict):
        findings = result.get("findings", [])
        quality_note = result.get("data_quality_notes", "")
        if quality_note:
            logger.info(f"LLM data quality note: {quality_note}")
        return findings

    return []


def generate_key_findings_sync(
    llm: OllamaClient,
    db: VillageDB,
    seed_findings: str | None = None,
) -> list[dict]:
    """Synchronous wrapper."""
    import asyncio
    return asyncio.run(generate_key_findings(llm, db, seed_findings))
