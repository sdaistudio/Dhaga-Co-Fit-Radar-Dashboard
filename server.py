"""Fit Radar web server: a small JSON API plus the static front end in web/.

Run locally:  uvicorn server:app --reload --port 7860
"""
import threading
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import config
from fitradar import store
from fitradar.graph import STEPS, run_pipeline
from fitradar.ingest import BadFile

app = FastAPI(title="Fit Radar")
STATUS = {"running": False, "step": 0, "note": "", "error": ""}
UPLOADS = config.RUNS_DIR / "uploads"
LOCK = threading.Lock()


def _paths():
    c, u = UPLOADS / "comments.csv", UPLOADS / "units_sold.csv"
    uploaded = c.exists() and u.exists()
    return (c, u, True) if uploaded else (config.DATA_DIR / "comments.csv", config.DATA_DIR / "units_sold.csv", False)


def _reader_label(provider: str, models: dict | None = None) -> str:
    models = models or config.MODELS.get(provider, {})
    if provider == "offline":
        return "Offline keyword rules (no model, no cost)"
    return f"{models.get('fast', '?')} + {models.get('strong', '?')}"


@app.get("/api/state")
def state():
    run = store.load_run()
    provider = config.resolve_provider()
    comments, units, uploaded = _paths()
    return {"run": run, "tags": store.tags(), "actions": store.actions(), "status": STATUS, "steps": STEPS,
            "next_provider": provider, "next_reader": _reader_label(provider),
            "run_reader": _reader_label(run["provider"], run.get("models")) if run else "",
            "stand_in": not uploaded, "has_saved_run": (config.RUNS_DIR / "latest" / "run.json").exists()}


@app.get("/api/status")
def status():
    return STATUS


def _work():
    def progress(step, note=""):
        STATUS.update(step=step, note=note)
    try:
        comments, units, _ = _paths()
        run_pipeline(progress=progress, comments_path=comments, units_path=units)
        STATUS.update(step=8, note="", error="")
    except BadFile as error:
        STATUS.update(error=str(error))
    except Exception as error:                      # shown on screen as a sentence, never as a traceback
        STATUS.update(error=f"The run stopped at step {STATUS['step']}: {type(error).__name__}. Nothing was lost. Press Run to try again.")
    finally:
        STATUS.update(running=False)


@app.post("/api/run")
def run():
    with LOCK:
        if STATUS["running"]:
            raise HTTPException(409, "A run is already in progress.")
        STATUS.update(running=True, step=0, note="", error="")
    threading.Thread(target=_work, daemon=True).start()
    return STATUS


class Tag(BaseModel):
    comment_id: str
    tag: str | None = None


@app.post("/api/tag")
def tag(body: Tag):
    return store.set_tag(body.comment_id, body.tag)


class Action(BaseModel):
    key: str
    decision: str | None = None      # "ok", "back" or None to undo
    fix: str = ""
    label: str = ""


@app.post("/api/action")
def action(body: Action):
    return store.set_action(body.key, body.decision, body.fix, body.label)


@app.post("/api/upload")
async def upload(comments: UploadFile = File(...), units: UploadFile = File(...)):
    UPLOADS.mkdir(parents=True, exist_ok=True)
    (UPLOADS / "comments.csv").write_bytes(await comments.read())
    (UPLOADS / "units_sold.csv").write_bytes(await units.read())
    return {"ok": True}


@app.post("/api/use-bundled")
def use_bundled():
    for name in ("comments.csv", "units_sold.csv"):
        (UPLOADS / name).unlink(missing_ok=True)
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(Path(config.WEB_DIR) / "index.html")


app.mount("/", StaticFiles(directory=config.WEB_DIR), name="web")
