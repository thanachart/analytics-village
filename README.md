# Analytics Village

A simulated village economy for learning real-world data analytics.

Each **challenge** is a standalone data analytics problem built from a shared village economy simulation. You'll explore transaction data, consult the simulated business owner, and submit a structured recommendation.

---

## Challenges

| ID | Title | Business | Tier | Type |
|----|-------|----------|------|------|
| [CH01](challenges/ch01/) | Open for Business | Village Fresh Supermarket | 1 | Reporting |

---

## Quick Start

Open the notebook for your challenge:

- **[CH01 — Open for Business](notebooks/ch01_open_for_business.ipynb)**

Or run locally:

```python
import sys; sys.path.insert(0, '.')
from student import Challenge, Decision

ch = Challenge.load('ch01', data_dir='challenges/ch01/data')

ch.brief()                # Read the challenge brief
ch.db.tables()            # See available data tables
ch.owner.questions()      # Ask the business owner questions
ch.db.daily_revenue()     # Pre-built revenue analysis
ch.db.customer_summary()  # Customer-level metrics
```

---

## How to Submit

1. Complete your analysis in the notebook
2. Build a `Decision` with your findings and recommendation
3. Validate: `d.validate()`
4. Export: `d.export(output_dir='submissions/ch01')`
5. Open a **Pull Request** to this repository

---

## Challenge Structure

```
challenges/ch01/
    data/village.db     SQLite database with simulation data
    brief.md            Challenge description
    schema.json         What fields your submission needs
    README.md           Challenge-specific instructions

student/                Python package (Challenge, Decision, Owner)
notebooks/              Guided analysis notebooks
submissions/            Submit your JSON here via PR
```

---

## What's in the Data?

Each challenge database (`village.db`) contains:

**Reference tables:**
- **households** — Customer profiles (size, income bracket, zone, dwelling type)
- **businesses** — Store names, types, locations
- **skus** — Product catalogue (name, category, price)
- **calendar_events** — Holidays, payday, weather with real dates

**Transaction tables:**
- **transactions** — Every purchase with date, value, satisfaction score
- **basket_items** — Line items per transaction (quantities, stockouts, substitutions)

**Operations:**
- **stock_ledger** — Daily inventory levels per SKU
- **store_metrics** — Daily KPIs (revenue, visitors, stockouts, waste)
- **waste_events** — Expired and damaged stock

**Customer:**
- **lifecycle_events** — State transitions (retained, at-risk, churned)
- **resident_days** — Daily household activity log
- **alt_transactions** — Purchases at competitor stores

Use `ch.db.tables()` to see all tables and `ch.db.query("SELECT ...")` to explore.

---

## Requirements

```
pandas
tabulate
```

No API keys needed. No LLM required. Everything runs locally.
