# Data and storage

## No database is needed to run this

Everything is stored as files.

| File | Written by | Holds |
|---|---|---|
| `data/comments.csv` | `data/generate_synthetic.py` | 2,030 rows: 2,000 comments plus 30 deliberate duplicates |
| `data/units_sold.csv` | the generator | Units sold by vendor, category, size and week |
| `data/gold_labels.csv` | the generator | The known answer for 300 comments |
| `data/demo_run/run.json` | `python -m fitradar.graph offline --demo` | A finished run, shown when no other run exists |
| `runs/latest/run.json` | each run | Every comment's reading and path, vendor rates, findings, counts, cost |
| `runs/tags.json` | the Review queue tab | `{comment_id: tag}` |
| `runs/actions.json` | the This week tab | `{vendor|category: {decision, fix, when}}` |
| `runs/uploads/` | the upload control | Your own CSV files, if you upload any |

`runs/` is not committed to git.

## The stand-in data

`python data/generate_synthetic.py` writes the same files every time (fixed seed).

- 17 vendors across 7 categories, six weeks of dates.
- Hinglish, some Hindi in Devanagari, some English; varied spellings; upper case; emoji.
- Hard cases: comments with two reasons, vague comments with no reason, one-word comments, blanks, duplicates.
- Each vendor writes sizes its own way ("XL", "X-Large", "42"); the load step makes them one label.
- Planted patterns: V-07 Kurtis run small at the bust; V-12 Dresses are short; V-03 Kids tees run large; V-18 Leggings are mixed; V-21 Palazzo has only 6 returns.

Every record is a comment on a returned order. Reviews of items the customer kept are not in the stand-in data.

## When you would want a database

On a free Hugging Face Space the disk is reset when the Space restarts, so tags and approvals made in the app are lost. That is acceptable for a demo. If you want them to last, or several people to use the app at once, move the three `runs/` files into a database. These are the tables it would need:

| Table | One row per | Columns |
|---|---|---|
| `runs` | pipeline run | `run_id`, `finished_at`, `provider`, `fast_model`, `strong_model`, `week_of`, counts, `cost_usd`, `seconds` |
| `comments` | comment | `comment_id`, `source`, `text`, `order_id`, `sku_id`, `vendor_id`, `vendor_city`, `category`, `size`, `created_at` |
| `readings` | comment per run | `run_id`, `comment_id`, `reason`, `second_reason`, `body_area`, `language`, `confidence`, `evidence_phrase`, `meaning_en`, `status`, `read_by`, `path` (JSON) |
| `vendor_stats` | vendor, category and run | `run_id`, `vendor_id`, `category`, `returns_read`, `fit_returns`, `units_sold`, `fit_return_rate`, `category_median`, `status`, `direction`, `body_area`, `rate_by_size` (JSON), `trend_6w` (JSON) |
| `findings` | vendor, category and run | `run_id`, `vendor_id`, `category`, `headline`, `evidence`, `suggested_fix`, `check`, `problems` (JSON), `attempts` |
| `human_tags` | tagged comment | `comment_id`, `tag`, `tagged_by`, `tagged_at` |
| `actions` | decision | `vendor_id`, `category`, `decision`, `fix`, `decided_by`, `decided_at`, `result` |
| `units_sold` | vendor, category, size, week | `vendor_id`, `category`, `size`, `week_start`, `units_sold` |

SQLite is enough for one server. Postgres (for example a free Supabase or Neon project) if it must survive restarts on a host with no persistent disk. Only `fitradar/store.py` would change; nothing else reads or writes storage.
