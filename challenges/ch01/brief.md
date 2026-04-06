# CH01 — Open for Business

## Your Client

**Khun Somchai** has been running **Village Fresh Supermarket** for 8 years in a small Thai village. It's the main grocery store for ~150 households. He's proud of his store but worried about recent trends he can't quite put into numbers.

## The Situation

Somchai has 90 days of data (Aug 15 – Nov 12, 2024) covering:
- ~4,300 transactions across 150 customer households
- 59 products (dairy, produce, meat, dry goods, beverages, snacks, household, frozen)
- Daily inventory levels, stockout events, and waste
- Customer visit patterns and satisfaction scores

He wants to understand: **How is my business really doing, and what should I do next?**

## Your Task

1. **Explore the data** — Understand revenue patterns, customer behavior, and operations
2. **Answer the challenge questions** — Run `ch.questions()` to see 10 guided questions
3. **Find insights** — What patterns does the data reveal that Somchai might not see?
4. **Make a recommendation** — Propose ONE specific, actionable plan with budget ≤ 10,000 THB

## Two Database Options

| Database | Use when |
|----------|----------|
| `village_normalized.db` | Practice **SQL joins and data preparation** |
| `village_star.db` | Focus on **analysis with pre-joined tables** |

## Budget

Up to **10,000 THB** for any recommended actions.

## Getting Started

```python
from student import Challenge, Decision

ch = Challenge.load('ch01', data_dir='challenges/ch01/data', db_name='village_normalized.db')
ch.brief()
ch.questions()
ch.db.tables()
```
