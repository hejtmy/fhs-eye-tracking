"""The whole extension contract: Bundle (data on a wire), Param (one setting), Node (one step).

Everything the web app shows about a step (title, explanation, settings form,
required inputs, code) is read from the Node class itself, so adding a step
means adding one class and nothing else.
"""
from __future__ import annotations

import copy
import fnmatch
import inspect
import textwrap
from dataclasses import dataclass, field, fields

import numpy as np
import pandas as pd

KEYS = ["participant", "trial"]

# Stages of an analysis, in the order they appear in the step library.
GROUPS = [
    dict(id="input", title="Load", hint="Bring a recording in and say what its columns mean."),
    dict(id="prepare", title="Prepare", hint="Define trials and conditions."),
    dict(id="clean", title="Clean", hint="Deal with blinks, gaps and noise."),
    dict(id="detect", title="Detect events", hint="Turn samples into fixations and saccades."),
    dict(id="aoi", title="Areas of interest", hint="Say which regions matter and what was looked at."),
    dict(id="summarise", title="Summarise", hint="Reduce to tables you can take to JASP, jamovi or R."),
]


class PipelineError(ValueError):
    """A problem the person building the pipeline can fix. The message is shown on the step."""


# ----------------------------------------------------------------------------- data on a wire

@dataclass(frozen=True)
class Bundle:
    """Everything known about a recording at one point in the pipeline.

    Steps never modify a bundle; they return a new one with tables replaced or
    added. Untouched tables are shared, so a long pipeline stays cheap.
    """

    tables: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)
    notes: tuple = ()

    def update(self, note=None, meta=None, **tables):
        notes = self.notes + ((note,) if note else ())
        return Bundle({**self.tables, **tables}, {**self.meta, **(meta or {})}, notes)

    def without(self, *names):
        return Bundle({k: v for k, v in self.tables.items() if k not in names}, self.meta, self.notes)

    def __contains__(self, name):
        return name in self.tables

    def __getitem__(self, name):
        return self.tables[name]

    def get(self, name):
        return self.tables.get(name)

    @property
    def samples(self):
        return self.tables["samples"]


# ----------------------------------------------------------------------------- settings

@dataclass
class Param:
    """One setting of a step. Subclasses validate a value and describe their form control."""

    key: str
    label: str
    default: object = None
    help: str = ""
    unit: object = ""         # text, or {value of another setting: text} together with unit_from
    unit_from: str = ""
    when: dict | None = None  # show only while other settings have these values
    control: str = "text"

    def clean(self, value):
        return value

    def schema(self):
        out = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if callable(value) or value is None or value == "" or value == ():
                continue
            out[f.name] = value
        out["default"] = self.default
        return out


@dataclass
class Number(Param):
    min: float = 0
    max: float = 1e9
    step: float = 1
    integer: bool = False
    control: str = "number"

    def clean(self, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value):
            raise PipelineError(f"{self.label}: enter a number.")
        if not self.min <= value <= self.max:
            unit = f" {self.unit}" if self.unit and isinstance(self.unit, str) else ""
            raise PipelineError(f"{self.label} must be between {self.min:g} and {self.max:g}{unit}.")
        if self.integer:
            if int(value) != value:
                raise PipelineError(f"{self.label} must be a whole number.")
            return int(value)
        return float(value)


@dataclass
class Choice(Param):
    options: tuple = ()  # (value, label) pairs
    control: str = "select"

    def clean(self, value):
        if value not in [v for v, _ in self.options]:
            raise PipelineError(f"{self.label}: choose one of {', '.join(label for _, label in self.options)}.")
        return value


@dataclass
class Toggle(Param):
    default: object = False
    control: str = "toggle"

    def clean(self, value):
        if not isinstance(value, bool):
            raise PipelineError(f"{self.label} must be on or off.")
        return value


@dataclass
class Text(Param):
    default: object = ""
    multiline: bool = False
    placeholder: str = ""
    max_length: int = 20000
    control: str = "text"

    def clean(self, value):
        if not isinstance(value, str) or len(value) > self.max_length:
            raise PipelineError(f"{self.label}: enter text of at most {self.max_length} characters.")
        return value


