# Extending Gaze Lab

Everything the app shows about a step — its place in the library, the
explanation, the settings form, the error when an earlier step is missing, the
code view — is read from one Python class. Adding a step, a file format or a
figure means adding one class or function. No other file changes: not the
server, not the web app, not the export.

| To add | Write | Where |
| --- | --- | --- |
| a step | a `Node` subclass with `@register` | `gazelab/nodes/*.py` or `plugins/*.py` |
| a file format | a `Reader` subclass with `@reader` | `gazelab/readers/*.py` or `plugins/*.py` |
| a figure | a function with `@view` | `gazelab/views.py` or `plugins/*.py` |
| a description of a new table | one `table(...)` call | next to the step that creates it |

Modules in `gazelab/nodes/` and `gazelab/readers/` are imported automatically.
Files in the plug-in folder (`plugins/`, or wherever `GAZELAB_PLUGINS` points)
are loaded the same way at start-up, which is the easiest route on a running
server: see `plugins/_example_velocity_filter.py`.

## How data moves

A pipeline is a tree: every step continues from exactly one earlier step, and
a step may have several followers (branches). What travels along a connection
is a **bundle**:

```python
data.samples                 # the samples table (a pandas DataFrame)
data["fixations"]            # any other table by name
"blinks" in data             # is a table there?
data.meta["px_per_deg"]      # facts about the recording: width_px, height_px, sampling_hz, experiment, dataset, stimuli, pupil_unit
data.notes                   # what the steps so far reported
```

A step never changes the bundle it receives. It returns a new one:

```python
return data.update("What I did, in one sentence.", samples=new_samples, my_table=frame)
```

`update` replaces or adds the named tables and shares all others, so long
pipelines stay cheap. `data.without("saccades")` drops a table. Because of
this rule, branches can never disturb each other and results can be cached.

### The tables every step can rely on

`samples` always exists and has one row per measurement:

| Column | Meaning |
| --- | --- |
| `participant`, `trial` | text labels; all work is done within these groups |
| `time` | milliseconds on the recording clock |
| `x`, `y` | gaze in pixels, origin top left; `NaN` when missing |
| `pupil` | pupil size as recorded; `NaN` when missing or absent |
| `masked`, `filled` | `True` where a cleaning step removed or estimated the value |
| `condition`, `stimulus` | optional labels of the trial |
| anything else | extra columns the person chose to keep in the Load step |

Conventions for tables you create: start with `participant` and `trial`; give
times in milliseconds **from the start of the trial** (`start`, `end`,
`duration`); never delete sample rows to mark bad data, set values to `NaN`
instead, so that time keeps running evenly. Helpers in `gazelab`:
`trials(samples)` (row positions per participant and trial), `runs(mask)`,
`sample_period(time)`, `with_trial_info(table, samples)` (adds condition and
stimulus), `num(n)` (a count formatted for reading).

## A step

```python
from gazelab import Choice, Node, Number, PipelineError, num, register, table

table("dwell_runs", "Dwell runs", "One row per uninterrupted stay in an area.",
      duration="Length of the stay in ms.")          # shown as column help in the app


@register
class MyStep(Node):
    kind = "my_step"                 # stored in pipeline files: never rename it later
    title = "Do something useful"    # what people see
    group = "clean"                  # input · prepare · clean · detect · aoi · summarise
    icon = "waves"                   # a name from frontend/src/icons.js; unknown names get a box
    summary = "One line for the step library."
    explain = """
        What the step does and why, for a student who has never heard of it.
        Blank lines separate paragraphs; **bold**, *italic*, `code` and
        lines starting with "- " (a list) are formatted.
    """
    question = "Something to think about while changing the settings."
    needs = ("samples", "fixations")  # tables that must exist; the app tells people what to add
    makes = ("dwell_runs",)           # tables this step creates (it may change others too)
    view = "signal"                   # the figure opened first; "table:dwell_runs" opens a table
    params = (
        Number("limit", "Longest stay", 500, unit="ms", min=0, max=10000, step=50, help="Shown under the field."),
        Choice("mode", "Mode", "strict", options=(("strict", "Strict"), ("loose", "Loose"))),
    )

    def run(self, data, p, ctx):
        if p["limit"] == 0:
            raise PipelineError("The longest stay must be more than 0 ms.")   # shown on the step, in these words
        ...
        return data.update(f"{num(len(frame))} stays found.", dwell_runs=frame)
```

Things worth knowing:

- **Settings** are validated before `run` is called; `p` holds clean values.
  Available kinds: `Number`, `Choice`, `Toggle`, `Text` (`multiline=True` for
  a text area), `Columns` (pick columns of an input table; `pattern="aoi hit*"`
  pre-selects by name), `TableName`, and `Custom` for a setting with its own
  editor. `when=dict(mode="strict")` shows a setting only while another one
  has that value. `unit=dict(ms="ms", samples="samples"), unit_from="count_in"`
  makes the unit label follow another setting.
- **Errors people can fix** are `PipelineError`s with a sentence that says
  what to do. Any other exception is reported on the step as unexpected and
  logged with its traceback; the rest of the pipeline keeps working.
- **The card text** of a step ("531 fixations") comes from `headline(out)`;
  the default counts the rows of the first table in `makes`.
- **The code view** shows the source of `run`. Write it to be read.
- **Do not write the mathematics yourself if a package has it.** Steps that
  clean or detect use pymovements; see the next section.
- A step with `needs = ()` starts a pipeline (like Load). It may implement
  `inputs(p, ctx)` to show what it reads, and `stamp(p, ctx)` to say when its
  result must be recomputed although its settings did not change.

