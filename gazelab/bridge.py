"""The bridge to pymovements, the package that does the eye-movement mathematics.

Gaze Lab keeps data as pandas tables so that every step can show them. A step
that cleans the signal or detects events does not compute anything itself: it
hands the samples to pymovements as a `Gaze` object, calls pymovements, and
copies the result back into tables.

Such a step is a GazeStep. It only lists the pymovements calls it makes. Because
that list is data, the same list is run by the app and printed as a script that
works outside the app, with the current settings filled in.
"""
from __future__ import annotations

import inspect
import textwrap
import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import polars as pl
import pymovements as pm

from .core import KEYS, Bundle, Node, PipelineError, with_trial_info

# Finding nothing is an ordinary result here (the step reports it), not something to warn about.
warnings.filterwarnings("ignore", message=".*No events were detected", category=UserWarning)
warnings.filterwarnings("ignore", message="All-NaN slice", category=RuntimeWarning, module="pymovements")

GAZE_COLUMNS = [*KEYS, "time", "x", "y", "pupil"]

# How a pymovements event property is called in Gaze Lab's tables.
PROPERTY_COLUMNS = dict(amplitude="amplitude_deg", peak_velocity="peak_velocity", dispersion="dispersion_deg")


def experiment_settings(meta):
    """The arguments of pm.Experiment: screen, viewing distance and sampling rate, as the Load step recorded them."""
    if not meta.get("experiment"):
        raise PipelineError("The viewing geometry and sampling rate are unknown at this point. They are set by the Load step.")
    return dict(meta["experiment"])


def to_gaze(data, time=None, stretch=None):
    """The samples of a bundle as a pymovements Gaze, one row per sample and in the same order.

    pymovements keeps time in whole milliseconds, so time is rounded. `time` replaces that clock
    and `stretch` splits trials further; only I-DT needs them (see nodes/detect.py).
    """
    s = data.samples
    frame = pd.DataFrame({key: s[key].to_numpy() for key in KEYS})
    if stretch is not None:
        frame["stretch"] = stretch
    frame["time"] = np.rint(s["time"].to_numpy(float)).astype("int64") if time is None else time
    for column in ("x", "y", "pupil"):
        frame[column] = s[column].to_numpy(float)
    return pm.gaze.from_pandas(
        frame, experiment=pm.Experiment(**experiment_settings(data.meta)),
        trial_columns=[c for c in frame.columns if c not in ("time", "x", "y", "pupil")],
        time_column="time", time_unit="ms", pixel_columns=["x", "y"],
    )


def count(gaze, name):
    """How many events of one kind pymovements has found so far."""
    return 0 if gaze.events is None else gaze.events.frame.filter(pl.col("name") == name).height


def cleaned_samples(gaze, samples):
    """The samples table after pymovements changed gaze or pupil. Values it removed are flagged as `masked`."""
    g = gaze.samples
    x, y = g["pixel"].list.get(0).to_numpy(), g["pixel"].list.get(1).to_numpy()
    pupil = g["pupil"].to_numpy().astype(float)
    lost = (samples["x"].notna().to_numpy() & np.isnan(x)) | (samples["pupil"].notna().to_numpy() & np.isnan(pupil))
    return samples.assign(x=x, y=y, pupil=pupil, masked=samples["masked"].to_numpy() | lost)


# ----------------------------------------------------------------------------- two calls, done in one pass
#
# pymovements handles the samples of each event separately: it filters the whole recording once
# per event. That is fine for a trial and takes minutes for a class's recordings (the time grows
# with samples × events). The two functions below give the same result as the pymovements methods
# they are named after, in one pass over the data. tests/test_steps.py checks them against pymovements.

