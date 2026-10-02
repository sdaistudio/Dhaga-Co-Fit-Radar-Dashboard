# Fit Radar: build specification (MVP 1)

This file is the brief for building Fit Radar with Claude Code in VS Code. Put it at the root of an empty repository and ask Claude Code to read it and follow the build order in section 14.

Context: FDE Academy Tech Track, Mini Project 1, the Dhaga & Co. engagement. Dhaga & Co. is a fictional direct-to-consumer fashion brand described in a case-study brief. The architecture reads the client's 410,000 customer reviews, newest first. The brief supplies no data file, so the build runs on stand-in data that is prepared separately and placed in `data/` (see section 5.3).

---

## 1. What we are building, and for whom

**The problem, in the client's words.** Returns are 31% of orders. For 44% of those returns the reason is recorded only as "Other" with free text. Neha, the Category Head, says most of that text is about fit, but she can read only a few hundred comments at a time. Dhaga & Co. also holds 410,000 product reviews that nobody has analysed. Size charts differ by vendor.

**The user.** Neha and her category team. They are not engineers. They must be able to open the app and use it without anyone explaining it.

**What Fit Radar does.** It reads the customer reviews newest first, and each week's return comments, records why each item came back, and shows which vendors and categories have a fit problem, in which direction (runs small, runs large, too short), with customer quotes as evidence and a suggested size-chart fix that Neha approves or sends back.

**What success looks like.**
- At least 85% agreement with comments labelled by hand (see section 12).
- The share of returns with no usable reason falls from 44% to under 10%.
- For approved fixes, the vendor's fit-return rate falls against similar vendors that were not changed.

**Not in scope.** Nothing customer-facing. No integration with any real system. No model training. No user accounts. No production hardening.

---

## 2. Rules from the project brief that the build must satisfy

Treat each of these as a requirement, and keep the list in the README as a checklist.

1. **A visible frontend** usable without narration. A notebook is not a submission.
2. **Deployed to a public URL** that works when a stranger opens it. Target: Hugging Face Spaces with Streamlit.
3. **Runs locally from the repository.** A stranger with the README gets it running in five minutes.
4. **At least two workflow patterns, used because the problem needs them.** This build uses four: parallelization, routing, prompt chaining, evaluator-optimizer.
5. **A deliberate code versus model line.** Every step is either deterministic code or a model call. Models are used only for judgement, language and messy mapping, never for arithmetic, comparison or lookup.
6. **At least two different models**, with the split justified on cost, latency and quality. Record seconds per call and per run.
7. **Stated temperatures.** Classification and evaluation at 0. Internal prose at 0.3.
8. **Structured output at every model boundary**, validated against a schema. Handle validation failure explicitly.
9. **Fails visibly.** When the system cannot answer, it says so on screen. No silent guesses.
10. **A cost line.** Report the cost of one run and the arithmetic to scale it to weekly volume.
11. **Holds up on real-shaped input:** Hinglish, free text, misspellings, one-word comments. Not three hand-picked rows.
12. **The demo must include one failure case shown on purpose.**

---

## 3. Technology

- Python 3.11 or later.
- **Streamlit** for the frontend.
- **Anthropic Python SDK** for model calls. API key from the `ANTHROPIC_API_KEY` environment variable. Never commit a key.
- **Pydantic v2** for every schema.
- **pandas** for data handling.
- **pytest** for tests.
- No database. Results are written to files under `runs/` (JSON and Parquet or CSV).

**Models** (set in `config.py`, never hard-coded elsewhere):

| Role | Model ID | Temperature | Used for |
|---|---|---|---|
| Fast | `claude-haiku-4-5-20251001` | 0 | Reading every comment; checking every finding |
| Strong | `claude-sonnet-5-5` | 0 for re-reads, 0.3 for findings | Unclear comments; writing findings |

Before writing the model client, check the current Anthropic documentation for the supported way to get schema-constrained JSON output from the SDK, and use that. Whatever method is used, the response must still be validated with Pydantic.

---

## 4. Repository layout

