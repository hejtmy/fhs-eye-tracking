"""Areas of interest: which regions matter, what was looked at, in which order."""
import re
from itertools import groupby

import numpy as np
import pandas as pd

from ..core import KEYS, Columns, Custom, Node, Number, PipelineError, Toggle, register, table, trial_info, trials, num

table("aois", "Areas of interest", "The regions as drawn or as named in the file.",
      name="Name of the area.", shape="rect or ellipse.", x="Left edge, pixels.", y="Top edge, pixels.", w="Width, pixels.",
      h="Height, pixels.", stimulus="The stimulus the area belongs to (empty = every stimulus).")
table("aoi_metrics", "AOI metrics", "One row per participant, trial and area of interest. Areas that were never looked at have zeros, not missing rows.",
      aoi="Area of interest.", fixation_count="Number of fixations in the area.", dwell_ms="Summed duration of those fixations.",
      dwell_pct="Dwell time as a share of all fixation time in the trial.", visits="How many times gaze entered the area.",
      first_fixation_ms="Time from trial start to the first fixation in the area (empty = never).",
      first_fixation_duration="Duration of that first fixation.", mean_fixation_ms="Mean fixation duration in the area.")
table("transitions", "Transitions", "How often gaze moved from one area directly to another, per participant and trial.",
      source="Area the gaze left.", target="Area the gaze entered.", count="Number of such moves.")
table("sequences", "AOI sequences", "The order in which areas were visited, one row per participant and trial.",
      sequence="Visited areas in order.", visits="Number of visits in the sequence.")
table("patterns", "Patterns", "How often each short sequence of areas occurred, per participant and trial.",
      pattern="Areas visited directly after one another.", count="Number of occurrences.")

OUTSIDE = "(outside)"


def clean_aois(value):
    if not isinstance(value, list) or len(value) > 200:
        raise PipelineError("Areas of interest must be a list of at most 200 shapes.")
    out = []
    for item in value:
        name = str(item.get("name", "")).strip() if isinstance(item, dict) else ""
        if not name or len(name) > 60:
            raise PipelineError("Every area of interest needs a name of 1–60 characters.")
        if item.get("shape") not in ("rect", "ellipse"):
            raise PipelineError(f"Area “{name}” must be a rectangle or an ellipse.")
        try:
            box = {k: float(item[k]) for k in ("x", "y", "w", "h")}
        except (KeyError, TypeError, ValueError):
            raise PipelineError(f"Area “{name}” needs a position and size in pixels.") from None
        if not all(np.isfinite(v) for v in box.values()) or box["w"] <= 0 or box["h"] <= 0:
            raise PipelineError(f"Area “{name}” needs a positive width and height.")
        out.append(dict(name=name, shape=item["shape"], **box, stimulus=str(item.get("stimulus") or "")))
    return out


def inside(shape, x, y):
    """Which points lie in a shape. x, y is the top-left corner of the shape's bounding box."""
    if shape["shape"] == "ellipse":
        rx, ry = shape["w"] / 2, shape["h"] / 2
        return ((x - shape["x"] - rx) / rx) ** 2 + ((y - shape["y"] - ry) / ry) ** 2 <= 1
    return (x >= shape["x"]) & (x <= shape["x"] + shape["w"]) & (y >= shape["y"]) & (y <= shape["y"] + shape["h"])


def assign(frame, shapes):
    """Name of the first listed shape that contains each row's x, y (empty when none does)."""
    x, y = frame["x"].to_numpy(float), frame["y"].to_numpy(float)
    stimulus = frame["stimulus"].to_numpy() if "stimulus" in frame else None
    label = np.full(len(frame), "", object)
    for shape in shapes:
        hit = inside(shape, x, y) & (label == "")
        if shape["stimulus"]:
            hit &= (stimulus == shape["stimulus"]) if stimulus is not None else False
        label[hit] = shape["name"]
    return label


def need_labels(data):
    fixations = data["fixations"]
    if "aoi" not in fixations.columns:
        raise PipelineError("The fixations are not yet assigned to areas of interest. Add “Draw areas of interest” or “Areas from file columns” before this step.")
    return fixations


def aoi_names(data, fixations):
    if "aois" in data:
        return list(dict.fromkeys(data["aois"]["name"]))
    return sorted(n for n in fixations["aoi"].unique() if n)