def nullify_event_samples(gaze, name, padding=(25, 25)):
    """What gaze.nullify_event_samples(name, padding=padding) does: empty the samples inside events of one kind.

    A sample lies inside an event when more (padded) events of its trial have started by then than have ended before it.
    """
    before, after = padding if isinstance(padding, tuple) else (padding, padding)
    keys = gaze.trial_columns
    events = gaze.events.frame.filter(pl.col("name") == name).partition_by(keys, as_dict=True)
    inside = np.zeros(gaze.samples.height, bool)
    for trial, part in gaze.samples.select(*keys, "time").with_row_index("row").partition_by(keys, as_dict=True).items():
        if trial in events:
            time = part["time"].to_numpy()
            started = np.searchsorted(np.sort(events[trial]["onset"].to_numpy() - before), time, side="right")
            ended = np.searchsorted(np.sort(events[trial]["offset"].to_numpy() + after), time, side="left")
            inside[part["row"].to_numpy()] = started > ended
    mask = pl.Series(inside)
    gaze.samples = gaze.samples.with_columns(pl.when(mask).then(None).otherwise(pl.col(c)).alias(c) for c in gaze.samples.columns if c not in ("time", *keys))


def compute_event_properties(gaze, measures, name):
    """What gaze.compute_event_properties(measures, name=name) does: describe every event of one kind.

    Every sample is first labelled with the event it lies in; pymovements' own measure expressions
    (amplitude, peak velocity, dispersion, location) are then evaluated per event.
    """
    keys = gaze.trial_columns
    events = gaze.events.frame.filter(pl.col("name") == name).with_row_index("event")
    inside = (gaze.samples.join_asof(events.select(*keys, "event", "onset", "offset"), left_on="time", right_on="onset", by=keys, strategy="backward", check_sortedness=False)
              .filter(pl.col("time") <= pl.col("offset")))
    values = inside.group_by("event", maintain_order=True).agg(*pm.EventSamplesProcessor(measures).measures)
    results = events.select(*keys, "name", "onset", "offset", "event").join(values, on="event", how="left").drop("event")
    gaze.events.add_event_properties(results, join_on=[*keys, "name", "onset", "offset"])


ONE_PASS = dict(nullify_event_samples=nullify_event_samples, compute_event_properties=compute_event_properties)


def speed(gaze):
    """Gaze speed per sample in °/s: the length of pymovements' (horizontal, vertical) velocity."""
    v = gaze.samples["velocity"]
    return np.hypot(v.list.get(0).to_numpy().astype(float), v.list.get(1).to_numpy().astype(float))


def events_table(gaze, name, samples, number):
    """The events of one kind as a table, one row per event.

    pymovements reports onsets and offsets on the clock of the Gaze object. Here they become
    milliseconds from the start of the trial, as in every other Gaze Lab table. The offset is
    the time of the event's last sample, so `duration` is offset minus onset.
    """
    keys = gaze.trial_columns
    events = gaze.events.frame.filter(pl.col("name") == name)
    e = pd.DataFrame(events.to_dict(as_series=False))
    out = e[KEYS].copy() if len(e) else pd.DataFrame({key: pd.Series(dtype="str") for key in KEYS})
    out[number] = out.groupby(KEYS, sort=False).cumcount() + 1
    clock = pd.DataFrame({key: gaze.samples[key].to_numpy() for key in keys})
    clock["tick"] = gaze.samples["time"].to_numpy()
    clock["ms"] = samples["time"].to_numpy(float)
    clock["ms"] -= clock.groupby(KEYS, sort=False)["ms"].transform("min")
    clock = clock.drop_duplicates([*keys, "tick"])
    for edge, column in (("onset", "start"), ("offset", "end")):
        found = e[[*keys, edge]].merge(clock, left_on=[*keys, edge], right_on=[*keys, "tick"], how="left") if len(e) else clock.head(0)
        out[column] = found["ms"].to_numpy(float)
    out["duration"] = out["end"] - out["start"]
    if "location" in e:
        out["x"], out["y"] = e["location"].str[0].to_numpy(float), e["location"].str[1].to_numpy(float)
    for source, column in PROPERTY_COLUMNS.items():
        if source in e:
            out[column] = e[source].to_numpy(float)
    return with_trial_info(out, samples)


