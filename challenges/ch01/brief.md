# CH01 — Open for Business

## Your Client

**Khun Somchai** has been running **Village Fresh Supermarket** for 8 years in a small Thai village. It's the main grocery store for ~150 households.

## The Situation

90 days of data (Aug 15 – Nov 12, 2024):
- ~30,000 item-level transactions across 150 customers
- 59 products (dairy, produce, meat, dry goods, beverages, snacks, household, frozen)
- Daily inventory levels for every product

He wants to understand: **How is my business really doing, and what should I do next?**

## Your Task

1. **Explore the data** — 4 tables: `products`, `calendar`, `transactions`, `inventory`
2. **Answer the challenge questions** — Run `ch.questions()`
3. **Find insights** — Revenue patterns, customer behavior, inventory problems
4. **Make a recommendation** — One specific action with budget ≤ 10,000 THB

## Two Database Options

| Database | Use when |
|----------|----------|
| `village_normalized.db` | Practice **SQL joins and data preparation** |
| `village_star.db` | Focus on **analysis with pre-joined tables** |

## Getting Started

```python
from student import Challenge
ch = Challenge.load('ch01', data_dir='data', db_name='village_normalized.db')
ch.brief()
ch.questions()
ch.db.tables()
```
