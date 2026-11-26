"""Loading a recording and giving its columns a meaning."""
from math import atan, degrees, radians, tan

import numpy as np
import pandas as pd

from ..core import KEYS, Bundle, Choice, Custom, Node, Number, PipelineError, register, sample_period, num
from ..readers import READERS, ROLES, read_file

ROLE_IDS = [r["id"] for r in ROLES]
NUMERIC = ("time", "x", "y", "pupil")
TIME_FACTOR = dict(ms=1.0, s=1000.0, us=0.001)


def clean_source(value):
    """Which dataset to read, how to read it and what its columns mean."""
    value = value or {}
    if not isinstance(value, dict):
        raise PipelineError("Choose a dataset to load.")
    mapping, extra, options = value.get("mapping") or {}, value.get("extra") or [], value.get("options") or {}
    reader = value.get("reader") or "auto"
    if reader != "auto" and reader not in READERS:
        raise PipelineError("Unknown file format.")
    if not isinstance(mapping, dict) or set(mapping) - set(ROLE_IDS) or not all(isinstance(v, str) for v in mapping.values()):
        raise PipelineError("The column mapping is not valid.")
    if not isinstance(extra, list) or not all(isinstance(c, str) for c in extra) or len(extra) > 300 or not isinstance(options, dict):
        raise PipelineError("The extra columns are not valid.")
    return dict(dataset=str(value.get("dataset") or ""), reader=reader, options=options, mapping=mapping, extra=extra)


def guess_time_unit(time):
    """Seconds, milliseconds or microseconds, judged from the spacing of samples (30–2000 Hz)."""
    step = sample_period(time)
    return "s" if step < 0.2 else "ms" if step < 500 else "us"


def labels(values):
    """Identifiers as text: 1.0 becomes “1”, missing stays missing."""
    values = pd.Series(values)
    if values.dtype.kind == "f" and (values.dropna() % 1 == 0).all():
        values = values.astype("Int64")
    return values.astype("str")


def standardise(raw, mapping, extra, label):
    """Pick the mapped columns of one file and name them time, x, y, pupil, …"""
    frame, out = raw.frame, {}
    for role in ROLES:
        column = mapping.get(role["id"]) or ""
        if column and column not in frame.columns:
            raise PipelineError(f"The column “{column}” chosen for {role['label']} is not in the file. Open the column mapping and choose again.")
        if not column and role.get("required"):
            raise PipelineError(f"Choose which column holds {role['label']}. Open “Columns” in the Load step.")
        if not column:
            continue
        values = frame[column]
        if role["id"] in NUMERIC:
            numbers = pd.to_numeric(values, errors="coerce")
            if numbers.notna().sum() < 0.5 * values.notna().sum():
                raise PipelineError(f"“{column}” ({role['label']}) is mostly text, not numbers. Check the decimal mark and the mapping.")
            values = numbers
        out[role["id"]] = values.to_numpy()
    table = pd.DataFrame(out)
    for column in ("participant", "trial", "condition", "stimulus"):
        if column in table:
            table[column] = labels(table[column])
    table["participant"] = table["participant"].fillna(label) if "participant" in table else label
    for column in extra:
        if column in frame.columns and column not in table.columns:
            table[column] = frame[column].to_numpy()
    return table


