# Architecture

```
data/comments.csv  ─┐
data/units_sold.csv ┴─> 1 Load and clean (code)
                         │
                         v
                        2 Read every comment (fast model, batches of 20 in parallel)
                         │
                 70% sure and one reason? ── yes ───────────────┐
                         │ no                                   │
                         v                                      │
                        3 Re-read (strong model) ── now sure ──>│
                         │ still unsure                         v
                         v                                     5 Count and compare (code)
                        4 Review queue (a person)               │
                                                                v
                                                               6 Write finding (strong model)
                                                                │        ^
                                                                v        │ fails: rewrite once
                                                               7 Evaluate (fast model + code)
                                                                │
                                                                v
                                                   runs/latest/run.json ──> web app (five tabs)
                                                   runs/tags.json  <── review queue tags
                                                   runs/actions.json <── approvals
```

## Files

| File | What it holds |
|---|---|
| `config.py` | Every setting: models, prices, temperatures, thresholds |
| `fitradar/graph.py` | The LangGraph state graph: nodes, conditional edges, the run summary |
| `fitradar/llm.py` | The readers: Claude, GPT, offline rules. One interface |
| `fitradar/ingest.py` | Step 1: load, tidy sizes, drop duplicates, mark unreadable |
| `fitradar/aggregate.py` | Step 5: rates, medians, flags, trend, quotes |
| `fitradar/findings.py` | The code half of step 7: every figure must be in the data |
| `fitradar/cost.py` | Tokens x price, seconds, weekly projection |
| `fitradar/store.py` | Reading and writing the JSON files |
| `fitradar/accuracy.py` | The accuracy test against known answers |
| `prompts/*.md` | The four prompts |
| `server.py` | FastAPI: `/api/state`, `/api/run`, `/api/status`, `/api/tag`, `/api/action`, `/api/upload` |
| `web/` | The front end |

## Where each pattern sits in the graph

- **Parallelization:** node `read`. `ModelReader.read_batches` sends all batches with `max_concurrency` set in `config.py`.
- **Routing:** conditional edge after `read` (`needs_reread`), then node `queue`.
- **Prompt chaining:** `read` -> `aggregate` -> `write`. The strong model sees only `aggregate.evidence_for(group)`.
- **Evaluator-optimizer:** conditional edge after `evaluate` (`after_evaluate`) loops back to `write` while a finding has failed and rewrites remain.

## How it is evaluated and improved

| What is checked | How | If it falls short |
|---|---|---|
| Each comment | Confidence on every reading | Strong model re-reads; then a person |
| Each finding | Code matches every number to the data; fast model checks every claim | Rewritten once; then shown as "not verified" |
| The prompts | `python -m fitradar.accuracy` against `data/gold_labels.csv` | Revise, re-test, keep only if the score rises; log it in `prompts/CHANGELOG.md` |
| Each approved fix | Fit-return rate before and after, against unchanged vendors | Tracking is built: a person marks a fix as live and the result due date is set (`FOLLOW_UP_DAYS` in `config.py`). The before and after comparison itself is not built; it needs four weeks of real data after the fix |

## Flagging rule

A vendor and category is **flagged** when it has at least 30 returns, its fit-return rate (fit returns divided by units sold) is at least 1.5 times the category median, and one direction holds at least 60% of its fit comments. It is **watch** when above the median without meeting those tests. Under 30 returns there is **no call**. All four numbers are in `config.py`.
