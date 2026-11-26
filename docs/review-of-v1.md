# Review of version 1 and what changed

Version 1 (kept in `legacy/gaze-lab-v1/`) worked and was tested: 33 tests
passed. The review below is about what made it hard to extend, to deploy and
to use for real data. File references point into `legacy/gaze-lab-v1/`.

## Findings

### Structure

| # | Finding | Where | Now |
| --- | --- | --- | --- |
| 1 | A step was defined in three places: a JSON manifest, a Python handler and per-step special cases in the web app (32 `kind === …` checks) and the server (`node["kind"] == "view"`, hard-coded table columns). Adding a step meant touching all of them. | `shared/nodes.json`, `backend/nodes/`, `frontend/src/App.vue`, `backend/main.py` | One Python class per step. Library, form, validation, error texts, code view and export are derived from it. |
| 2 | The data model had fixed slots (`fixations`, `blinks`, `aois`, `stats`, `baseline_corrected`). A new kind of result (saccades, transitions) needed a change to the model, the summary, the downloads, the export and the preview. | `backend/model.py` | A bundle of named tables. A step adds a table; tables, downloads, export and change reports are generic. |
| 3 | Loading was not a step. Dataset, column mapping, units and screen size were 20 fields of every request, and the request object was modified in place while reading them. A saved pipeline did not say which data it belonged to. | `backend/main.py` (`RunRequest`, `source_data`) | Load is an ordinary step whose settings hold the dataset, format, mapping and geometry. A pipeline file is complete. |
| 4 | Simulation lived inside the engine: a `simulate_blinks` flag travelled through every request and injected artificial blinks into loaded data. | `backend/engine.py` (`inject_teaching_blinks`) | The example data are generated once by `examples/generate.py`, with blinks in them. The engine only analyses. |
| 5 | The reproducible export was made by reading the engine's source files, stripping imports with `ast` and concatenating them into one script. Any helper in another module broke it silently. | `backend/standalone.py`, `backend/export.py` | The zip contains the `gazelab` package itself and a five-line `run.py`. A test re-runs the export and compares every table. |
| 6 | The web app was one 2 400-line component and a 4 800-line stylesheet. Four overlapping places showed data (output panel, raw data tab, inspect tab, compare tab), with two navigation bars leading to them. | `frontend/src/App.vue`, `style.css` | 15 components, the largest 175 lines; 300 lines of CSS. One data panel with Input and Output. |

### Behaviour

| # | Finding | Where | Now |
| --- | --- | --- | --- |
| 7 | Every request re-ran the whole pipeline from the CSV: the run, each download, each figure, the code view, the export. The test suite took 114 s. | `backend/main.py` | Results are cached per step by a fingerprint of its settings and everything upstream. Changing a setting recomputes only what depends on it. The suite takes 6 s. |
| 8 | One failing step failed the whole request, so nothing was shown. | `execute_graph` | A failing step shows its error; steps after it wait; other branches are unaffected. |
| 9 | Uploads lived in the memory of one process: at most 8 datasets of 8 MB and 250 000 rows, gone after an hour or a restart, and a second worker process could not see them. A class of 30 would hit “the upload store is full”. | `backend/main.py`, `stimuli.py`, `event_store.py` | Uploads are folders on disk with configurable size, row and retention limits; several workers share them. |
| 10 | Only EyeLink ASC and generic CSV could be read; there was no Tobii support. One file per dataset, so one participant per upload. | `backend/importers.py` | Readers are plug-ins: Tobii Pro Lab export, raw Glasses 2 `livedata.json.gz`, EyeLink, generic CSV. Several files per dataset. |
| 11 | Thresholds were in pixels only, so settings could not be compared between set-ups; no saccades; I-VT without merging of split fixations. | `backend/nodes/gaze.py` | Thresholds in degrees from the viewing geometry; a saccade step (Engbert & Kliegl) with amplitude and peak velocity. Merging is still missing, because pymovements has none that respects trials. |
| 12 | AOI analysis produced dwell time and fixation count only, and left out trials in which an area was not looked at (a bias when averaging). No transitions or sequences. | `backend/nodes/gaze.py` | Dwell, count, visits, time to first fixation, first fixation duration, with explicit zero rows; transition counts; visit sequences and n-step patterns. |
| 13 | The teaching data had no blinks, no saccade dynamics, 3 participants, and referred to stimulus images that did not exist. | `data/raw_data.csv`, `data/trials.csv` | Three simulated datasets in real export formats, with images, known true fixations and built-in effects. |

