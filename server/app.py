"""HTTP API. Thin by design: every request names a graph and a step; the engine does the rest.

The server keeps no pipeline state. Datasets live on disk, step results in a
small in-memory cache keyed by the step's settings and everything upstream.
"""
import io
import json
import logging
import os
import time
import zipfile
from importlib.metadata import version
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel, Field

import gazelab
from gazelab import GROUPS, NODES, TABLES, VIEWS, Context, Library, PipelineError, Runner, changes
from gazelab.cli import result_files
from gazelab.datasets import safe_name
from gazelab.pipeline import Cache
from gazelab.readers import READERS, ROLES, read_file
from gazelab.views import select

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("GAZELAB_DATA_DIR", ROOT / "var"))
MAX_UPLOAD = int(os.environ.get("GAZELAB_MAX_UPLOAD_MB", "300")) * 1024 * 1024
TTL_HOURS = float(os.environ.get("GAZELAB_UPLOAD_TTL_HOURS", "168"))
RECORDINGS = (".csv", ".tsv", ".txt", ".dat", ".asc", ".json", ".gz")

log = logging.getLogger("gazelab")
library = Library(examples=ROOT / "examples" / "datasets", uploads=DATA_DIR / "datasets")
runner = Runner(Context(library, max_rows=int(os.environ.get("GAZELAB_MAX_ROWS", "3000000"))),
                Cache(int(os.environ.get("GAZELAB_CACHE_STEPS", "64"))))
described = Cache(256)
library.purge(TTL_HOURS)

app = FastAPI(title="Gaze Lab", version=gazelab.__version__, docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(GZipMiddleware, minimum_size=2000)


@app.exception_handler(PipelineError)
def pipeline_error(request, exc):
    return JSONResponse(status_code=422, content=dict(detail=str(exc)))


class Step(BaseModel):
    graph: dict
    node: str = Field(max_length=80)
    side: str = "output"          # "output" of the step, or its "input"


class TableRequest(Step):
    table: str = Field(max_length=120)
    offset: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=500)
    participant: str = ""
    trial: str = ""


class ViewRequest(Step):
    view: str
    compare: bool = False         # draw the step's input underneath, in grey
    participant: str = ""
    trial: str = ""
    window: list[float] | None = None


class RunRequest(BaseModel):
    graph: dict
    name: str = Field("pipeline", max_length=120)


# ----------------------------------------------------------------------------- describing things

@app.get("/api/health")
def health():
    return dict(status="ok", version=gazelab.__version__)


def example_pipelines():
    out = []
    for path in sorted((ROOT / "examples" / "pipelines").glob("*.json")):
        out.append(dict(id=path.stem, **json.loads(path.read_text())))
    return out