```
fit-radar/
├── README.md
├── FIT_RADAR_BUILD_SPEC.md        # this file
├── requirements.txt
├── .env.example                    # ANTHROPIC_API_KEY=
├── .gitignore                      # .env, runs/*, __pycache__
├── app.py                          # Streamlit entry point
├── config.py                       # models, thresholds, prices, paths
├── fitradar/
│   ├── __init__.py
│   ├── schemas.py                  # all Pydantic models
│   ├── ingest.py                   # step 1: load, clean, join (code)
│   ├── classify.py                 # step 2: parallel batch read (fast model)
│   ├── route.py                    # steps 3 and 4: escalate or queue
│   ├── aggregate.py                # step 5: rates and flags (code)
│   ├── findings.py                 # step 6: write each finding (strong)
│   ├── evaluate_finding.py         # step 7: check each finding (fast + code), one rewrite
│   ├── accuracy.py                 # accuracy test against hand labels
│   ├── llm.py                      # one thin client: call, validate, retry, log tokens
│   ├── cost.py                     # token, seconds and rupee accounting
│   ├── pipeline.py                 # runs steps 1 to 7, reports progress
│   └── store.py                    # read and write run results, tags, actions
├── prompts/
│   ├── classify.md
│   ├── reread.md
│   ├── finding.md
│   └── evaluate.md
├── data/
│   ├── reviews.csv                 # customer reviews (stand-in, supplied separately)
│   ├── return_comments.csv         # weekly "Other" return comments (stand-in, supplied separately)
│   ├── units_sold.csv              # supplied separately
│   ├── gold_labels.csv             # 300 reviews labelled by hand
│   └── demo_run/                   # a saved finished run, committed (see section 10)
├── docs/
│   ├── discovery_note.md
│   └── build_note.md
└── tests/
    ├── test_ingest.py
    ├── test_aggregate.py
    ├── test_schemas.py
    ├── test_route.py
    └── test_cost.py
```

---

## 5. Data

### 5.1 Input files

**`reviews.csv`**, one row per customer review. This is the main source: 410,000 reviews, eighteen months deep.

| Column | Type | Notes |
|---|---|---|
| `comment_id` | string | Unique |
| `text` | string | Free text, mostly Hinglish. May be blank, one word, or duplicated |
| `star_rating` | integer | 1 to 5 |
| `order_id` | string | |
| `sku_id` | string | |
| `vendor_id` | string | For example `V-07` |
| `vendor_city` | string | Tiruppur or Jaipur |
| `category` | string | Kurtis, Dresses, Kids tees, Leggings, Palazzo, Kurtas, Tops |
| `size_bought` | string | As the vendor labels it; labels differ by vendor and must be made consistent at load |
| `created_at` | date | Used to assign the batch |

**`return_comments.csv`**, one row per return coded "Other": the same columns without `star_rating`, plus `return_reason_code`. About 6,547 a week at the client's volume.

**`units_sold.csv`**, one row per vendor, category, size and week: `vendor_id, category, size, week_start, units_sold`. This is the denominator for the fit-return rate.

At load, both text files are combined into one table with a `source` column (`review` or `return`).

### 5.2 Reading order

Reviews are read in three batches by age, newest first. The load step assigns each review a `batch` from `created_at` relative to the newest date in the file.

| Batch | Reviews | About how many | Why |
|---|---|---|---|
| 1 | Last month | 22,800 | Speaks to products on sale now; proves the pipeline cheaply |
| 2 | 1 to 3 months old | 45,600 | Enough history for a six-week trend |
| 3 | Over 3 months old | 341,700 | Long-run vendor patterns; read only if the first two prove useful |

- The user chooses which batches to run. Batch 1 is the default.
- A later batch adds to the results of earlier ones; nothing already read is read again.
- Counts assume reviews are spread evenly over eighteen months, which the brief does not say.
- Return comments are always read for the current week.

### 5.3 Stand-in data

The brief supplies no data. Stand-in files in the shapes above are prepared separately and are not part of this specification's architecture. The build must not depend on how they were made. They are expected to:

- Be mostly Hinglish in Latin script, with some Hindi in Devanagari and some English, and varied spellings of the same word.
- Include hard cases: two reasons in one comment, one-word comments, blanks, duplicates, vague comments with no reason.
- Span more than three months, so all three batches have rows.
- Carry a few known vendor patterns so results can be checked: for example V-07 Kurtis running small, V-12 Dresses shorter than shown, V-03 Kids tees running large, V-18 Leggings mixed, V-21 Palazzo with only 6 returns.

`gold_labels.csv` holds the correct reason for 300 reviews, labelled by hand by the group.

If the stand-in files are not yet in `data/`, stop and ask for them. Do not generate data inside this build.

---

## 6. The pipeline

Seven steps. The table is the code versus model line and must be reproduced in `docs/build_note.md`.

