"""Giving a recording structure: trials, conditions, time windows."""
import re
from io import StringIO

import numpy as np
import pandas as pd

from ..core import KEYS, Choice, Node, Number, PipelineError, Text, Toggle, register, table, trials, num

table("trials", "Trials", "One row per trial that was cut from the recording.",
      start="Start on the recording clock, ms.", end="End on the recording clock, ms.", duration="Length in ms.")


def glob_regex(pattern):
    """`*_start` → a regular expression whose first group is the part matched by *."""
    return re.compile("^" + re.escape(pattern.strip()).replace(r"\*", "(.*)") + "$", re.IGNORECASE)


@register
class TrialsFromEvents(Node):
    kind = "trials_from_events"
    title = "Cut trials from markers"
    group = "prepare"
    icon = "scissors"
    summary = "Use start and end markers in the recording to define trials."
    explain = """
        A glasses recording is one long stream: putting the glasses on, walking to the shelf, doing the task,
        chatting afterwards. Only parts of it are your experiment. Recordings usually contain **markers**
        (Tobii calls them events, EyeLink calls them messages) sent at the moments that matter.

        This step finds pairs of markers and turns the time between them into a trial. With the patterns
        `*_start` and `*_end`, the markers `search_start` … `search_end` become a trial called `search`.
        Samples outside every trial are dropped, because nothing can be concluded from them.
    """
    question = "Look at the Markers table of the input. Which moments were marked, and is the time between two markers really one unit of behaviour?"
    needs = ("samples", "events")
    makes = ("samples", "trials")
    view = "signal"
    params = (
        Text("start", "A trial starts at markers named", "*_start", help="* stands for any text; that text becomes the trial's name."),
        Text("end", "and ends at markers named", "*_end", help="Leave empty to end each trial where the next one starts."),
        Toggle("as_condition", "Use the trial's name as its condition", True,
               help="Handy when each marked interval is a different task."),
        Choice("outside", "Samples outside trials", "drop", options=(("drop", "Leave out"), ("keep", "Keep as trial “(between)”"))),
    )

    def run(self, data, p, ctx):
        if not p["start"].strip():
            raise PipelineError("Enter the name of the markers that start a trial, for example *_start.")
        start_rx, end_rx = glob_regex(p["start"]), glob_regex(p["end"]) if p["end"].strip() else None
        samples, events = data.samples, data["events"]
        time, who = samples["time"].to_numpy(float), samples["participant"].to_numpy()
        trial = np.full(len(samples), None, object)
        rows = []
        for participant, marks in events.groupby("participant", sort=False):
            marks = marks.sort_values("time")
            labels, times = marks["label"].astype(str).tolist(), marks["time"].to_numpy(float)
            starts = [(i, start_rx.match(label)) for i, label in enumerate(labels)]
            starts = [(i, m) for i, m in starts if m]
            mine, seen = who == participant, {}
            for n, (i, match) in enumerate(starts):
                name = (match.group(1) if match.groups() else labels[i]) or labels[i]
                stop = times[starts[n + 1][0]] if n + 1 < len(starts) else np.inf
                if end_rx:
                    for j in range(i + 1, len(labels)):
                        found = end_rx.match(labels[j])
                        if found and (not found.groups() or not match.groups() or found.group(1).casefold() == name.casefold()):
                            stop = min(stop, times[j])
                            break
                seen[name] = seen.get(name, 0) + 1
                label = name if seen[name] == 1 else f"{name}#{seen[name]}"
                inside = mine & (time >= times[i]) & (time < stop)
                if inside.any():
                    trial[inside] = label
                    rows.append(dict(participant=participant, trial=label, condition=name, start=times[i],
                                     end=float(time[inside].max()), duration=float(time[inside].max() - times[i])))
        if not rows:
            known = ", ".join(sorted(set(events["label"].astype(str)))[:8])
            raise PipelineError(f"No markers are named like “{p['start']}”. The recording has: {known}.")
        found = pd.notna(trial)
        trial[~found] = "(between)"
        samples = samples.assign(trial=trial)
        if p["as_condition"]:
            lookup = {(r["participant"], r["trial"]): r["condition"] for r in rows}
            samples["condition"] = [lookup.get(key) for key in zip(who, trial)]
        if p["outside"] == "drop":
            samples = samples[found].reset_index(drop=True)
        cut = pd.DataFrame(rows)
        if not p["as_condition"]:
            cut = cut.drop(columns="condition")
        note = (f"{len(rows)} trials cut from markers; {num(int((~found).sum()))} samples outside trials "
                f"{'left out' if p['outside'] == 'drop' else 'kept'}.")
        return data.update(note, samples=samples, trials=cut)