## A step that uses pymovements

Cleaning and event detection are not implemented in Gaze Lab. Those steps are
`GazeStep`s (`gazelab/bridge.py`): they list the calls to make on a
pymovements `Gaze` object and say what to keep of the result.

```python
from gazelab import register
from gazelab.bridge import GazeStep, call, events_table


@register
class FixationsHMM(GazeStep):
    kind = "fixations_ihmm"
    title = "Detect fixations with a hidden Markov model (I-HMM)"
    group = "detect"
    summary = "…"
    explain = """…"""
    makes = ("fixations",)

    def calls(self, p, data):
        return [
            call("pix2deg"),
            call("pos2vel", "savitzky_golay", window_length=5, degree=2),
            call("detect", "ihmm"),
            call("compute_event_properties", [("location", {"position_column": "pixel"})], name="fixation"),
        ]

    def keep(self, data, gaze, p):
        fixations = events_table(gaze, "fixation", data.samples, "fixation")
        return data.update(f"{len(fixations)} fixations.", fixations=fixations)
```

Because the calls are data, three things follow without more code: the app
runs them, the inspector prints them as a script that works outside the app
(with the experiment definition and the current settings filled in), and a
test can check that the two agree
(`test_the_script_shown_for_a_step_reproduces_it_without_gaze_lab` runs over
every `GazeStep`).

The bridge does the conversions in one place:

- `to_gaze(data)` builds the `Gaze` from the samples table, with participant
  and trial as trial columns and the experiment from `data.meta["experiment"]`
  (set by the Load step). pymovements needs whole milliseconds, so time is rounded.
- `cleaned_samples(gaze, samples)` copies gaze and pupil back and flags what
  pymovements emptied as `masked`; `speed(gaze)` gives gaze speed in °/s.
- `events_table(gaze, name, samples, number)` turns events into a table with
  times in milliseconds from the start of the trial.
- `compute_event_properties` is evaluated for all events in one pass. Called
  directly, pymovements filters the whole recording once per event, which
  takes minutes on a long recording. The measure expressions are still
  pymovements' own and the numbers are identical.

When pymovements raises, the step shows which call stopped and why.

A setting with its own editor needs one more piece in the web app: a
component, registered in the `special` map of
`frontend/src/components/ParamForm.vue`. The AOI drawing tool
(`control="aois"`) and the recording chooser (`control="source"`) work this way.

## A file format

```python
from gazelab.readers import Raw, Reader, reader


@reader
class MyTracker(Reader):
    id = "my_tracker"
    title = "MyTracker export"
    about = "How to export the file from the manufacturer's software."
    extensions = (".txt",)
    options = ()                      # Param objects, shown under “File format”

    def sniff(self, path, head):      # 0–1: how sure are you that this file is yours?
        return 0.9 if head.startswith("## MyTracker") else 0.0

    def read(self, path, o):
        frame = ...                   # one row per sample, columns as in the file
        events = ...                  # optional: time (same unit as the samples), label, value
        return Raw(frame, events, notes=["What was done while reading."],
                   hints=dict(time_unit="ms", gaze_unit="px", width_px=1920, height_px=1080))
```

The reader returns the file "as read". Which column means what is decided
afterwards by the column mapping, which the reader can pre-fill by overriding
`suggest(raw)`; by default, column names are matched against the aliases in
`gazelab/readers/__init__.py` (add yours there if the format is just a table
with unusual names). `hints` pre-fill the settings of the Load step.

## A figure

```python
from gazelab import view
from gazelab.views import select


@view("dwell_hist", "Stay lengths", needs=("dwell_runs",), single_trial=False)
def dwell_hist(data, sel, before=None):
    rows = select(data["dwell_runs"], sel)          # the chosen participant / trial, or all
    return dict(data=[dict(type="histogram", x=rows["duration"].tolist())],
                layout=dict(xaxis=dict(title=dict(text="Stay (ms)"))),
                info=dict(title=f"{len(rows)} stays", hint="Shown beside the title."))
```

A view returns a [Plotly](https://plotly.com/javascript/) figure as plain
dictionaries; the web app adds fonts and colours. It appears on every step
whose output holds the tables in `needs`. With `compares=True` the view also
receives the step's input as `before` and can draw it underneath. The web app
bundles Plotly's cartesian chart types (lines, bars, histograms, heat maps,
images); 3D and maps are not included.

## Testing what you add

`tests/conftest.py` has two helpers that keep tests short: `recording()`
builds a small recording with three known fixations and a blink, and the
`workspace` fixture turns any table into a dataset and a ready Load step:

```python
def test_my_step(workspace):
    runner, load = workspace(recording())
    result = runner.run(chain(load, ("fixations_ivt", dict(threshold=30)), ("my_step", {})))["n2"]
    assert result.ok, result.error
    assert len(result.bundle["dwell_runs"]) == 3
```

`tests/test_engine.py` already checks every registered step for an
explanation, a question and valid defaults, so a new step is covered by that
test the moment it is registered.

## Running pipelines without the web app

```sh
python -m gazelab steps                              # what is available
python -m gazelab run pipeline.json --data data --out results
```

`--data` is a folder that contains one folder per dataset, each with a
`dataset.json` (see any folder in `examples/datasets/`). This is exactly what
the zip from “Export results” contains, and `run.py` in that zip calls it.

```python
from gazelab import run_pipeline
results = run_pipeline("pipeline.json", data="data")
fixations = results["s4"].bundle["fixations"]        # by step id
```