@dataclass
class Columns(Param):
    """Pick column(s) of an input table. `pattern` pre-selects matching columns when left empty."""

    table: str = "samples"
    table_from: str = ""  # name of another setting that holds the table name
    multiple: bool = True
    pattern: str = ""
    control: str = "columns"

    def __post_init__(self):
        if self.default is None:
            self.default = [] if self.multiple else ""

    def clean(self, value):
        if self.multiple:
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value) or len(value) > 500:
                raise PipelineError(f"{self.label}: choose columns from the list.")
            return list(dict.fromkeys(value))
        if not isinstance(value, str):
            raise PipelineError(f"{self.label}: choose a column.")
        return value

    def resolve(self, value, frame):
        """Columns to use: the chosen ones, or those matching `pattern` when nothing was chosen."""
        chosen = value if self.multiple else ([value] if value else [])
        if not chosen and self.pattern:
            chosen = [c for c in frame.columns if fnmatch.fnmatchcase(str(c).casefold(), self.pattern.casefold())]
        missing = [c for c in chosen if c not in frame.columns]
        if missing:
            raise PipelineError(f"{self.label}: column “{missing[0]}” is not in the {self.table} table at this point.")
        return chosen if self.multiple else (chosen[0] if chosen else "")


@dataclass
class TableName(Param):
    default: object = ""
    control: str = "table"

    def clean(self, value):
        if not isinstance(value, str) or len(value) > 80:
            raise PipelineError(f"{self.label}: choose a table.")
        return value


@dataclass
class Custom(Param):
    """A setting with its own editor in the web app (for example the AOI drawing tool)."""

    validate: object = None

    def clean(self, value):
        return self.validate(value) if self.validate else value


# ----------------------------------------------------------------------------- steps

class Node:
    """One step of a pipeline. Subclass, fill in the class attributes, implement run()."""

    kind = ""
    title = ""
    group = "clean"
    icon = "box"
    summary = ""    # one line, shown in the step library
    explain = ""    # what the step does and why, shown beside its settings
    question = ""   # something to think about while changing the settings
    needs: tuple = ("samples",)   # tables that must already exist
    makes: tuple = ()             # tables this step creates (it may change others as well)
    params: tuple = ()
    view = ""                     # the view opened first when the step is selected
    package = ""                  # the package that does the step's mathematics, if it is not Gaze Lab itself

    def run(self, data: Bundle, p: dict, ctx) -> Bundle:
        raise NotImplementedError

    def headline(self, out: Bundle) -> str:
        """A few words for the step's card on the canvas."""
        for name in self.makes:
            if name in out and name != "samples":
                return f"{num(len(out[name]))} {name.replace('_', ' ') if name in ('fixations', 'saccades', 'blinks', 'trials') else 'rows'}"
        return ""

    def stamp(self, p: dict, ctx) -> str:
        """Anything outside the settings that changes the result (e.g. the files of a dataset)."""
        return ""

    def inputs(self, p: dict, ctx) -> Bundle | None:
        """What a source step reads, for the Input tab. Ordinary steps receive their parent's output."""
        return None

    def clean(self, raw):
        raw = raw or {}
        if not isinstance(raw, dict):
            raise PipelineError("Step settings must be an object.")
        return {p.key: p.clean(raw[p.key] if p.key in raw else copy.deepcopy(p.default)) for p in self.params}

    def param(self, key):
        return next(p for p in self.params if p.key == key)

    def code(self):
        """The source shown under “Python code” in the app."""
        return textwrap.dedent(inspect.getsource(type(self).run))

    def describe(self):
        return dict(
            kind=self.kind, title=self.title, group=self.group, icon=self.icon, summary=self.summary,
            explain=textwrap.dedent(self.explain).strip(), question=self.question, needs=list(self.needs),
            makes=list(self.makes), view=self.view, source=not self.needs,
            params=[p.schema() for p in self.params], package=self.package, code=self.code(),
        )


NODES: dict[str, Node] = {}
TABLES: dict[str, dict] = {}
VIEWS: dict[str, dict] = {}