@register
class Load(Node):
    kind = "load"
    title = "Load recording"
    group = "input"
    icon = "database"
    summary = "Read files from an eye tracker and name their columns."
    explain = """
        Every analysis starts from **samples**: the eye tracker writes one row each time it measures the eye,
        typically 50 to 1000 times per second. This step reads the files, works out which columns hold time,
        gaze position and pupil size, and converts them to common units: milliseconds and pixels.

        Nothing is cleaned or interpreted yet. Compare **File as read** (what the tracker wrote)
        with **Output** (the same samples with standard names) to see exactly what was taken over.

        The viewing geometry matters later: detection thresholds are given in degrees of visual angle, and the
        number of pixels per degree depends on screen size and viewing distance (or, for glasses, on the scene
        camera's field of view).
    """
    question = "What does one row represent? How many rows per second does this tracker record, and what happens in the data when the eye is not found?"
    needs = ()
    makes = ("samples", "events")
    view = "signal"
    params = (
        Custom("source", "Recording", default=None, control="source", validate=clean_source),
        Choice("time_unit", "Time is in", "auto", options=(("auto", "Detect"), ("ms", "Milliseconds"), ("s", "Seconds"), ("us", "Microseconds"))),
        Choice("gaze_unit", "Gaze is in", "auto", options=(("auto", "Detect"), ("px", "Pixels"), ("normalised", "Fractions of the screen (0–1)")),
               help="Fractions are multiplied by the width and height below."),
        Number("width_px", "Width", 1920, unit="px", min=16, max=20000, integer=True, help="Of the screen, or of the scene video for glasses."),
        Number("height_px", "Height", 1080, unit="px", min=16, max=20000, integer=True),
        Choice("stimulus_fit", "Stimulus images", "stretch", options=(("stretch", "Fill the whole screen"), ("contain", "Fitted inside the screen, centred")),
               help="How the images were shown. WebGazer experiments fit each image inside the screen on a grey background."),
        Choice("geometry", "Viewing geometry", "screen", options=(("screen", "Screen at a known distance"), ("camera", "Scene camera (glasses)")),
               help="Used to convert pixels to degrees of visual angle."),
        Number("screen_width_cm", "Screen width", 53, unit="cm", min=1, max=1000, step=0.5, when=dict(geometry="screen")),
        Number("distance_cm", "Viewing distance", 60, unit="cm", min=1, max=2000, when=dict(geometry="screen")),
        Number("fov_deg", "Horizontal field of view", 82, unit="°", min=5, max=180, when=dict(geometry="camera"),
               help="82° for Tobii Pro Glasses 2, 95° for Glasses 3."),
    )

    def stamp(self, p, ctx):
        return ctx.dataset(p["source"]["dataset"]).stamp()

    def _read(self, p, ctx):
        source = p["source"]
        dataset = ctx.dataset(source["dataset"])
        if not dataset.files:
            raise PipelineError("This dataset has no recording files yet. Add at least one.")
        return dataset, [(f, *read_file(dataset.path(f["name"]), source["reader"], source["options"])) for f in dataset.files]

    def inputs(self, p, ctx):
        _, files = self._read(p, ctx)
        tables = {}
        for info, _, raw in files[:12]:
            tables[f"file: {info['label']}"] = raw.frame
            if raw.events is not None and len(raw.events):
                tables[f"markers: {info['label']}"] = raw.events
        return Bundle(tables)

    def run(self, data, p, ctx):
        source = p["source"]
        dataset, files = self._read(p, ctx)
        parts, markers, notes = [], [], []
        for info, reader, raw in files:
            mapping = source["mapping"] or reader.suggest(raw)["mapping"]
            parts.append(standardise(raw, mapping, source["extra"], info["label"]))
            if not notes:
                notes += raw.notes
            if raw.events is not None and len(raw.events):
                # markers must carry the same participant name as the samples they belong to
                people, column = parts[-1]["participant"].unique(), mapping.get("participant")
                if column and column in raw.events.columns and raw.events[column].notna().all():
                    who = labels(raw.events[column]).to_numpy()
                elif len(people) == 1:
                    who = people[0]
                else:
                    who = info["label"]
                    notes.append(f"“{info['name']}” holds several participants, and its markers do not say whose they are. Export one file per recording to use markers.")
                markers.append(raw.events[["time", "label", "value"]].assign(participant=who))
        samples = pd.concat(parts, ignore_index=True)
        samples = samples[samples["time"].notna()]
        if "trial" in samples:
            outside = int(samples["trial"].isna().sum())
            if outside:
                notes.append(f"{num(outside)} samples that belong to no trial were left out.")
                samples = samples[samples["trial"].notna()]
        else:
            samples = samples.assign(trial="1")
        if len(samples) < 3:
            raise PipelineError("Fewer than three usable samples were found. Check the column mapping.")
        if len(samples) > ctx.max_rows:
            raise PipelineError(f"This dataset has {num(len(samples))} samples; this server accepts up to {num(ctx.max_rows)}. Split it or raise GAZELAB_MAX_ROWS.")

        # Units: everything downstream assumes milliseconds and pixels.
        unit = guess_time_unit(samples["time"].to_numpy()[:5000]) if p["time_unit"] == "auto" else p["time_unit"]
        samples["time"] = samples["time"] * TIME_FACTOR[unit]
        gaze_unit = p["gaze_unit"]
        if gaze_unit == "auto":
            spread = np.nanpercentile(np.abs(samples[["x", "y"]].to_numpy(float)), 99) if samples["x"].notna().any() else 0
            gaze_unit = "normalised" if 0 < spread <= 1.5 else "px"
        if gaze_unit == "normalised":
            samples["x"], samples["y"] = samples["x"] * p["width_px"], samples["y"] * p["height_px"]
        if "pupil" not in samples:
            samples["pupil"] = np.nan
        zero = int((samples["pupil"] <= 0).sum())
        samples["pupil"] = samples["pupil"].where(samples["pupil"] > 0)
        if zero:
            notes.append(f"{num(zero)} pupil values of zero or less mean “eye not found” and were set to missing.")

        # Time must run forward within each participant and trial.
        step = samples.groupby(KEYS, sort=False)["time"].diff()
        if (step < 0).any():
            raise PipelineError("Time jumps backwards within a recording. If the file holds several trials or participants, map their columns in the Load step.")
        if (step == 0).any():
            notes.append(f"{int((step == 0).sum())} samples repeated a timestamp and were dropped.")
            samples = samples[step != 0]
        ordered = [*KEYS, *[c for c in ("condition", "stimulus") if c in samples], "time", "x", "y", "pupil"]
        samples = samples[[*ordered, *[c for c in samples.columns if c not in ordered]]].reset_index(drop=True)
        samples["masked"], samples["filled"] = False, False

        # Viewing geometry, in the terms pymovements uses: a screen of a known size at a known distance.
        # A scene camera is the same thing: its picture is a window one metre away that spans the field of view.
        period = sample_period(samples["time"].to_numpy()[:20000])
        distance = p["distance_cm"] if p["geometry"] == "screen" else 100.0
        width_cm = p["screen_width_cm"] if p["geometry"] == "screen" else 2 * distance * tan(radians(min(p["fov_deg"], 170) / 2))
        per_degree = p["width_px"] / (2 * degrees(atan(width_cm / 2 / distance)))
        rate = float(f"{1000 / period:.4g}") if period else None
        experiment = dict(screen_width_px=p["width_px"], screen_height_px=p["height_px"], screen_width_cm=round(width_cm, 2),
                          screen_height_cm=round(width_cm * p["height_px"] / p["width_px"], 2), distance_cm=float(distance),
                          origin="upper left", sampling_rate=rate)
        meta = dict(dataset=dataset.id, width_px=p["width_px"], height_px=p["height_px"], px_per_deg=per_degree, sampling_hz=rate,
                    experiment=experiment if rate else None, stimuli=dict(dataset.stimuli), stimulus_fit=p["stimulus_fit"], pupil_unit="as recorded")
        groups = samples.groupby(KEYS, sort=False).ngroups
        notes.insert(0, f"{num(len(samples))} samples · {samples['participant'].nunique()} participant(s) · {groups} trial(s) · "
                        f"about {meta['sampling_hz']:.0f} samples per second · time read as {dict(ms='milliseconds', s='seconds', us='microseconds')[unit]}, "
                        f"gaze as {'screen fractions' if gaze_unit == 'normalised' else 'pixels'} · {per_degree:.1f} px per degree.")
        if len(files) > 1:
            notes.append(f"{len(files)} files were read the same way; the remarks above describe the first.")
        tables = dict(samples=samples)
        if markers:
            events = pd.concat(markers, ignore_index=True)
            events["time"] = pd.to_numeric(events["time"], errors="coerce") * TIME_FACTOR[unit]
            tables["events"] = events[["participant", "time", "label", "value"]].sort_values(["participant", "time"], kind="stable").reset_index(drop=True)
        result = Bundle(tables, meta)
        for note in notes:
            result = result.update(note)
        return result

    def headline(self, out):
        s = out.samples
        return f"{num(len(s))} samples"
