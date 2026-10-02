# Notes for Claude Code

This repository is a working MVP. Read `README.md` and `docs/ARCHITECTURE.md` first.

## Ground rules

- Every model call returns a validated Pydantic record. Never parse free text from a model.
- No number shown on screen is computed by a model. Arithmetic lives in `fitradar/aggregate.py` and `fitradar/cost.py`.
- When the system cannot answer, it says so on screen. Do not add fallbacks that guess.
- Settings belong in `config.py`. Do not hard-code model names, prices or thresholds elsewhere.
- Storage goes through `fitradar/store.py` only.
- Keep the front end as plain HTML, CSS and JavaScript in `web/`. No framework, no build step.
- Screen wording is plain English for a non-technical category team.
- All bundled data is invented. Do not present it as real.

## Before changing a prompt

Run `python -m fitradar.accuracy`, change the prompt, run a model pass, run the accuracy test again. Keep the change only if the score rises. Log it in `prompts/CHANGELOG.md`.

## Checks

`pytest` must pass. It needs no API key.

## Likely first tasks

1. Run the pipeline with a real key and fix anything the live service rejects (`docs/MODEL_OPTIONS.md`, "Not yet tested").
2. Fill in the comparison table in `docs/MODEL_OPTIONS.md`.
3. Deploy (`docs/DEPLOYMENT.md`).