@register
class TrialInfo(Node):
    kind = "trial_info"
    title = "Add trial information"
    group = "prepare"
    icon = "tags"
    summary = "Attach conditions or stimulus names from a small table you type or paste."
    explain = """
        Eye-tracker files often know *that* trial 7 happened but not *what* it was: which condition, which picture.
        That knowledge usually lives in the experiment's own log. Paste it here as a small table with a
        `trial` column (and a `participant` column if trials differ between people) and any columns to add,
        typically `condition` and `stimulus`.

        The pasted table is saved with the pipeline, so the analysis stays reproducible.
    """
    question = "Is the condition a property of the trial, of the participant, or of both?"
    makes = ("samples",)
    view = "table:samples"
    params = (
        Text("rows", "Trial table (CSV)", "trial,condition\n1,easy\n2,hard\n", multiline=True,
             help="First line: column names. Needs a trial column; a participant column is optional."),
    )

    def run(self, data, p, ctx):
        try:
            lookup = pd.read_csv(StringIO(p["rows"]), sep=None, engine="python", dtype=str, skipinitialspace=True).dropna(how="all")
        except Exception as exc:
            raise PipelineError(f"The trial table could not be read: {exc}") from exc
        lookup.columns = [c.strip().casefold() for c in lookup.columns]
        keys = [k for k in KEYS if k in lookup.columns]
        if "trial" not in keys or len(lookup.columns) == len(keys):
            raise PipelineError("The table needs a “trial” column and at least one column to add, e.g. condition.")
        if lookup.duplicated(keys).any():
            raise PipelineError("The table lists the same trial twice.")
        added = [c for c in lookup.columns if c not in keys]
        samples = data.samples.drop(columns=[c for c in added if c in data.samples.columns])
        merged = samples.merge(lookup, on=keys, how="left")
        unmatched = merged.loc[merged[added[0]].isna(), KEYS].drop_duplicates()
        front = [*KEYS, *added]
        merged = merged[[*front, *[c for c in merged.columns if c not in front]]]
        note = f"Added {', '.join(added)} to {len(samples.groupby(KEYS)) - len(unmatched)} trials."
        if len(unmatched):
            note += f" {len(unmatched)} trials have no row in the table and stay empty."
        return data.update(note, samples=merged)


@register
class Crop(Node):
    kind = "crop"
    title = "Trim trials in time"
    group = "prepare"
    icon = "crop"
    summary = "Keep only a time window of each trial."
    explain = """
        Trials often begin before the interesting part: a fixation cross, a countdown, the moment the picture
        loads. This step keeps a window of each trial, measured from the trial's first sample, and drops the rest.

        Trimming changes every measure that depends on trial length: number of fixations, dwell time,
        time to first fixation. Decide the window before looking at the results.
    """
    question = "If you cut the first 200 ms, which fixations disappear, and would that change who looked at the target first?"
    makes = ("samples",)
    view = "signal"
    params = (
        Number("start_ms", "Keep from", 0, unit="ms", min=0, max=3.6e6, step=50, help="Counted from the start of each trial."),
        Number("end_ms", "Keep until", 0, unit="ms", min=0, max=3.6e6, step=50, help="0 keeps everything to the end of the trial."),
    )

    def run(self, data, p, ctx):
        if p["end_ms"] and p["end_ms"] <= p["start_ms"]:
            raise PipelineError("“Keep until” must be later than “Keep from” (or 0 for the end of the trial).")
        samples = data.samples
        time, keep = samples["time"].to_numpy(float), np.zeros(len(samples), bool)
        for rows in trials(samples).values():
            since = time[rows] - time[rows[0]]
            keep[rows] = (since >= p["start_ms"]) & ((since < p["end_ms"]) if p["end_ms"] else True)
        if not keep.any():
            raise PipelineError("No samples fall inside this window.")
        window = f"{p['start_ms']:g} ms to " + (f"{p['end_ms']:g} ms" if p["end_ms"] else "the end")
        return data.update(f"Kept {window} of each trial: {num(int(keep.sum()))} of {num(len(keep))} samples.",
                           samples=samples[keep].reset_index(drop=True))