### Smaller things

- Unused code suggesting generated boilerplate: `aoi_definitions = context.aois`
  at the top of every preprocessing handler, unused imports of `savgol_filter`
  and `pandas`, “compatibility aliases” nobody used (`backend/nodes/*.py`,
  `backend/engine.py`).
- Graph validation was written twice (`execution_graph` and `validate_graph`).
- `/api/bootstrap` read a hard-coded `data/raw_data.csv` whatever dataset was active.
- The AOI file used an undocumented convention (for circles, `width` was the
  radius), converted in `backend/cases.py`.
- A hard-coded avatar “LH” and a marketing headline took the top of the screen.
- Docker: no health check, no volume, no settings, a root file system that
  was writable, and no deployment guide.

## Decisions that reverse earlier ones

**`pymovements` stays, and does more than in version 1.** An intermediate
draft of version 2 replaced it with detectors written here in NumPy. That was
reversed: students should be able to take the code of a step into their own
scripts, and for that the code has to be a package they can install, not this
project's own implementation. Off-screen removal, blink detection, smoothing,
pixel-to-degree conversion, velocity, I-VT, I-DT, saccade detection, event
properties and EyeLink parsing are all pymovements calls now (version 1 used it
for I-VT, I-DT, blinks and EyeLink). Each such step prints its calls as a
script with the current settings, and a test runs every script against the
step's own result.

What that costs, and what was found on the way:

- The Docker image is about 1 GB instead of 0.5 GB (pymovements brings Polars,
  PyArrow, Matplotlib and scikit-learn).
- pymovements 0.28 computes event properties and empties event samples one
  event at a time, by filtering the whole recording. On 1.1 million samples
  the pipeline took more than two minutes. `gazelab/bridge.py` evaluates the
  same two operations in one pass (10 seconds for the same pipeline) and a
  test checks the results against pymovements.
- Its I-DT needs evenly spaced whole-number timestamps and a duration that is
  a whole number of samples. The step builds such a clock (milliseconds where
  the tracker's period is a whole number of ms, sample counts otherwise) and
  reports what the duration became.
- Its I-DT ends each fixation on the sample that broke the dispersion limit,
  one sample into the saccade. The step says so and does not report the
  dispersion of I-DT fixations.
- It has no merging of fixations split by noise (its
  `merge_subsequent_close_events` ignores trial borders and position), no gap
  filling with a length limit, no pupil baseline and no pupil smoothing. The
  first and the last are therefore not offered; gap filling and baseline
  correction are the two cleaning steps still written here.
- Thresholds are in degrees only, as pymovements works; the pixel option is gone.

**Visualise is no longer a step.** Every step shows figures of its own output,
so a separate step added nothing. Figures are Plotly descriptions built in
Python (`gazelab/views.py`), which removed Matplotlib and the duplicate
plotting code in the web app.

**External event files were dropped.** Version 1 could attach a separate CSV
of events to a dataset. Markers now come from the recording itself (Tobii
events, EyeLink messages, Glasses 2 API events). Conditions that live in a
separate log are added with the step *Add trial information*. If separate
event files with timestamps are needed again, that is a reader or a step, not
a change to the engine.

## Numbers

| | Version 1 | Version 2 |
| --- | --- | --- |
| Python (engine and server) | 1 800 lines | 3 700 lines, with 20 steps instead of 9, 4 file formats instead of 2, and the figures that used to be JavaScript |
| Web app | 6 100 lines JS/Vue, 4 800 CSS | 1 300 lines JS/Vue, 300 CSS |
| Places to edit to add a step | 3 or more | 1 |
| Test suite | 33 tests, 114 s | 81 tests, 6 s |
| Python dependencies | FastAPI, pandas, NumPy, SciPy, pymovements (Polars, PyArrow), Matplotlib, Pillow | FastAPI, pandas, NumPy, SciPy, pymovements (Polars, PyArrow, Matplotlib), Pillow |
