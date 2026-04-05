# EP01 — Open for Business

**Business:** Village Fresh Supermarket (Khun Somchai)
**Tier:** 1 — Reporting
**Challenge:** Sales reporting, aggregation, time series, KPIs

## Quick Start

```python
import sys; sys.path.insert(0, '../..')
from student import Episode, Decision

ep = Episode.load('ep01', data_dir='data')
ep.brief()
ep.db.tables()
ep.owner.questions()
```

## Data

- `data/village.db` — SQLite database with all simulation tables
- `brief.md` — Episode challenge brief
- `schema.json` — Submission field requirements

## Submit Your Analysis

1. Complete your analysis in the notebook
2. Build a `Decision` object with your findings and recommendation
3. Export to `../../submissions/ep01/YOUR_STUDENT_ID.json`
4. Open a Pull Request to this repository

See the [notebook](../../notebooks/ep01_open_for_business.ipynb) for a guided walkthrough.