| # | Step | Done by | Pattern | Why |
|---|---|---|---|---|
| 1 | Load, clean, join, assign batch, drop blanks and duplicates | Code | – | Exact, free, testable |
| 2 | Read every comment in batches of 20 | Fast model | Parallelization | Hinglish free text is language work; volume needs concurrency |
| 3 | Re-read unclear comments | Strong model | Routing | Judgement on ambiguity is worth a dearer call on a minority |
| 4 | Send the still-unclear to a person | Code | Routing | A visible gap beats a silent wrong answer |
| 5 | Compute rates, compare to median, flag | Code | Prompt chaining (middle link) | Arithmetic and comparison: never a model |
| 6 | Write each finding | Strong model | Prompt chaining | Plain-language output needs a model, fed only step 5's numbers and quotes |
| 7 | Evaluate each finding; send failures back to step 6 once | Fast model + code | Evaluator-optimizer | Figures and claims must be verified before anyone sees them |

Two loops sit on top of the steps:

- **Inside a run (evaluate and rewrite):** step 7 checks step 6's output. A failure returns to step 6 with the reasons, once.
- **Across runs (improve):** a person's tags from the review queue join the hand labels as test cases. The accuracy test scores the reading instructions. A revised instruction is adopted only if the score rises.

### Step 1: ingest (`ingest.py`)

- Load the three CSVs. Strip whitespace. Make `size_bought` consistent across vendors (for example "XL", "X-Large" and "42" to one label, by a lookup table in code). Combine reviews and return comments with a `source` column. Assign each review its batch (section 5.2) and keep only the batches selected for this run.
- Mark a comment **unreadable by rule**, without calling a model, if the text is blank, fewer than 3 words, or contains no letters. These still count in the totals as "Unreadable".
- Drop exact duplicates of (`order_id`, `text`). Report how many were dropped.
- Output a clean DataFrame and an `IngestReport` with counts: in, blank, duplicate, unreadable by rule, sent to model.

### Step 2: classify (`classify.py`)

- Batch 20 comments per call. Run batches concurrently with a configurable limit (default 8).
- Fast model, temperature 0.
- Output per comment is a `CommentReading` (schema in section 7).
- The prompt in `prompts/classify.md` must: define each reason; give Hinglish, Hindi and English examples for each; tell the model to report low confidence rather than guess; tell it to record a second reason when two are present; and require the exact phrase it relied on.
- If a batch fails validation, retry it once with the validation error included. If it fails again, split the batch and retry each comment alone. Any comment that still fails goes to the review queue with status `schema_failed`.

### Steps 3 and 4: route (`route.py`)

- **Accept** if confidence is at or above `CONF_ACCEPT` (default 0.70) and there is no second reason.
- **Escalate to the strong model** if confidence is below `CONF_ACCEPT`, or a second reason is present. Strong model, temperature 0, one comment per call, using `prompts/reread.md`.
- After the re-read: accept if confidence is at or above `CONF_ACCEPT`; otherwise put it in the **review queue** with the model's best guess and confidence.
- A comment with two reasons is counted under both in the reason breakdown.
- Record for every comment the path it took, as a list of steps, so the Comments tab can show it.

### Step 5: aggregate (`aggregate.py`)

All deterministic.

- **Fit-return rate** = fit-related returns ÷ units sold, for each vendor and category, and for each size within it.
- **Category median** = median of that rate across vendors in the category.
- **Status:**
  - `too_few` if returns for the vendor and category are below `MIN_RETURNS` (default 30). No finding is written.
  - `flag` if the rate is at least `FLAG_RATIO` (default 1.5) times the category median.
  - `watch` if the rate is above the median but below the flag threshold, or if fit complaints have no dominant direction (no single direction above 60% of fit comments).
  - `ok` otherwise.
- **Direction:** the dominant fit reason and body area among the fit comments.
- **Trend:** the rate for each of the last six weeks.
- **Evidence:** the counts used, and up to five representative quotes chosen by code (highest confidence, distinct text).

### Steps 6 and 7: write, then evaluate (`findings.py`, `evaluate_finding.py`)

- For each `flag` or `watch` group, send the strong model (temperature 0.3) the numbers and quotes from step 5 and ask for a `Finding` (section 7): a one-sentence finding, an evidence sentence that cites the numbers, and a suggested fix.
- **Step 7, evaluate, in two parts:**
  - **Code check:** every number that appears in the finding text must equal a number in the evidence payload. Extract numbers with a regular expression and compare.
  - **Model check:** fast model, temperature 0, using `prompts/evaluate.md`. It answers whether each claim is supported by the supplied quotes and numbers, and returns an `Evaluation`.
