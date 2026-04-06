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
| `calendar` | Full date table with day-of-week, payday, events |
| `transactions` | Every purchase (customer, store, date, amount) |
| `transaction_items` | Line items per transaction (product, qty, stockouts) |
| `inventory` | Daily stock levels per product |
| `customer_lifecycle` | State transitions (retained, at-risk, churned) |
| `customer_daily_activity` | Daily visit/absence log |
| `competitor_visits` | Purchases at competitor stores |
| `store_daily_metrics` | Daily KPIs (revenue, customers, stockouts) |
| `waste_log` | Expired/damaged stock |

### `village_star.db` — Star Schema (focus on analysis)
| Table | Description |
|-------|-------------|
| `dim_customer` | Customer dimension |
| `dim_product` | Product dimension |
| `dim_store` | Store dimension |
| `dim_date` | Date dimension (day-of-week, month, payday, events) |
| `fact_sales` | One row per item sold (denormalized with all keys) |
| `fact_daily_store` | Daily store KPIs |
| `fact_inventory` | Daily stock snapshots |
| `fact_customer_lifecycle` | Lifecycle state transitions |
| `fact_competitor_visits` | Competitor store visits |

---

## Quick Start

```python
import sys; sys.path.insert(0, '.')
from student import Challenge, Decision

# Load normalized DB (for data prep practice)
ch = Challenge.load('ch01', data_dir='challenges/ch01/data')

# Or load star schema DB (for analysis)
# ch = Challenge.load('ch01', data_dir='challenges/ch01/data', db_name='village_star.db')

ch.brief()
ch.db.tables()
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
    brief.md                    Challenge description
    schema.json                 Submission requirements

student/                        Python utilities
notebooks/                      Guided analysis notebooks
submissions/                    Submit your JSON here via PR
```

---

## Requirements

```
pandas
tabulate
```

No API keys needed. No LLM required. Everything runs locally.
