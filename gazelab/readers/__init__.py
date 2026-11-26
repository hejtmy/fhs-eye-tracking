"""File readers, one module per eye-tracker format.

A reader turns a file into a table "as recorded" plus, when the format has
them, a table of markers. It also suggests which columns hold time, gaze and
pupil, so that most files load without any manual mapping.

To support a new format, add a module here with a Reader subclass decorated
with @reader. Nothing else needs to change.
"""
from __future__ import annotations

import gzip
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules

import pandas as pd

from ..core import PipelineError

# What a column can mean. `time`, `x` and `y` are required.
ROLES = [
    dict(id="time", label="Time", required=True, help="When each sample was taken."),
    dict(id="x", label="Gaze X", required=True, help="Horizontal gaze position."),
    dict(id="y", label="Gaze Y", required=True, help="Vertical gaze position."),
    dict(id="pupil", label="Pupil size", help="Leave empty if the file has none."),
    dict(id="participant", label="Participant", help="Leave empty to use one participant per file."),
    dict(id="trial", label="Trial", help="Leave empty for one continuous recording; trials can be cut from markers later."),
    dict(id="condition", label="Condition", help="Experimental condition of each trial."),
    dict(id="stimulus", label="Stimulus", help="Name of the image shown, matched to uploaded images."),
]

# Column names seen in exports of common trackers, most specific first.
ALIASES = {
    "time": ["recording timestamp", "time_ms", "timestamp", "time", "gaze_timestamp", "device_time_stamp",
             "system_time_stamp", "tracker_time", "recordingtime", "t"],
    "x": ["gaze point x", "gaze_x", "x", "gazepointx", "x_pix", "bpogx", "fpogx", "por x", "l por x", "gaze x", "x_left"],
    "y": ["gaze point y", "gaze_y", "y", "gazepointy", "y_pix", "bpogy", "fpogy", "por y", "l por y", "gaze y", "y_left"],
    "pupil": ["pupil diameter mean", "pupil", "pupil_mm", "pupil_size", "pupil diameter filtered", "pupil diameter left",
              "pupil_left", "diameter", "pupil diameter", "lpd", "l pupil diameter", "pupil_diameter"],
    "participant": ["participant name", "participant", "participant_id", "subject", "subject_id", "subject_nr", "recording name", "user"],
    "trial": ["trial", "trial_id", "trial_index", "trial_nr", "trialid"],
    "condition": ["condition", "cond"],
    "stimulus": ["presented stimulus name", "stimulus", "stimulus_name", "presented media name", "media", "image"],
}


def simple(name):
    """Compare column names loosely: ignore case, units in brackets and punctuation."""
    return re.sub(r"[^a-z0-9]+", "", re.sub(r"[\[(].*?[\])]", "", str(name).casefold()))


def suggest_mapping(columns, aliases=ALIASES):
    lookup = {}
    for column in columns:
        lookup.setdefault(simple(column), column)
    return {role: next((lookup[simple(a)] for a in names if simple(a) in lookup), "") for role, names in aliases.items()}


@dataclass
class Raw:
    """A file as read: its table, any markers, and remarks from the reader."""

    frame: pd.DataFrame
    events: pd.DataFrame | None = None   # columns: time (same unit as the samples), label, value; may repeat the file's participant column
    notes: list = field(default_factory=list)
    hints: dict = field(default_factory=dict)  # suggested Load settings, e.g. width_px, time_unit


class Reader:
    id = ""
    title = ""
    about = ""
    extensions: tuple = ()
    options: tuple = ()   # Param objects, shown under “Reading options”

    def sniff(self, path: Path, head: str) -> float:
        """How sure this reader is that the file is its format, 0–1."""
        return 0.0

    def read(self, path: Path, o: dict) -> Raw:
        raise NotImplementedError

    def suggest(self, raw: Raw) -> dict:
        """Proposed column mapping, extra columns worth keeping and Load settings."""
        return dict(mapping=suggest_mapping(raw.frame.columns), extra=[], params=dict(raw.hints))

    def clean(self, options):
        options = options or {}
        return {p.key: p.clean(options[p.key] if p.key in options else p.default) for p in self.options}

    def describe(self):
        return dict(id=self.id, title=self.title, about=self.about, extensions=list(self.extensions),
                    options=[p.schema() for p in self.options])


READERS: dict[str, Reader] = {}


def reader(cls):
    READERS[cls.id] = cls()
    return cls


def open_text(path: Path):
    """Open plain or gzipped text, coping with the encodings eye-tracker software writes."""
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rb") as handle:
        start = handle.read(4)
    encoding = "utf-16" if start[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"
    return opener(path, "rt", encoding=encoding, errors="replace", newline="")


def head(path: Path, size=16384):
    try:
        with open_text(path) as handle:
            return handle.read(size)
    except (OSError, EOFError, UnicodeError):
        return ""


def detect(path: Path) -> Reader:
    start = head(path)
    if not start.strip():
        raise PipelineError(f"“{path.name}” is empty or not a text file. Export samples as text (CSV/TSV), EyeLink ASC or Tobii livedata.json.")
    best = max(READERS.values(), key=lambda r: r.sniff(path, start))
    return best


@lru_cache(maxsize=12)
def _read(path_text, modified, reader_id, options_json):
    path = Path(path_text)
    chosen = detect(path) if reader_id == "auto" else READERS[reader_id]
    try:
        raw = chosen.read(path, chosen.clean(json.loads(options_json)))
    except PipelineError:
        raise
    except Exception as exc:  # a reader met something unexpected in the file
        raise PipelineError(f"Could not read “{path.name}” as {chosen.title}: {str(exc)[:300]}") from exc
    if raw.frame.empty:
        raise PipelineError(f"“{path.name}” contains no samples when read as {chosen.title}.")
    raw.frame.columns = [str(c) for c in raw.frame.columns]
    return chosen, raw


def read_file(path: Path, reader_id="auto", options=None) -> tuple[Reader, Raw]:
    """Read a recording file. Results are cached; treat the returned tables as read-only."""
    if reader_id != "auto" and reader_id not in READERS:
        raise PipelineError(f"Unknown file format {reader_id!r}.")
    return _read(str(path), path.stat().st_mtime_ns, reader_id, json.dumps(options or {}, sort_keys=True))


for module in sorted(iter_modules(__path__), key=lambda m: m.name):
    if not module.name.startswith("_"):
        import_module(f"{__name__}.{module.name}")
