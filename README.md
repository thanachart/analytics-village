# Analytics Village

A simulated village economy for learning real-world data analytics.

Each **challenge** provides two database formats — choose the one that fits your learning goal.

---

## Challenges

| ID | Title | Business | Tier | Type |
|----|-------|----------|------|------|
| [CH01](challenges/ch01/) | Open for Business | Village Fresh Supermarket | 1 | Reporting |

---

## Two Database Formats

Each challenge comes with **two SQLite databases** containing the same data in different structures:

### `village_normalized.db` — ERP/CRM Style (practice joins & data prep)
| Table | Description |
|-------|-------------|
| `customers` | Customer profiles (size, income, zone) |
| `products` | Product catalogue (name, category, price) |
| `stores` | Store names, types, locations |
| `suppliers` | Supplier names and reliability |
| `calendar` | Full date table with day-of-week, payday, events |
| `transactions` | Every purchase (customer, store, date, amount, satisfaction) |
| `transaction_items` | Line items per transaction (product, qty, stockouts, substitutions) |
| `inventory` | Daily stock levels per product (opening, sold, received, closing) |
| `store_daily_metrics` | Daily KPIs (revenue, customers, stockouts, waste) |
| `waste_log` | Expired/damaged stock with cost |

### `village_star.db` — Star Schema (focus on analysis)
| Table | Description |
|-------|-------------|
| `dim_customer` | Customer dimension |
| `dim_product` | Product dimension |
| `dim_store` | Store dimension |
| `dim_date` | Date dimension (day-of-week, month, payday, events) |
| `fact_sales` | One row per item sold (all keys + satisfaction + stockout flags) |
| `fact_daily_store` | Daily store KPIs |
| `fact_inventory` | Daily stock snapshots |

Students derive lifecycle, churn, and competitor behavior from transaction patterns — see the [Analytics Workbook](notebooks/ch01_analytics.ipynb).

---

## Quick Start

**Pick a notebook:**
- [CH01 Normalized](notebooks/ch01_normalized.ipynb) — practice SQL joins & data prep
- [CH01 Star Schema](notebooks/ch01_star.ipynb) — focus on analysis with flat tables
- [CH01 Analytics Workbook](notebooks/ch01_analytics.ipynb) — learn to build cohort, churn, basket, segmentation tables

Or run locally:
```python
from student import Challenge, Decision

# Option A: Normalized (practice joins)
ch = Challenge.load('ch01', data_dir='challenges/ch01/data', db_name='village_normalized.db')

# Option B: Star schema (focus on analysis)
ch = Challenge.load('ch01', data_dir='challenges/ch01/data', db_name='village_star.db')

ch.brief()         # Challenge description
ch.questions()     # 10 guided questions
ch.db.tables()     # See database tables
```

---

## How to Submit

1. Complete your analysis in the [notebook](notebooks/ch01_open_for_business.ipynb)
2. Build a `Decision` with your findings
3. Validate: `d.validate()`
4. Export: `d.export(output_dir='submissions/ch01')`
5. Open a **Pull Request**

---

## Challenge Structure

```
challenges/ch01/
    data/
        village_normalized.db   ERP/CRM style (practice joins)
        village_star.db         Star schema (focus on analysis)
    brief.md                    Challenge description and context
    questions.json              10 guided analysis questions
    schema.json                 Submission requirements

notebooks/
    ch01_normalized.ipynb       Notebook for normalized DB
    ch01_star.ipynb             Notebook for star schema DB

student/                        Python utilities (Challenge, Decision)
submissions/ch01/               Submit your JSON here via PR
```

---

## Requirements

```
pandas
tabulate
```

No API keys needed. No LLM required. Everything runs locally.