def visit_sequences(fixations, keep_outside):
    """{(participant, trial): [area, area, …]} with repeated fixations in one area collapsed to a single visit."""
    out = {}
    for key, group in fixations.sort_values("start").groupby(KEYS, sort=False):
        labels = [a or OUTSIDE for a in group["aoi"]]
        if not keep_outside:
            labels = [a for a in labels if a != OUTSIDE]
        out[key] = [a for a, _ in groupby(labels)]
    return out


@register
class DrawAois(Node):
    kind = "aoi_draw"
    title = "Draw areas of interest"
    group = "aoi"
    icon = "scan"
    summary = "Mark the regions of the stimulus you care about."
    explain = """
        Raw coordinates rarely answer a research question. “Did people look at the price?” needs a region
        called *price*. An **area of interest** (AOI) is a shape you draw on the stimulus; every fixation whose
        centre falls inside gets the area's name.

        AOIs are part of your hypothesis, so draw them before looking at where people looked. Leave a margin
        of about one degree around small objects: trackers are rarely more accurate than that. Where shapes
        overlap, the one listed first wins, so put small areas before large ones.

        An area can belong to one stimulus or to all of them. For glasses data, draw on the snapshot that the
        gaze was mapped onto, not on the moving scene video.
    """
    question = "Enlarge one area by 20 pixels on every side. Does the conclusion survive? If not, how much of your result is the tracker's accuracy?"
    makes = ("aois",)
    view = "gaze"
    params = (Custom("aois", "Areas of interest", default=[], control="aois", validate=clean_aois),)

    def run(self, data, p, ctx):
        shapes = p["aois"]
        if not shapes:
            raise PipelineError("No areas yet. Open the editor in this step's settings and draw at least one.")
        s = data.samples
        tables = dict(aois=pd.DataFrame(shapes), samples=s.assign(aoi=assign(s, shapes)))
        note = f"{len(shapes)} areas of interest. "
        if "fixations" in data:
            fixations = data["fixations"].assign(aoi=assign(data["fixations"], shapes))
            tables["fixations"] = fixations
            hits = (fixations["aoi"] != "").sum()
            note += f"{num(hits)} of {num(len(fixations))} fixations fall inside one."
        else:
            note += "Samples are labelled; add fixation detection before this step to label fixations too."
        if any(shape["stimulus"] for shape in shapes) and "stimulus" not in s:
            note += " Some areas belong to a stimulus, but the data have no stimulus column, so those areas match nothing."
        return data.update(note, **tables)

    def headline(self, out):
        return f"{len(out['aois'])} areas"


@register
class AoisFromColumns(Node):
    kind = "aoi_columns"
    title = "Areas from file columns"
    group = "aoi"
    icon = "columns"
    summary = "Use AOI hits that the recording software already computed."
    explain = """
        With glasses the scene moves with the head, so a shape drawn on the video would be in the wrong place a
        moment later. Tobii Pro Lab solves this by **mapping** gaze onto a still snapshot and can export, for
        every sample, whether it hit each area: one column per area, named like *AOI hit [Shelf - Milk]*,
        holding 1 or 0.

        This step reads those columns. A sample gets the name of the area it hit, and a fixation gets the area
        that most of its samples hit.
    """
    question = "A fixation of 12 samples has 7 hits on “Milk” and 5 on nothing. Did the person look at the milk? What rule would you write down in your methods section?"
    makes = ("aois",)
    view = "signal"
    params = (
        Columns("columns", "Columns that mark hits", pattern="aoi hit*", help="Leave empty to use every column whose name starts with “AOI hit”."),
        Number("majority", "A fixation belongs to an area if it holds at least", 50, unit="% of its samples", min=1, max=100, step=5),
    )

    def run(self, data, p, ctx):
        s = data.samples
        columns = self.param("columns").resolve(p["columns"], s)
        if not columns:
            raise PipelineError("No AOI hit columns were found. In the Load step, keep them under “Extra columns”.")
        names = [re.sub(r"^aoi hit\s*", "", c, flags=re.I).strip(" []") for c in columns]
        if all(" - " in n for n in names) and len({n.split(" - ", 1)[0] for n in names}) == 1:
            names = [n.split(" - ", 1)[1] for n in names]  # drop the shared snapshot name
        hits = np.column_stack([pd.to_numeric(s[c], errors="coerce").fillna(0).to_numpy() > 0 for c in columns])
        label = np.where(hits.any(axis=1), np.array(names, object)[hits.argmax(axis=1)], "")
        tables = dict(samples=s.assign(aoi=label), aois=pd.DataFrame(dict(name=names, column=columns)))
        note = f"{len(names)} areas from file columns: {', '.join(names[:8])}{'…' if len(names) > 8 else ''}."
        if "fixations" in data:
            fixations, time = data["fixations"], s["time"].to_numpy(float)
            where, area = trials(s), []
            for participant, trial, start, end in fixations[[*KEYS, "start", "end"]].itertuples(index=False):
                at = where[(participant, trial)]
                since = time[at] - time[at[0]]
                own = label[at[(since >= start - 1e-6) & (since < end - 1e-6)]]
                counts = pd.Series(own[own != ""]).value_counts()
                area.append(counts.index[0] if len(counts) and counts.iloc[0] >= p["majority"] / 100 * max(len(own), 1) else "")
            tables["fixations"] = fixations.assign(aoi=area)
            note += f" {num(sum(bool(a) for a in area))} of {num(len(area))} fixations lie in an area."
        return data.update(note, **tables)

    def headline(self, out):
        return f"{len(out['aois'])} areas"


