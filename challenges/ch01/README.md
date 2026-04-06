# CH01 — Open for Business

**Business:** Village Fresh Supermarket (Khun Somchai)
**Tier:** 1 — Reporting
**Period:** Aug 15 – Nov 12, 2024 (90 days)

## Two Database Options

| Notebook | Database | Focus |
|----------|----------|-------|
| [ch01_normalized.ipynb](../../notebooks/ch01_normalized.ipynb) | `village_normalized.db` | Practice SQL joins & data prep |
| [ch01_star.ipynb](../../notebooks/ch01_star.ipynb) | `village_star.db` | Focus on analysis with flat tables |

## Files

- `data/village_normalized.db` — ERP/CRM style (customers, products, transactions, transaction_items, inventory...)
- `data/village_star.db` — Star schema (dim_customer, dim_product, fact_sales, fact_daily_store...)
- `brief.md` — Challenge description and context
- `questions.json` — 10 guided analysis questions
- `schema.json` — Submission field requirements

## Quick Start

```python
from student import Challenge, Decision
ch = Challenge.load('ch01', data_dir='data', db_name='village_normalized.db')
ch.brief()
ch.questions()
ch.db.tables()
```

## Submit

Export to `../../submissions/ch01/YOUR_ID.json` and open a Pull Request.
