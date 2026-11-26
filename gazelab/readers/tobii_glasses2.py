"""Tobii Pro Glasses 2 raw recordings: `livedata.json.gz` from the SD card.

Found at projects/<id>/recordings/<id>/segments/1/livedata.json.gz. Each line
is one JSON packet: `ts` is microseconds, `s` is 0 when the value is valid, and
one further key says what it is — `gp` gaze point in the scene video (0–1),
`gp3` gaze point in 3D (mm), `pd` pupil diameter (mm) per `eye`, `gy`/`ac`
motion sensors. Packets of one gaze sample share a `gidx`.
"""
import json

import numpy as np
import pandas as pd

from ..core import num
from . import Raw, Reader, open_text, reader
from .tobii_prolab import SCENE_CAMERA_FOV

VIDEO = (1920, 1080)


@reader
class TobiiGlasses2(Reader):
    id = "tobii_glasses2"
    title = "Tobii Pro Glasses 2 raw recording (livedata.json)"
    about = "Upload livedata.json.gz straight from the recording folder on the SD card. No Tobii software needed."
    extensions = (".json", ".gz")

    def sniff(self, path, head):
        first = head.lstrip()[:400]
        return 0.95 if first.startswith("{") and '"ts"' in first and '"s"' in first else 0.0

    def read(self, path, o):
        samples, markers, skipped, sensors, first_ts = {}, [], 0, 0, None
        with open_text(path) as handle:
            for line in handle:
                try:
                    packet = json.loads(line)
                    ts = packet["ts"]
                except (ValueError, KeyError, TypeError):
                    skipped += 1
                    continue
                first_ts = ts if first_ts is None else first_ts
                valid = packet.get("s", 0) == 0
                if "gidx" in packet:
                    row = samples.setdefault(packet["gidx"], {"ts": ts})
                    if not valid:
                        continue
                    if "gp" in packet:
                        row["ts"], (row["gaze_x"], row["gaze_y"]) = ts, packet["gp"]
                    elif "pd" in packet:
                        row["pupil_" + packet.get("eye", "left")] = packet["pd"]
                    elif "gp3" in packet:
                        row["gaze3d_x"], row["gaze3d_y"], row["gaze3d_z"] = packet["gp3"]
                elif "gy" in packet or "ac" in packet:
                    sensors += 1
                elif "tag" in packet or "type" in packet:
                    markers.append((ts, str(packet.get("tag") or packet.get("type")), packet.get("ets")))
                elif "dir" in packet and "sig" in packet:
                    markers.append((ts, f"sync_{packet['dir']}_{'high' if packet['sig'] else 'low'}", None))
        if not samples:
            raise ValueError("no gaze packets found. Is this the livedata.json(.gz) file of a Glasses 2 recording?")
        frame = pd.DataFrame.from_dict(samples, orient="index").sort_values("ts")
        for column in ("gaze_x", "gaze_y", "pupil_left", "pupil_right"):
            if column not in frame:
                frame[column] = np.nan
        frame.insert(0, "time_ms", (frame.pop("ts") - first_ts) / 1000)
        frame["gaze_x"] *= VIDEO[0]
        frame["gaze_y"] *= VIDEO[1]
        frame["pupil_mean"] = frame[["pupil_left", "pupil_right"]].mean(axis=1)
        frame.insert(1, "gidx", frame.index)
        events = pd.DataFrame(markers, columns=["time", "label", "value"])
        events["time"] = (events["time"] - first_ts) / 1000
        notes = [f"Glasses 2 recording: {num(len(frame))} gaze samples, {num(sensors)} motion-sensor packets set aside, {len(events)} markers.",
                 "Gaze is in scene-video pixels (1920 × 1080). The scene moves with the head, so positions are relative to the camera, not to the world."]
        if skipped:
            notes.append(f"{skipped} unreadable lines were skipped.")
        hints = dict(time_unit="ms", gaze_unit="px", width_px=VIDEO[0], height_px=VIDEO[1], geometry="camera", fov_deg=SCENE_CAMERA_FOV)
        return Raw(frame.reset_index(drop=True), events, notes, hints)

    def suggest(self, raw):
        return dict(mapping=dict(time="time_ms", x="gaze_x", y="gaze_y", pupil="pupil_mean", participant="", trial="", condition="", stimulus=""),
                    extra=[], params=dict(raw.hints))
