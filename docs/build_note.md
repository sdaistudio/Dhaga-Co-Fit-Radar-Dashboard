# Build note

Two pages at most. Sections marked **[TO COMPLETE]** need a live run with a real API key.

## Code versus model

Every step is either code or a model call. Models do judgement, language and messy mapping. They never do arithmetic, comparison or lookup.

| # | Step | Done by | Pattern | Why |
|---|---|---|---|---|
| 1 | Load, clean, tidy sizes, drop blanks and duplicates | Code | – | Exact, free, testable |
| 2 | Read every comment in batches of 20 | Fast model, temperature 0 | Parallelization | Hinglish free text is language work; volume needs concurrency |
| 3 | Re-read unclear comments | Strong model, temperature 0 | Routing | Judgement on ambiguity is worth a dearer call on a minority |
| 4 | Send the still-unclear to a person | Code | Routing | A visible gap beats a silent wrong answer |
| 5 | Compute rates, compare to the category median, flag | Code | Prompt chaining (middle link) | Arithmetic and comparison: never a model |
| 6 | Write each finding | Strong model, temperature 0.3 | Prompt chaining | Plain-language output needs a model, fed only step 5's numbers and quotes |
| 7 | Check each finding; send failures back to step 6 once | Fast model, temperature 0, plus code | Evaluator-optimizer | Figures and claims are verified before anyone sees them |

## Why each pattern is there, and what breaks without it

| Pattern | Where | Without it |
|---|---|---|
| Parallelization | Step 2: batches run side by side (`MAX_CONCURRENCY` in `config.py`) | One call at a time, a week's 11,800 comments take too long to run while Neha waits |
| Routing | Steps 3 and 4: under 70% sure, or two reasons, goes to the strong model; still unsure goes to a person | Either every comment goes to the strong model (dearer) or unclear ones are guessed (wrong answers, shown as fact) |
| Prompt chaining | Steps 2, 5, 6: the writer sees only the numbers code produced | The writer is free to calculate or invent figures that nobody checked |
| Evaluator-optimizer | Step 7: code matches every number to the data; the fast model checks every claim against the quotes; one rewrite | An invented figure or an unsupported claim reaches the category team |

## Cost

Prices (US dollars per million tokens, input / output): fast 1.00 / 5.00, strong 2.00 / 10.00. Rupees at 88 to the dollar. All in `config.py`.

**Planning estimate** (from the build specification, before any measured run): about $0.00045 per comment read, $0.0023 per re-read, $0.018 per finding written and checked. For 2,000 comments with 15% re-read and 5 findings, about $1.63. At the weekly volume of about 11,800 comments (6,547 "Other" returns plus an estimated 5,256 new reviews), about $10.30, roughly Rs 906 a week. The review figure is an estimate.

**Measured** **[TO COMPLETE]** after the first live run. Copy from the Run and cost tab:

| Line | Calls | Tokens in | Tokens out | Seconds | Dollars |
|---|---|---|---|---|---|
| Fast model: read comments | | | | | |
| Strong model: re-read unclear comments | | | | | |
| Strong model: write findings | | | | | |
| Fast model: check findings | | | | | |
| **This run** | | | | | |
| **Weekly, scaled to 11,804 comments** | | | | | |

The committed demo run (`data/demo_run/run.json`) was made with the offline keyword rules, so its cost is zero and its seconds are not a measure of a model.

## Accuracy

Target: 85% agreement with the 300 hand labels (`python -m fitradar.accuracy`).

| Reader | Prompt version | Checked | Agreement | Weakest reason |
|---|---|---|---|---|
| Claude fast + strong | **[TO COMPLETE]** | | | |

The offline keyword rules score highly on the stand-in data only because the rules were written for it. That score is not reported here.

Every prompt version and its score is logged in `prompts/CHANGELOG.md`. Half of the hand labels should be held back as a test set that prompt revisions are not tuned on. **[TO COMPLETE]** Record which half.

## How this build differs from the build specification

| Specification | This build | Why |
|---|---|---|
| Streamlit front end (`app.py`) | Plain HTML, CSS and JavaScript in `web/`, served by FastAPI (`server.py`) | **[TO COMPLETE]** the group's reason |
| Separate modules for classify, route, evaluate and pipeline | One LangGraph state graph in `fitradar/graph.py`; the four patterns are its nodes and conditional edges | The patterns are visible as the graph's shape |
| Anthropic SDK directly | LangChain `with_structured_output`, so Claude or GPT can fill either role | Lets the model comparison in `docs/MODEL_OPTIONS.md` run on the same pipeline |
| `reviews.csv` and `return_comments.csv` | One `comments.csv` with a `source` column (`review` or `return`) | The combined table is what step 1 produces anyway |
| Reviews read in three batches by age | Not built: the whole file is read in one run | **[TO COMPLETE]** |
| `confidence` limited to 0 to 1 in the schema | Clamped to 0 to 1 in code after the reply | **[TO COMPLETE]** confirm whether the provider accepts the limit in the schema |

## The thing that broke that we did not expect

**[TO COMPLETE]**