- If either check fails, regenerate once with the failure reasons included. If it fails again, show the group on screen with the label "Finding could not be verified" and the raw numbers only.
- Record whether each finding passed first time, was rewritten, or failed, with the evaluator's reasons.

### How the system is evaluated and improved

| What is checked | How | By | If it falls short |
|---|---|---|---|
| Each comment: is the reading sure? | Confidence on every reading; a second reason is flagged | Fast model | Under 70% or two reasons: strong model re-reads. Still under 70%: a person tags it |
| Each finding: is it true to the data? | Every number matched to the data; every claim matched to the quotes | Code, then fast model | Strong model rewrites once with the reasons. Fails again: shown as "not verified", numbers only |
| The reading instructions: are readings right? | `python -m fitradar.accuracy` on 300 hand labels plus saved human tags; agreement overall and per reason; target 85% | Code | Revise the prompt, re-run the test, adopt the revision only if the score rises. Keep each prompt version and its score in `prompts/CHANGELOG.md` |
| Each approved fix: did returns fall? | Vendor's fit-return rate before and after, four weeks apart, against similar unchanged vendors | Code | Report "no clear change" |

Human tags are saved with the comment text so they can be reused as test cases. Never use the same comments both to revise a prompt and to score it: hold back half of the hand labels as a test set that prompt revisions are not tuned on.

---

## 7. Schemas (`schemas.py`)

Write these as Pydantic v2 models. Use enums for every closed set.

```python
class Reason(str, Enum):
    fit_small = "fit_small"
    fit_large = "fit_large"
    fit_short = "fit_short"
    fit_long = "fit_long"
    fit_other = "fit_other"
    quality = "quality"
    colour = "colour"
    late = "late"
    changed_mind = "changed_mind"
    other = "other"
    unclear = "unclear"

class BodyArea(str, Enum):
    bust = "bust"; waist = "waist"; hip = "hip"; shoulder = "shoulder"
    sleeve = "sleeve"; length = "length"; overall = "overall"; not_applicable = "not_applicable"

class CommentReading(BaseModel):
    comment_id: str
    reason: Reason
    second_reason: Reason | None = None
    body_area: BodyArea
    language: Literal["hinglish", "hindi", "english", "other"]
    confidence: float = Field(ge=0, le=1)
    evidence_phrase: str          # exact words from the comment
    meaning_en: str               # one short English sentence

class PathStep(BaseModel):
    by: Literal["code", "fast", "strong", "person"]
    note: str

class CommentResult(BaseModel):
    reading: CommentReading | None
    status: Literal["accepted", "queued", "unreadable_rule", "schema_failed"]
    read_by: Literal["rule", "fast", "strong", "person"]
    path: list[PathStep]

class GroupStats(BaseModel):
    vendor_id: str; category: str; vendor_city: str
    returns_read: int; fit_returns: int; units_sold: int
    fit_return_rate: float; category_median: float
    status: Literal["flag", "watch", "ok", "too_few"]
    direction: Reason | None; body_area: BodyArea | None
    rate_by_size: dict[str, float]
    trend_6w: list[float]
    quotes: list[str]

class Finding(BaseModel):
    vendor_id: str; category: str
    headline: str                 # one sentence
    evidence: str                 # cites the numbers
    suggested_fix: str

class Evaluation(BaseModel):
    supported: bool
    problems: list[str]

class RunSummary(BaseModel):
    run_id: str; started_at: datetime
    counts: dict[str, int]        # in, dropped, read, escalated, queued, findings, rewritten
    reason_share: dict[str, float]
    cost_usd: float; cost_inr: float
    tokens: dict[str, dict[str, int]]   # per model: input, output
```

---

## 8. The screen (`app.py`)

One Streamlit app, wide layout, five tabs. A reference design exists as a clickable mock-up; the content of each tab is specified here so the build does not depend on it.

**Header on every tab:** app name, the week of the data, which batches are loaded, and a "Stand-in data" badge whenever the bundled files are in use.

**Sidebar:** file uploaders for `reviews.csv`, `return_comments.csv` and `units_sold.csv`, a "Use bundled data" button, a batch selector (last month; 1 to 3 months; over 3 months), a "Run" button, and a mode indicator: **Live** (API key present) or **Replay** (showing the saved demo run).

