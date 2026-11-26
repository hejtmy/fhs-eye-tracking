"""Tobii Pro Lab “Data Export” files (TSV). Covers Tobii Pro Glasses 2 and 3 and screen-based trackers.

Glasses exports interleave eye-tracker rows with gyroscope and accelerometer
rows and with marker rows; this reader separates them. Column names changed
between Pro Lab versions (newer ones carry units, e.g. “Gaze point X [MCS px]”),
so columns are matched by the start of their name.
"""
import pandas as pd

from ..core import Choice, num
from . import Raw, Reader, reader, simple, suggest_mapping
from ._tables import read_table
from .delimited import DECIMAL

SCENE_CAMERA_FOV = 82  # horizontal field of view of the Glasses 2 scene camera, degrees


def find(columns, *names):
    """First column whose name is, or starts with, one of the given names."""
    keys = {simple(c): c for c in reversed(list(columns))}
    for name in map(simple, names):
        if name in keys:
            return keys[name]
    for name in map(simple, names):
        for key, column in keys.items():
            if key.startswith(name):
                return column
    return None


@reader
class TobiiProLab(Reader):
    id = "tobii_prolab"
    title = "Tobii Pro Lab data export (Glasses 2 / 3, screen trackers)"
    about = ("In Tobii Pro Lab choose Data Export, tab-separated, one file per recording or all in one. "
             "Include Recording timestamp, Gaze point X/Y, Pupil diameter, Participant name, Event and, for glasses, Sensor.")
    extensions = (".tsv", ".txt")
    options = (DECIMAL, Choice("pupil", "Pupil size from", "mean", options=(("mean", "Mean of both eyes"), ("left", "Left eye"), ("right", "Right eye"))))

    def sniff(self, path, head):
        first = simple(head.splitlines()[0]) if head else ""
        return 0.9 if "recordingtimestamp" in first and ("gazepointx" in first or "sensor" in first) else 0.0

    def read(self, path, o):
        frame, used = read_table(path, "tab", o["decimal"])
        notes = [f"Tobii Pro Lab export, decimal mark “{used['decimal']}”."]
        time, sensor, event = (find(frame.columns, n) for n in ("recording timestamp", "sensor", "event"))
        gaze_x = find(frame.columns, "gaze point x")
        if not time or not gaze_x:
            raise ValueError("the export needs the columns “Recording timestamp” and “Gaze point X / Y”.")

        events = None
        if event:
            value = find(frame.columns, "event value")
            marked = frame[frame[event].notna()]
            events = pd.DataFrame(dict(time=marked[time].to_numpy(), label=marked[event].astype(str).to_numpy(),
                                       value=marked[value].to_numpy() if value else None))
            for owner in ("participant name", "recording name"):  # lets the Load step tell whose marker it is
                if column := find(frame.columns, owner):
                    events[column] = marked[column].to_numpy()
            frame = frame[frame[event].isna() | frame[gaze_x].notna()]
        hints = dict(time_unit="us" if any(u in time.casefold() for u in ("[μs]", "[µs]", "[us]")) else "ms", gaze_unit="px")
        if sensor:
            is_eye = frame[sensor].isna() | frame[sensor].astype(str).str.casefold().eq("eye tracker")
            notes.append(f"Kept {num(int(is_eye.sum()))} eye-tracker rows; set aside {num(int((~is_eye).sum()))} gyroscope/accelerometer rows.")
            frame = frame[is_eye]
            hints.update(geometry="camera", fov_deg=SCENE_CAMERA_FOV)
        frame = frame.dropna(axis=1, how="all").reset_index(drop=True)

        left, right = find(frame.columns, "pupil diameter left"), find(frame.columns, "pupil diameter right")
        chosen = [c for c, eye in ((left, "left"), (right, "right")) if c and o["pupil"] in ("mean", eye)]
        if chosen:
            frame["Pupil diameter mean"] = frame[chosen].mean(axis=1)
            notes.append("Pupil size: " + ("mean of the eyes that were tracked." if len(chosen) > 1 else f"{o['pupil']} eye."))
        for key, name in (("width_px", "recording resolution width"), ("height_px", "recording resolution height")):
            column = find(frame.columns, name)
            if column is not None and frame[column].notna().any():
                hints[key] = int(float(frame[column].dropna().iloc[0]))
        return Raw(frame, events, notes, hints)

    def suggest(self, raw):
        columns = list(raw.frame.columns)
        mapping = suggest_mapping(columns)
        keep = [c for c in columns if simple(c).startswith(("aoihit", "eyemovementtype", "mappedgazedata", "mappedgazepoint", "mappedfixation", "gazeeventduration"))]
        return dict(mapping=mapping, extra=keep, params=dict(raw.hints))