def register(cls):
    """Class decorator: make a Node available to pipelines, the API and the web app."""
    if not cls.kind or not cls.title or not cls.summary or not cls.explain:
        raise ValueError(f"{cls.__name__} needs a kind, title, summary and explain text.")
    if cls.kind in NODES and type(NODES[cls.kind]).__module__ != cls.__module__:
        raise ValueError(f"A step called {cls.kind!r} is already registered.")
    if cls.group not in [g["id"] for g in GROUPS]:
        raise ValueError(f"{cls.kind}: unknown group {cls.group!r}.")
    NODES[cls.kind] = cls()
    return cls


def table(name, title, about, /, **columns):
    """Document a table so the app can explain its rows and columns."""
    TABLES[name] = dict(name=name, title=title, about=about, columns=columns)


def view(id, title, needs=("samples",), single_trial=True, compares=False):
    """Function decorator: register a figure builder `(data, sel, before) -> plotly figure dict`.

    `single_trial` views show one participant and trial; the others pool the selection.
    `compares` views can draw the step's input underneath (they use the `before` bundle).
    """
    def wrap(fn):
        VIEWS[id] = dict(id=id, title=title, needs=tuple(needs), single_trial=single_trial, compares=compares, build=fn)
        return fn
    return wrap


def makers(table_name):
    """Titles of the steps that can produce a table, for helpful error messages."""
    return [n.title for n in NODES.values() if table_name in n.makes]


# ----------------------------------------------------------------------------- small shared helpers

def runs(mask):
    """Half-open (start, end) index pairs of consecutive True values."""
    change = np.diff(np.r_[False, np.asarray(mask, bool), False].astype(np.int8))
    return list(zip(np.flatnonzero(change == 1), np.flatnonzero(change == -1)))


def trials(samples):
    """{(participant, trial): row positions}, in recording order."""
    return samples.groupby(KEYS, sort=False).indices


def sample_period(time):
    """Typical time between samples, in ms (0 when unknown).

    Measured across 20 samples at a time, so that timestamps rounded by the tracker
    (8.3, 16.7, 25.0 …) still give the true period (8.33).
    """
    time = np.asarray(time, float)
    span = min(20, len(time) - 1)
    if span < 1:
        return 0.0
    step = (time[span:] - time[:-span]) / span
    step = step[np.isfinite(step) & (step > 0)]
    return float(np.median(step)) if len(step) else 0.0


def trial_info(samples):
    """One row per participant and trial with its start time and any condition / stimulus label."""
    extra = [c for c in ("condition", "stimulus") if c in samples.columns]
    grouped = samples.groupby(KEYS, sort=False)
    info = grouped[extra].first() if extra else pd.DataFrame(index=grouped.size().index)
    info["trial_start"] = grouped["time"].min()
    return info.reset_index()


def with_trial_info(frame, samples):
    """Add condition / stimulus columns to an event or summary table, right after the keys."""
    info = trial_info(samples).drop(columns="trial_start")
    extra = [c for c in info.columns if c not in KEYS and c not in frame.columns]
    if not extra or frame.empty:
        for column in extra:
            frame[column] = pd.Series(dtype="str")
        return frame[[*KEYS, *extra, *[c for c in frame.columns if c not in KEYS and c not in extra]]]
    merged = frame.merge(info[[*KEYS, *extra]], on=KEYS, how="left")
    return merged[[*KEYS, *extra, *[c for c in frame.columns if c not in KEYS]]]


def num(value):
    """A count for reading: 24 480 rather than 24480."""
    return f"{int(value):,}".replace(",", "\u00a0")


def pct(part, whole):
    return f"{100 * part / whole:.1f}%" if whole else "0%"


table("samples", "Samples", "One row per measurement the eye tracker took.",
      participant="Who was recorded.", trial="Which part of the recording this row belongs to.",
      time="Milliseconds on the recording clock.", x="Horizontal gaze position in pixels (0 = left edge).",
      y="Vertical gaze position in pixels (0 = top edge).", pupil="Pupil size as reported by the tracker.",
      condition="Experimental condition of the trial.", stimulus="What was shown during the trial.",
      masked="True where a cleaning step removed the value.", filled="True where a value was estimated, not measured.",
      velocity="Gaze speed at this sample.", aoi="Area of interest the gaze was in (empty = none).")
table("events", "Markers", "Messages or triggers stored in the recording, such as task starts.",
      time="Milliseconds on the recording clock.", label="Text of the marker.", value="Extra value sent with the marker.")
