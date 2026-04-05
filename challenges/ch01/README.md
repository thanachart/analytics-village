# CH01 — Open for Business

**Business:** Village Fresh Supermarket (Khun Somchai)
**Tier:** 1 — Reporting
**Challenge:** Sales reporting, aggregation, time series, KPIs

## Quick Start

```python
import sys; sys.path.insert(0, '../..')
from student import Challenge, Decision

ch = Challenge.load('ch01', data_dir='data')
ch.brief()
ch.db.tables()
ch.owner.questions()
```

## Data

- `data/village.db` — SQLite database with all simulation tables
- `brief.md` — Challenge description
- `schema.json` — Submission field requirements

## Submit

1. Complete your analysis in the [notebook](../../notebooks/ch01_open_for_business.ipynb)
2. Build a `Decision` with your findings
3. Export to `../../submissions/ch01/YOUR_STUDENT_ID.json`
4. Open a Pull Request