### Tab 1: This week
- Four figures: comments read (of how many in the file), share about fit, vendors flagged, comments needing a person.
- Table of vendor and category groups: vendor, category, signal, fit-return rate, category median, returns read, status. Sorted with flagged first. Selecting a row opens its detail.
- Detail panel for the selected group: the finding headline, the evidence sentence, fit-return rate by size (bar chart), six-week trend (bar chart), two or three customer quotes, the suggested fix, a line confirming the figures were checked, and two buttons: **Approve size-chart fix** and **Send back**.
- For a `too_few` group, the panel shows: "No recommendation shown. Fit Radar needs at least 30 returns before it calls a pattern." No buttons.
- Below the table: a stacked bar of all return reasons for the week. Choosing a reason opens the Comments tab filtered to it.
- One line under the table stating the flagging rule in plain words.

### Tab 2: Comments
- Filter by reason, vendor and "read by".
- Table: comment text, reason, confidence, read by.
- Detail for the selected comment: original text, English meaning, all recorded fields, and the path it took (each step labelled code, fast model, strong model or person).

### Tab 3: Review queue
- Count of comments needing a person and a sentence explaining why they are there.
- For each: text, English meaning, the model's best guess and confidence, and buttons to tag it: Fit, Quality, Colour, Changed mind, Cannot tell. Tagging removes it from the queue, saves the tag to `runs/<run_id>/human_tags.csv`, and updates the counter. Provide an undo.

### Tab 4: Actions
- List of approved fixes: vendor, fix, date approved, status, and result.
- New approvals show "Not measured yet. Compared four weeks after the fix."
- A short panel explaining how a fix is judged: before and after for the fixed vendor, against similar vendors that were not changed.
- Persist to `runs/actions.csv`.

### Tab 5: Run and cost
- The seven steps, each showing who does it (code, fast, strong, person), a one-line description, its count and its seconds. While a run is in progress, show live progress per step.
- Cost of this run: one line per model with the arithmetic (calls or tokens × price), total in dollars and rupees.
- Projection to weekly volume, and to each review batch, with the multipliers shown and editable.
- The latest accuracy score and the prompt version it belongs to.
- A "Who does what" legend.

**Wording rules for the screen:** plain English, no jargon. Say "fast model" and "strong model", not model IDs, except on the Run and cost tab. Never show a traceback to the user; show a sentence saying what failed and what to do.

---

## 9. Failure behaviour (must all be visible on screen)

| Case | What the user sees |
|---|---|
| Blank, one-word or symbol-only comment | Counted under "Unreadable". Never sent to a model. |
| Two reasons in one comment | Both tagged; counted under both; path shows the re-read. |
| Both models under 70% sure | In the review queue with the best guess and confidence. |
| Model output fails the schema twice | In the review queue marked "could not be read automatically"; the run continues. |
| Vendor with fewer than 30 returns | "Too few returns to call." No finding. |
| Finding fails its check twice | "Finding could not be verified", numbers shown without prose. |
| API error or rate limit | Retry with backoff up to 3 times, then a banner: "The run stopped at step N. Nothing was lost. Press Run to continue." Completed batches are not re-run. |
| No API key | App opens in Replay mode with a clear banner. |
| Uploaded file has wrong columns | A message naming the missing columns. |

For the live demo, the bundled data must reliably show the two-reason case and the too-few-returns case.

---

## 10. Replay mode

The public URL must work when opened cold, even without an API key or if the API is slow.

- Commit one complete finished run under `data/demo_run/`.
- If `ANTHROPIC_API_KEY` is missing, or the user chooses "Use saved run", the app loads that run and every tab works, including tagging and approving.
- The Run and cost tab can replay the step progress from the saved counts.
- Live mode and Replay mode must be labelled so nobody mistakes one for the other.

---

## 11. Cost accounting (`cost.py`)

- Record input and output tokens and elapsed seconds for every call. Never estimate when the real count is available.
- Prices in `config.py` (US dollars per million tokens; verify against the Anthropic pricing page before the demo):
  - Fast: 1.00 input, 5.00 output
  - Strong: 2.00 input, 10.00 output