@register
class AoiMetrics(Node):
    kind = "aoi_metrics"
    title = "Measure attention per area"
    group = "aoi"
    icon = "bar-chart"
    summary = "Dwell time, fixation count, visits and time to first fixation for every area."
    explain = """
        The standard AOI measures answer different questions:

        - **Dwell time** — how long was the area looked at in total? (interest, or difficulty)
        - **Fixation count** and **visits** — how often? A visit is an entry: three fixations in a row are one visit.
        - **Time to first fixation** — how quickly was it noticed? (salience, search efficiency)
        - **First fixation duration** — how long did the first look last? (early processing)

        Every participant × trial × area gets a row, **including areas nobody looked at** (zero dwell). Leaving
        those rows out is a classic mistake: the average would then describe only the trials in which the area was seen.
        Time to first fixation stays empty in that case, because “never” is not a number.
    """
    question = "Dwell time is longer in one condition. Was the area more interesting, or harder to understand? What other measure would tell these apart?"
    needs = ("samples", "fixations")
    makes = ("aoi_metrics",)
    view = "aoi_bars"

    def run(self, data, p, ctx):
        fixations, names = need_labels(data), None
        names = aoi_names(data, fixations)
        if not names:
            raise PipelineError("No fixation fell into any area of interest.")
        ordered = fixations.sort_values([*KEYS, "start"], kind="stable")
        entered = ordered["aoi"] != ordered.groupby(KEYS, sort=False)["aoi"].shift()
        hits = ordered[ordered["aoi"] != ""].assign(entered=entered)
        by_area = hits.groupby([*KEYS, "aoi"], sort=False)
        measured = by_area.agg(fixation_count=("duration", "size"), dwell_ms=("duration", "sum"), visits=("entered", "sum"),
                               first_fixation_ms=("start", "first"), first_fixation_duration=("duration", "first"),
                               mean_fixation_ms=("duration", "mean")).reset_index()
        total = ordered.groupby(KEYS, sort=False)["duration"].sum().rename("total").reset_index()

        # every trial × every area that applies to its stimulus, so that “not looked at” becomes a row of zeros
        info = trial_info(data.samples).drop(columns="trial_start")
        grid = info.merge(pd.DataFrame(dict(aoi=names)), how="cross")
        if "aois" in data and "stimulus" in data["aois"] and "stimulus" in grid:
            scope = data["aois"].groupby("name")["stimulus"].agg(set).to_dict()
            applies = [("" in scope[a]) or (s in scope[a]) for a, s in zip(grid["aoi"], grid["stimulus"])]
            grid = grid[applies]
        out = grid.merge(measured, on=[*KEYS, "aoi"], how="left").merge(total, on=KEYS, how="left")
        for column in ("fixation_count", "dwell_ms", "visits"):
            out[column] = out[column].fillna(0)
        out[["fixation_count", "visits"]] = out[["fixation_count", "visits"]].astype(int)
        out.insert(out.columns.get_loc("dwell_ms") + 1, "dwell_pct", (100 * out["dwell_ms"] / out.pop("total")).round(2))
        seen = (out["fixation_count"] > 0).mean()
        note = f"{num(len(out))} rows: {len(names)} areas × {len(info)} trials. Areas were looked at in {100 * seen:.0f}% of those rows; the rest are zeros."
        return data.update(note, aoi_metrics=out.reset_index(drop=True))