# ----------------------------------------------------------------------------- steps made of pymovements calls

@dataclass(frozen=True)
class Call:
    """One call of a method of a pymovements Gaze object."""

    method: str
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)

    def __call__(self, gaze):
        one_pass = ONE_PASS.get(self.method)  # the same result as the pymovements method, much faster on long recordings
        return one_pass(gaze, *self.args, **self.kwargs) if one_pass else getattr(gaze, self.method)(*self.args, **self.kwargs)

    def __str__(self):
        arguments = [written(a) for a in self.args] + [f"{key}={written(value)}" for key, value in self.kwargs.items()]
        return f"gaze.{self.method}({', '.join(arguments)})"

    def line(self):
        """The call as a line of a script. A call that works on found events is skipped when none were found, as in the app."""
        return f'if "{self.needs}" in gaze.events.frame["name"]:\n    {self}' if self.needs else str(self)

    @property
    def needs(self):
        """The kind of event that must have been found for this call to make sense."""
        if self.method == "nullify_event_samples":
            return self.args[0]
        return self.kwargs.get("name") if self.method == "compute_event_properties" else None


def call(method, *args, **kwargs):
    return Call(method, args, kwargs)


def written(value):
    """A value as it would be typed in a script."""
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, dict):
        return "{" + ", ".join(f"{written(k)}: {written(v)}" for k, v in value.items()) + "}"
    if isinstance(value, (list, tuple)):
        inner = ", ".join(map(written, value))
        return f"[{inner}]" if isinstance(value, list) else f"({inner})"
    return repr(value)


SCRIPT = '''\
import pandas as pd
import pymovements as pm

# The Samples table that goes into this step: open the step's Input tab and download it as CSV.
samples = pd.read_csv("samples.csv")
{clock}

experiment = pm.Experiment(
    {experiment},
)
gaze = pm.gaze.from_pandas(
    samples[["participant", "trial", "time", "x", "y", "pupil"]], experiment=experiment,
    trial_columns=["participant", "trial"], time_column="time", time_unit="ms", pixel_columns=["x", "y"],
)

{calls}

print(gaze.{shows})
'''


class GazeStep(Node):
    """A step whose work is a list of pymovements calls.

    A subclass says which calls to make (`calls`) and what to keep of the result (`keep`).
    """

    package = "pymovements"
    shows = "events.frame"   # what the script prints at the end: "events.frame" or "samples"

    def calls(self, p: dict, data: Bundle) -> list[Call]:
        raise NotImplementedError

    def keep(self, data: Bundle, gaze: pm.Gaze, p: dict) -> Bundle:
        raise NotImplementedError

    def gaze(self, data, p):
        return to_gaze(data)

    def clock(self, p, data):
        """The line of the script that prepares the time column."""
        return 'samples["time"] = samples["time"].round().astype("int64")   # pymovements keeps time in whole milliseconds'

    def run(self, data, p, ctx):
        steps = self.calls(p, data)
        gaze = self.gaze(data, p)
        for step in steps:
            if step.needs and not count(gaze, step.needs):
                continue  # nothing of this kind was found, so there is nothing to work on
            try:
                step(gaze)
            except Exception as exc:  # pymovements refused the data or the settings; say which call and why
                raise PipelineError(f"pymovements stopped at {step}: {str(exc)[:300]}") from exc
        return self.keep(data, gaze, p)

    def script(self, p, data):
        """This step as a script that runs without Gaze Lab, with the current settings filled in."""
        experiment = ",\n    ".join(f"{key}={written(value)}" for key, value in experiment_settings(data.meta).items())
        return SCRIPT.format(clock=self.clock(p, data), experiment=experiment, shows=self.shows,
                             calls="\n".join(step.line() for step in self.calls(p, data)))

    def code(self):
        return "\n".join(textwrap.dedent(inspect.getsource(getattr(type(self), name))) for name in ("calls", "keep"))
