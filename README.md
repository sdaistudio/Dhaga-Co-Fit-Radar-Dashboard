---
title: Fit Radar
emoji: 📏
colorFrom: indigo
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# Fit Radar

Fit Radar reads return comments and product reviews for a fashion brand, records why each item came back, and shows which vendors have a fit problem, in which direction, with a suggested size-chart fix for a person to approve.

**Live demo (Replay mode, saved run):** https://sdaistudio.github.io/Dhaga-Co-Fit-Radar-Dashboard/

Built for FDE Academy Tech Track, Mini Project 1 (the Dhaga & Co. engagement). Dhaga & Co. is a case study. **All data in this repository is invented stand-in data.**

## Run it in five minutes

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python data/generate_synthetic.py                      # writes the 2,000-record stand-in data
uvicorn server:app --port 7860
```

Or run using Docker:

```bash
docker build -t fitradar .
docker run -d --name fitradar-app -p 7860:7860 fitradar
```

Open http://localhost:7860. With no API key the app opens on a saved demo run made with offline keyword rules, so every tab works at once.

To read the comments with a real model, copy `.env.example` to `.env`, add a key, load it into your shell (`set -a; source .env; set +a`), restart, then press **Run** on the Run and cost tab.

## What it expects

Two CSV files, either the bundled ones in `data/` or your own uploaded on the Run and cost tab.

- `comments.csv`: `comment_id, source, text, order_id, sku_id, vendor_id, vendor_city, category, size_bought, created_at` (extra columns are ignored)
- `units_sold.csv`: `vendor_id, category, size, week_start, units_sold`

## What it does when something goes wrong

| Situation | What you see |
|---|---|
| Blank, one-word or symbol-only comment | Counted as unreadable. Not sent to a model. |
| Two reasons in one comment | Both tagged; the path shows the second read. |
| Both readers under 70% sure | In the review queue, with the best guess. |
| A model reply fails validation | Retried, then sent to the review queue. The run continues. |
| Vendor with fewer than 30 returns | "No recommendation shown." |
| A finding fails its check twice | "Finding could not be verified", numbers only. |
| The model service fails | A sentence on the Run tab saying which step stopped. |
| No API key | The app runs on offline keyword rules and says so in the header. |
| A file has the wrong columns | A message naming the missing columns. |

## How it is built

- **Front end:** plain HTML, CSS and JavaScript in `web/`. No build step.
- **Server:** FastAPI (`server.py`).
- **Pipeline:** a LangGraph state graph (`fitradar/graph.py`), seven steps.
- **Models:** through LangChain. Claude by default, OpenRouter or GPT optional, offline rules with no key. See `docs/MODEL_OPTIONS.md`.
- **Storage:** JSON files in `runs/`. No database. See `docs/DATA_AND_STORAGE.md`.

| Step | Done by | Pattern |
|---|---|---|
| 1 Load and clean | Code | – |
| 2 Read every comment | Fast model | Parallelization |
| 3 Re-read the unclear ones | Strong model | Routing |
| 4 Pass the rest to a person | Code | Routing |
| 5 Count and compare | Code | Prompt chaining (middle link) |
| 6 Write each finding | Strong model | Prompt chaining |
| 7 Evaluate each finding | Fast model + code | Evaluator-optimizer |

More in `docs/ARCHITECTURE.md`. The brief this was built from is `FIT_RADAR_BUILD_SPEC.md`; `docs/build_note.md` records where the build differs from it. The problem, owner and success measure are in `docs/discovery_note.md`.

## Commands

```bash
python data/generate_synthetic.py     # rebuild the stand-in data (same output every time)
python -m fitradar.graph offline      # run the pipeline without the web app
python -m fitradar.graph anthropic    # run it with Claude (needs ANTHROPIC_API_KEY)
python -m fitradar.accuracy           # score the latest run against the 300 known answers
pytest                                # tests; no API key needed
```

## Deploy

See `docs/DEPLOYMENT.md`. The repository includes a `Dockerfile` and the header above, so it runs as a Hugging Face Docker Space as it is.

## Brief checklist

- [x] Visible front end, usable without narration
- [x] Deployed to a public URL: GitHub Pages, Replay mode (see `docs/DEPLOYMENT.md`)
- [x] Runs locally from the repository
- [x] Four patterns, each for a reason
- [x] Code versus model line: no number is computed by a model
- [x] Two models, with cost and seconds recorded per run
- [x] Temperatures stated: 0 to read and evaluate, 0.3 for findings (`config.py`)
- [x] Structured output at every model call, with validation-failure handling
- [x] Fails visibly
- [x] Cost line with arithmetic
- [ ] Live model run measured (cost and accuracy figures are not filled in until you run with a key)