@register
class Transitions(Node):
    kind = "aoi_transitions"
    title = "Count transitions between areas"
    group = "aoi"
    icon = "shuffle"
    summary = "How often gaze moved from each area directly to each other area."
    explain = """
        Dwell time says *how much* each area was looked at, but not *how the areas were used together*.
        A **transition** is a move from one area straight to another. Counting them shows comparison
        behaviour: many moves between two products mean they were weighed against each other; many moves
        from a picture to its caption and back mean the two were integrated.

        Fixations outside every area can either be ignored (A → nothing → B counts as A → B) or kept as an
        area of their own. The choice changes the counts and has to be reported.
    """
    question = "Is A → B as frequent as B → A? What would an asymmetry tell you about how the display is read?"
    needs = ("samples", "fixations")
    makes = ("transitions",)
    view = "transition_matrix"
    params = (Toggle("keep_outside", "Count “outside every area” as an area", False),)

    def run(self, data, p, ctx):
        fixations = need_labels(data)
        names = aoi_names(data, fixations) + ([OUTSIDE] if p["keep_outside"] else [])
        pairs = [(a, b) for a in names for b in names if a != b]
        rows = []
        for (participant, trial), sequence in visit_sequences(fixations, p["keep_outside"]).items():
            counts = pd.Series(list(zip(sequence, sequence[1:]))).value_counts().to_dict() if len(sequence) > 1 else {}
            rows += [(participant, trial, a, b, counts.get((a, b), 0)) for a, b in pairs]
        out = pd.DataFrame(rows, columns=["participant", "trial", "source", "target", "count"])
        info = trial_info(data.samples).drop(columns="trial_start")
        out = info.merge(out, on=KEYS, how="inner")
        return data.update(f"{num(int(out['count'].sum()))} transitions between {len(names)} areas.", transitions=out)

    def headline(self, out):
        return f"{num(int(out['transitions']['count'].sum()))} transitions"


@register
class Patterns(Node):
    kind = "aoi_patterns"
    title = "Find viewing patterns"
    group = "aoi"
    icon = "route"
    summary = "The order in which areas were visited, and how often each short sequence occurs."
    explain = """
        A **scanpath** is the order in which areas were visited, for example *Logo → Price → Product → Price*.
        Whole scanpaths are almost never identical between two people, so they are compared through their
        building blocks: every run of *n* consecutive visits is a **pattern**. With n = 2 a pattern is a
        transition; with n = 3, *Price → Product → Price* captures a look back, which a transition count cannot.

        The step writes two tables: the full sequence of every trial, and how often each pattern occurred in
        every trial. Sum the counts over trials (with the summary step) to find the dominant strategies.
    """
    question = "Which pattern is most common? Is that a property of the people, or of where the designer placed things?"
    needs = ("samples", "fixations")
    makes = ("sequences", "patterns")
    view = "pattern_bars"
    params = (
        Number("length", "Pattern length", 3, unit="visits", min=2, max=6, integer=True),
        Toggle("keep_outside", "Count “outside every area” as an area", False),
    )

    def run(self, data, p, ctx):
        fixations, n = need_labels(data), p["length"]
        sequences, patterns = [], []
        for (participant, trial), sequence in visit_sequences(fixations, p["keep_outside"]).items():
            sequences.append((participant, trial, " → ".join(sequence), len(sequence)))
            grams = pd.Series([" → ".join(sequence[i:i + n]) for i in range(len(sequence) - n + 1)], dtype="str").value_counts()
            patterns += [(participant, trial, pattern, count) for pattern, count in grams.items()]
        info = trial_info(data.samples).drop(columns="trial_start")
        sequences = info.merge(pd.DataFrame(sequences, columns=["participant", "trial", "sequence", "visits"]), on=KEYS, how="left")
        patterns = info.merge(pd.DataFrame(patterns, columns=["participant", "trial", "pattern", "count"]), on=KEYS, how="inner")
        distinct = patterns["pattern"].nunique()
        note = f"{distinct} different patterns of {n} visits; {num(int(patterns['count'].sum()))} occurrences in total."
        return data.update(note, sequences=sequences.fillna(dict(sequence="", visits=0)), patterns=patterns)

    def headline(self, out):
        return f"{out['patterns']['pattern'].nunique()} patterns"
