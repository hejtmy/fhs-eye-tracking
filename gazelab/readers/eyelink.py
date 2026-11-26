"""EyeLink ASC files (EDF converted with SR Research's edf2asc, samples and events).

The file is parsed by pymovements (pymovements.gaze.from_asc). What is added here
is specific to Gaze Lab: one table column per measurement, and trials from the
TRIALID … TRIAL_RESULT messages that EyeLink experiments conventionally send.
"""
import warnings

import numpy as np
import pandas as pd
import pymovements as pm

from ..core import Choice
from . import Raw, Reader, open_text, reader


@reader
class EyeLinkAsc(Reader):
    id = "eyelink_asc"
    title = "EyeLink ASC (converted from EDF)"
    about = "Convert the EDF with EDF2ASC (samples and events), then upload the .asc file. TRIALID messages become trials."
    extensions = (".asc",)
    options = (Choice("eye", "Eye", "auto", options=(("auto", "The recorded eye (left if both)"), ("left", "Left"), ("right", "Right"))),)

    def sniff(self, path, head):
        if "** CONVERTED FROM" in head or "\nSAMPLES\t" in head or "\nSAMPLES " in head:
            return 0.95
        return 0.8 if path.suffix.lower() == ".asc" else 0.0

    def read(self, path, o):
        with open_text(path) as handle, warnings.catch_warnings():
            warnings.simplefilter("ignore")  # pymovements warns about every header line a file lacks
            gaze = pm.gaze.from_asc(handle, messages=True)
        samples = gaze.samples
        if not len(samples):
            raise ValueError("no sample lines found. Convert the EDF with samples included.")
        binocular = len(samples["pixel"][0]) == 4
        names = ["x_left", "y_left", "x_right", "y_right"] if binocular else ["x", "y"]
        frame = pd.DataFrame({"time": samples["time"].to_numpy()})
        for i, name in enumerate(names):
            frame[name] = samples["pixel"].list.get(i).to_numpy()
        if binocular:
            frame["pupil_left"], frame["pupil_right"] = (samples["pupil"].list.get(i).to_numpy() for i in (0, 1))
            eye = "right" if o["eye"] == "right" else "left"
            for channel in ("x", "y", "pupil"):
                frame[channel] = frame[f"{channel}_{eye}"]
        else:
            frame["pupil"] = samples["pupil"].to_numpy()
        notes = [f"EyeLink recording, {'both eyes' if binocular else 'one eye'}, read with pymovements. Time is in ms; pupil size is in the tracker's arbitrary units."]
        if binocular:
            notes.append(f"Using the {eye} eye. Both eyes stay available as extra columns.")
        log = gaze.messages
        messages = list(zip(log["time"].to_list(), log["content"].to_list())) if log is not None else []
        screen = next((tuple(int(float(n)) + 1 for n in text.split()[-2:]) for _, text in messages if text.startswith(("DISPLAY_COORDS", "GAZE_COORDS"))), None)

        events = pd.DataFrame(messages, columns=["time", "label"])
        events["value"] = None
        starts = [(t, text.split()[1] if len(text.split()) > 1 else "trial") for t, text in messages if text.startswith("TRIALID")]
        if starts:
            ends = np.array([t for t, text in messages if text.startswith("TRIAL_RESULT")])
            time, trial, seen = frame["time"].to_numpy(float), np.full(len(frame), None, object), {}
            for i, (start, label) in enumerate(starts):
                stop = starts[i + 1][0] if i + 1 < len(starts) else np.inf
                later = ends[(ends > start) & (ends <= stop)]
                stop = later[0] if len(later) else stop
                seen[label] = seen.get(label, 0) + 1
                trial[(time >= start) & (time < stop)] = label if seen[label] == 1 else f"{label}#{seen[label]}"
            frame["trial"] = trial
            notes.append(f"{len(starts)} trials from TRIALID … TRIAL_RESULT messages; samples between trials are left out.")
        hints = dict(time_unit="ms", gaze_unit="px", geometry="screen")
        if screen:
            hints.update(width_px=screen[0], height_px=screen[1])
        return Raw(frame, events, notes, hints)
