# Analytics Village

A simulated village economy for learning real-world data analytics.

Each **challenge** is a standalone data analytics problem built from a shared village economy simulation. You'll explore transaction data, consult the simulated business owner, and submit a structured recommendation.

---

## Challenges

| ID | Title | Business | Tier | Type |
|----|-------|----------|------|------|
| [CH01](episodes/ep01/) | Open for Business | Village Fresh Supermarket | 1 | Reporting |

---

## Quick Start

Open the notebook for your challenge:

- **[CH01 — Open for Business](notebooks/ep01_open_for_business.ipynb)**

Or run locally:

```python
import sys; sys.path.insert(0, '.')
from student import Episode, Decision

ep = Episode.load('ep01', data_dir='episodes/ep01/data')

ep.brief()                # Read the challenge brief
ep.db.tables()            # See available data tables
ep.owner.questions()      # Ask the business owner questions
ep.db.daily_revenue()     # Pre-built revenue analysis
ep.db.customer_summary()  # Customer-level metrics
```

---

## How to Submit

1. Complete your analysis in the notebook
2. Build a `Decision` with your findings and recommendation
3. Validate: `d.validate()`
4. Export: `d.export(output_dir='submissions/ep01')`
5. Open a **Pull Request** to this repository

---

## Challenge Structure

```
episodes/ep01/
    data/village.db     SQLite database with simulation data
    brief.md            Challenge description
    schema.json         What fields your submission needs
    README.md           Challenge-specific instructions

student/                Python package (Episode, Decision, Owner)
notebooks/              Guided analysis notebooks
submissions/            Submit your JSON here via PR
```

---

## What's in the Data?

Each challenge database contains realistic simulated data including:

- **transactions** — Every purchase (customer, items, value, satisfaction)
- **basket_items** — Line items per transaction (stockouts, substitutions)
- **households** — Customer profiles (income, size, persona weights)
- **stock_ledger** — Daily inventory levels per product
- **lifecycle_events** — Customer state transitions (retained, at-risk, churned)
- **store_metrics** — Daily KPIs (revenue, visitors, stockouts, waste)
- **skus** — Product catalogue with Thai pricing

Use `ep.db.tables()` to see all available tables and `ep.db.query("SELECT ...")` to explore.

---

## Requirements

```
pandas
tabulate
```

No API keys needed. No LLM required. Everything runs locally.