@app.get("/api/catalog")
def catalog():
    """Everything the web app needs to draw itself: steps, their settings, file formats, examples."""
    return dict(
        version=gazelab.__version__, groups=GROUPS, nodes=[n.describe() for n in NODES.values()], tables=TABLES,
        views=[{k: v[k] for k in ("id", "title", "single_trial", "compares")} | dict(needs=list(v["needs"])) for v in VIEWS.values()],
        readers=[r.describe() for r in READERS.values()], roles=ROLES,
        examples=dict(datasets=[d.describe() for d in library.examples()], pipelines=example_pipelines()),
        limits=dict(upload_mb=MAX_UPLOAD // 1024 // 1024, keep_hours=TTL_HOURS),
        packages=dict(pymovements=dict(version=version("pymovements"), url="https://pymovements.readthedocs.io")))


def columns_of(name, frame):
    docs = TABLES.get(name, {}).get("columns", {})
    kinds = dict(f="number", i="number", u="number", b="yes/no")
    return [dict(name=str(c), type=kinds.get(frame[c].dtype.kind, "text"), about=docs.get(str(c), "")) for c in frame.columns]


def tables_of(bundle, before=None):
    if bundle is None:
        return []
    change = {c["table"]: c for c in changes(before, bundle)} if before is not None else {}
    return [dict(name=name, title=TABLES.get(name, {}).get("title", name), about=TABLES.get(name, {}).get("about", ""), rows=len(frame),
                 columns=columns_of(name, frame), change=change.get(name, {}).get("change", "new" if before is None else "same"),
                 detail=change.get(name, {}).get("detail", "")) for name, frame in bundle.tables.items()]


def input_of(result):
    """What a step received: its parent's output, or for a Load step the files as they were read."""
    if result.parent is not None:
        return result.parent
    try:
        return NODES[result.kind].inputs(result.params, runner.ctx) if result.params else None
    except PipelineError:
        return None


def describe(result):
    """One step's state for the app: status, what it reported, which tables and views it offers."""
    key = result.fingerprint + ("" if result.ok else ":" + result.error)
    if result.fingerprint and (hit := described.get(key)):
        return dict(hit, cached=result.cached)
    node, source = NODES[result.kind], input_of(result)
    out = dict(status="ok" if result.ok else "blocked" if result.blocked else "error", error=result.error, ms=result.ms, cached=result.cached,
               fingerprint=result.fingerprint, inputs=tables_of(source), is_source=not node.needs)

    def views_of(bundle):
        return [{k: v[k] for k in ("id", "title", "single_trial", "compares")} for v in VIEWS.values() if bundle is not None and all(t in bundle for t in v["needs"])]

    # the participant and trial pickers follow the output; a step that failed still lets people look at its input
    shown = result.bundle if result.ok else source
    groups = {}
    if shown is not None and "samples" in shown:
        for participant, trial in list(gazelab.trials(shown.samples))[:5000]:
            groups.setdefault(participant, []).append(trial)
    out.update(trials=groups, input_views=views_of(source))
    if hasattr(node, "script") and source is not None and "samples" in source and result.params:
        try:
            out["script"] = node.script(result.params, source)
        except (PipelineError, KeyError):
            pass  # the step itself reports what is wrong with its settings
    if result.ok:
        views = views_of(result.bundle)
        first = node.view if node.view.startswith("table:") or any(v["id"] == node.view for v in views) else (views[0]["id"] if views else "")
        out.update(headline=node.headline(result.bundle), notes=result.notes, tables=tables_of(result.bundle, result.parent or gazelab.Bundle()), views=views, view=first)
    if result.fingerprint:
        described.put(key, out)
    return out


def step(request: Step):
    result = runner.run(request.graph, request.node)[request.node]
    bundle = result.bundle if request.side == "output" else input_of(result)
    if bundle is None:
        raise PipelineError(result.error or "This step has no data yet.")
    return result, bundle


# ----------------------------------------------------------------------------- running and looking

@app.post("/api/run")
def run(request: RunRequest):
    started = time.perf_counter()
    results = runner.run(request.graph)
    return dict(steps={i: describe(r) for i, r in results.items()}, ms=round((time.perf_counter() - started) * 1000))


@app.post("/api/table")
def table(request: TableRequest):
    _, bundle = step(request)
    if request.table not in bundle:
        raise PipelineError(f"There is no table “{request.table}” at this step.")
    frame = bundle[request.table]
    if "samples" in bundle:  # files "as read" have their own columns; only pipeline tables share participant and trial
        frame = select(frame, dict(participant=request.participant, trial=request.trial))
    page = frame.iloc[request.offset:request.offset + request.limit]
    rows = json.loads(page.to_json(orient="values", double_precision=4, date_format="iso"))
    return dict(columns=columns_of(request.table, frame), rows=rows, total=len(frame), offset=request.offset)


@app.post("/api/view")
def figure(request: ViewRequest):
    result, bundle = step(request)
    if request.view not in VIEWS or not all(t in bundle for t in VIEWS[request.view]["needs"]):
        raise PipelineError("This view is not available for this step.")
    before = result.parent if request.compare and request.side == "output" else None
    selection = dict(participant=request.participant, trial=request.trial, window=request.window)
    return VIEWS[request.view]["build"](bundle, selection, before)


@app.post("/api/download")
def download(request: TableRequest):
    _, bundle = step(request)
    if request.table not in bundle:
        raise PipelineError(f"There is no table “{request.table}” at this step.")
    name = safe_name(request.table.replace(":", "").replace(" ", "_")) + ".csv"
    return Response(bundle[request.table].to_csv(index=False), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{name}"'})


RUN_PY = '''"""Re-run this analysis without the web app:  python run.py"""
import os
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
os.chdir(here)
if (here / "plugins").is_dir():
    os.environ.setdefault("GAZELAB_PLUGINS", str(here / "plugins"))
sys.path.insert(0, str(here))

from gazelab.cli import main  # noqa: E402

sys.exit(main(["run", "pipeline.json", "--data", "data", "--out", "results"]))
'''

README = """Gaze Lab analysis: {name}

This folder is a complete, re-runnable copy of the analysis.

  results/       every step's new or changed tables as CSV, plus what each step reported
  results/steps.json   the steps in order, with their settings
  pipeline.json  the pipeline; open it in Gaze Lab to continue working on it
  data/          the recordings and stimulus images the pipeline reads
  gazelab/       the analysis code, exactly as the web app ran it; cleaning and event
                 detection are done by the pymovements package (see gazelab/bridge.py)
  run.py         runs the pipeline again and rewrites results/

To re-run:   pip install -r requirements.txt   then   python run.py

Open the CSV files in results/ directly in JASP (File > Open), jamovi, R or a spreadsheet.
Example datasets shipped with Gaze Lab are simulated; they support no scientific conclusion.
"""


@app.post("/api/export")
def export(request: RunRequest):
    """A zip with the results and everything needed to reproduce them without this server."""
    results = runner.run(request.graph)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("pipeline.json", json.dumps(dict(name=request.name, graph=request.graph), indent=2, ensure_ascii=False))
        for name, text in result_files(request.graph, results):
            bundle.writestr(f"results/{name}", text)
        datasets = {r.params["source"]["dataset"] for r in results.values() if r.kind == "load" and r.params.get("source", {}).get("dataset")}
        for dataset_id in datasets:
            try:
                dataset = library.get(dataset_id)
            except PipelineError:
                continue
            for path in sorted(dataset.root.rglob("*")):
                if path.is_file() and not path.name.startswith("."):
                    bundle.write(path, f"data/{dataset_id}/{path.relative_to(dataset.root)}")
        package = Path(gazelab.__file__).parent
        for path in sorted(package.rglob("*.py")):
            bundle.write(path, f"gazelab/{path.relative_to(package)}")
        plugins = os.environ.get("GAZELAB_PLUGINS")
        for path in sorted(Path(plugins).glob("*.py")) if plugins and Path(plugins).is_dir() else []:
            bundle.write(path, f"plugins/{path.name}")
        bundle.writestr("run.py", RUN_PY)
        bundle.writestr("requirements.txt", "".join(f"{p}=={version(p)}\n" for p in ("numpy", "pandas", "scipy", "pymovements")))
        bundle.writestr("README.txt", README.format(name=request.name))
    filename = safe_name(request.name.replace(" ", "-").lower(), "pipeline") + ".zip"
    return Response(archive.getvalue(), media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# ----------------------------------------------------------------------------- datasets

async def store(upload: UploadFile, target: Path, budget: int):
    """Write an upload to disk in pieces, refusing to exceed the size budget. Returns bytes written."""
    written = 0
    with target.open("wb") as handle:
        while chunk := await upload.read(1024 * 1024):
            written += len(chunk)
            if written > budget:
                handle.close()
                target.unlink(missing_ok=True)
                raise HTTPException(413, f"Uploads are limited to {MAX_UPLOAD // 1024 // 1024} MB per dataset on this server.")
            handle.write(chunk)
    return written


def editable(dataset_id):
    dataset = library.get(dataset_id)
    if dataset.example:
        raise HTTPException(403, "Example datasets cannot be changed. Upload your own files instead.")
    return dataset


async def add_files(dataset, files):
    budget = MAX_UPLOAD - sum(p.stat().st_size for p in dataset.root.rglob("*") if p.is_file())
    for upload in files:
        name = safe_name(upload.filename or "recording.csv")
        if not name.lower().endswith(RECORDINGS):
            raise HTTPException(415, f"“{name}” is not a recording this server can read. Use CSV/TSV/text, EyeLink .asc or Tobii livedata.json(.gz).")
        stem, suffix = (name[:-len(".json.gz")], ".json.gz") if name.lower().endswith(".json.gz") else (Path(name).stem, Path(name).suffix)
        n = 1
        while (dataset.root / name).exists():
            n += 1
            name = f"{stem}-{n}{suffix}"
        budget -= await store(upload, dataset.root / name, budget)
        dataset.info["files"].append(dict(name=name, label=dataset.unique_label(stem)))
    dataset.save()
    return dataset.describe()


@app.post("/api/datasets")
async def create_dataset(files: list[UploadFile] = File(...)):
    library.purge(TTL_HOURS)
    dataset = library.create(Path(files[0].filename or "My recording").stem if len(files) == 1 else f"{len(files)} recordings")
    try:
        return await add_files(dataset, files)
    except Exception:
        library.delete(dataset.id)
        raise


@app.post("/api/datasets/{dataset_id}/files")
async def more_files(dataset_id: str, files: list[UploadFile] = File(...)):
    return await add_files(editable(dataset_id), files)


class Label(BaseModel):
    label: str = Field(min_length=1, max_length=60)


@app.patch("/api/datasets/{dataset_id}/files/{name}")
def relabel(dataset_id: str, name: str, body: Label):
    dataset = editable(dataset_id)
    entry = next((f for f in dataset.files if f["name"] == name), None)
    if entry is None:
        raise HTTPException(404, "No such file in this dataset.")
    entry["label"] = ""
    entry["label"] = dataset.unique_label(body.label.strip())
    dataset.save()
    return dataset.describe()


@app.delete("/api/datasets/{dataset_id}/files/{name}")
def remove_file(dataset_id: str, name: str):
    dataset = editable(dataset_id)
    dataset.path(name).unlink()
    dataset.info["files"] = [f for f in dataset.files if f["name"] != name]
    dataset.save()
    return dataset.describe()


@app.post("/api/datasets/{dataset_id}/stimuli")
async def add_stimuli(dataset_id: str, files: list[UploadFile] = File(...)):
    """Stimulus images. An image is matched to trials by its file name (without extension)."""
    dataset = editable(dataset_id)
    (dataset.root / "stimuli").mkdir(exist_ok=True)
    for upload in files:
        content = await upload.read(20 * 1024 * 1024 + 1)
        try:
            with Image.open(io.BytesIO(content)) as image:
                if len(content) > 20 * 1024 * 1024 or image.format not in ("PNG", "JPEG", "WEBP") or image.width * image.height > 40_000_000:
                    raise ValueError
                clean = image.convert("RGB")
        except Exception:
            raise HTTPException(415, f"“{upload.filename}” is not a PNG, JPEG or WebP image of reasonable size.") from None
        name = safe_name(Path(upload.filename or "stimulus").stem)
        clean.save(dataset.root / "stimuli" / f"{name}.png", optimize=True)
        dataset.info.setdefault("stimuli", {})[name] = f"stimuli/{name}.png"
    dataset.save()
    return dataset.describe()


@app.delete("/api/datasets/{dataset_id}/stimuli/{name}")
def remove_stimulus(dataset_id: str, name: str):
    dataset = editable(dataset_id)
    if name in dataset.stimuli:
        dataset.path(dataset.info["stimuli"].pop(name)).unlink(missing_ok=True)
        dataset.save()
    return dataset.describe()


@app.get("/api/datasets/{dataset_id}")
def get_dataset(dataset_id: str):
    return library.get(dataset_id).describe()


@app.delete("/api/datasets/{dataset_id}")
def delete_dataset(dataset_id: str):
    library.delete(dataset_id)
    return dict(deleted=True)


@app.get("/api/datasets/{dataset_id}/stimuli/{name}")
def stimulus(dataset_id: str, name: str):
    dataset = library.get(dataset_id)
    if name not in dataset.stimuli:
        raise HTTPException(404, "No such stimulus image.")
    return FileResponse(dataset.path(dataset.stimuli[name]), headers={"Cache-Control": "private, max-age=3600"})


class Probe(BaseModel):
    reader: str = "auto"
    options: dict = {}


@app.post("/api/datasets/{dataset_id}/probe")
def probe(dataset_id: str, body: Probe):
    """Read the first file and report what was found: the format, the columns and a proposed mapping."""
    dataset = library.get(dataset_id)
    if not dataset.files:
        raise PipelineError("This dataset has no recording files yet.")
    reader, raw = read_file(dataset.path(dataset.files[0]["name"]), body.reader, body.options)
    frame = raw.frame
    examples = frame.head(200)
    columns = [dict(name=c, type="number" if frame[c].dtype.kind in "fiu" else "text",
                    example=next((f"{v:.5g}" if isinstance(v, float) else str(v)[:24] for v in examples[c] if pd.notna(v)), "")) for c in frame.columns]
    suggestion = reader.suggest(raw)
    defaults = dataset.info.get("defaults", {})
    suggestion["params"] = {**suggestion["params"], **{k: v for k, v in defaults.items() if k != "source"}}
    if "source" in defaults:
        suggestion["mapping"] = {**suggestion["mapping"], **defaults["source"].get("mapping", {})}
    return dict(reader=reader.id, options=reader.clean(body.options), columns=columns, rows=len(frame), notes=raw.notes, suggestion=suggestion,
                markers=0 if raw.events is None else len(raw.events))


# ----------------------------------------------------------------------------- the web app itself

DIST = ROOT / "frontend" / "dist"
if DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Unknown API endpoint.")
        file = (DIST / path).resolve()
        return FileResponse(file if path and file.is_relative_to(DIST) and file.is_file() else DIST / "index.html")