- `USD_TO_INR` in `config.py`, default 88.
- Planning estimate, to be replaced by measured figures after the first real run: about $0.00045 per comment on the fast model, about $0.0023 per re-read on the strong model, about $0.018 per finding written and checked. For 2,000 comments with 15% re-read and 5 findings that is about $1.63. At the client's weekly volume of about 11,800 comments it is about $10.30, roughly ₹906 a week.
- The weekly volume is 6,547 "Other" returns (48,000 orders × 31% × 44%) plus an estimated 5,256 new reviews (410,000 ÷ 78 weeks). The review figure is an estimate; label it as one.
- Reading all 410,000 reviews once is about $326: roughly $18 for the last month, $36 for 1 to 3 months and $272 for older reviews, if reviews are spread evenly. Show the cost of each batch before it is run.

---

## 12. Tests and acceptance

**Unit tests (no API calls):**
- Ingest: blanks, duplicates and short comments handled as specified; counts add up.
- Aggregate: rates, medians, statuses and thresholds correct on a small fixed dataset, including the `too_few` and `watch` cases.
- Route: each combination of confidence and second reason goes to the right place.
- Schemas: valid and invalid payloads.
- Cost: arithmetic matches a hand-worked example.
- Findings code check: a finding containing a number not in the evidence is rejected.

**Accuracy test (uses the API, run on demand):** `python -m fitradar.accuracy` classifies the 300 hand-labelled reviews and prints agreement overall and per reason, plus a confusion table. Target: 85% or better overall. Write the result into `docs/build_note.md`.

**Acceptance checklist:**
- [ ] `streamlit run app.py` works from a clean clone in under five minutes following the README.
- [ ] Opens in Replay mode with no API key.
- [ ] A full live run on batch 1 completes and all five tabs show its results.
- [ ] On the stand-in data, the known vendor patterns come out as expected (for example V-07, V-12 and V-03 flagged; V-18 "watch"; V-21 "too few").
- [ ] Running batch 2 after batch 1 adds to the results without re-reading batch 1.
- [ ] Seconds per call and per run are recorded and shown.
- [ ] Every failure case in section 9 can be demonstrated.
- [ ] Every model call returns a validated schema; no free-text parsing anywhere.
- [ ] Cost of the run is shown with its arithmetic.
- [ ] No number is computed by a model.
- [ ] No secrets in the repository.
- [ ] All unit tests pass.

---

## 13. Documents to write

- **`README.md`:** what it does; how to run locally; what input it expects; what it does when something goes wrong; the requirement checklist from section 2; how to deploy.
- **`docs/discovery_note.md`:** one page with the problem sentence, owner, evidence, cost, success measure, ranked shortlist and biggest assumption. Leave clearly marked placeholders for the group to complete; do not invent client facts.
- **`docs/build_note.md`:** two pages at most with the code versus model table, why each pattern is there and what breaks without it, the cost line with measured figures, the accuracy result, and a section headed "The thing that broke that we did not expect" left for the group to fill in.

---

## 14. Build order

Work in this order. After each stage, run the tests and stop for review.

1. **Skeleton and deploy first.** Repository layout, `requirements.txt`, `config.py`, a Streamlit page with the five empty tabs. Deploy this to Hugging Face Spaces before anything else and confirm the URL opens.
2. **Data in place.** Confirm the stand-in files and hand labels are in `data/` and match section 5. Inspect them by eye. Do not generate data.
3. **Schemas and ingest**, with tests.
4. **Aggregate**, with tests, driven by the hand labels and a small fixed test table so it can be built and checked before any model call exists.
5. **Model client (`llm.py`)**: call, validate, retry, token logging.
6. **Classify and route.** Run on 100 comments first, read the output, then the full sample.
7. **Findings, evaluator and the rewrite loop.**
8. **Pipeline and storage.** Save a full run; commit it as `data/demo_run/`.
9. **The five tabs**, in order, reading from a saved run so the interface can be built without spending on API calls.
10. **Replay mode, failure cases, cost tab.**
11. **Accuracy test, prompt changelog, documents, README.**
12. **Redeploy and test the public URL on a phone and on a machine that has never seen it.**

---

## 15. Things to ask the group rather than assume

- The minimum-returns threshold (30) and flag ratio (1.5): confirm or change.
- Whether reviews and return comments should be weighted equally.
- Who prepares the stand-in data and who labels the 300 reviews by hand.
- The hosting account and Space name.
- Who in the group owns each of: discovery note, frontend, workflow, deployment, pitch.

If something is not specified here and matters, ask before building it. If it does not matter, choose the simplest option and note the choice in the README.
