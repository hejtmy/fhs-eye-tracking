"""Reducing a recording to tables for statistics software."""
import re

import numpy as np
import pandas as pd

from ..core import KEYS, Choice, Columns, Node, PipelineError, TableName, register, table, trial_info, trials

table("trial_summary", "Trial summary", "One row per participant and trial with the usual quality and behaviour measures.",
      duration_ms="Length of the trial.", valid_gaze_pct="Share of samples with a gaze position.",
      pupil_mean="Mean pupil size over the trial.", blink_count="Number of blinks.", fixation_count="Number of fixations.",
      fixation_mean_ms="Mean fixation duration.", saccade_count="Number of saccades.", saccade_amplitude_deg="Mean saccade size in degrees.")
table("summary", "Summary", "The table you asked for, ready for JASP, jamovi, R or a spreadsheet.")

PREFERRED = ("aoi_metrics", "patterns", "transitions", "trial_summary", "fixations")
NOT_MEASURES = {"trial", "fixation", "saccade", "blink", "x", "y", "w", "h", "start", "end", "time"}


@register
class TrialSummary(Node):
    kind = "trial_summary"
    title = "Summarise each trial"
    group = "summarise"
    icon = "list"
    summary = "One row per trial: data quality, fixations, saccades, blinks, pupil."
    explain = """
        Statistics are run on one number per participant and condition, not on thousands of samples. This step
        reduces every trial to one row. What the row contains depends on the steps before it: fixation
        measures appear only after fixation detection, blink counts only after blink detection.

        Look at **valid_gaze_pct** first. A trial with half of its samples missing produces a fixation count
        that means little. Decide on an exclusion rule (for example, less than 75% valid) *before* comparing conditions.
    """
    question = "Sort the table by valid_gaze_pct. Would you keep the worst trial? Would your answer change if it supported your hypothesis?"
    makes = ("trial_summary",)
    view = "table:trial_summary"

    def run(self, data, p, ctx):
        s = data.samples
        time, pupil = s["time"].to_numpy(float), s["pupil"].to_numpy(float)
        has_gaze = np.isfinite(s[["x", "y"]].to_numpy(float)).all(axis=1)
        rows = []
        for (participant, trial), at in trials(s).items():
            row = dict(participant=participant, trial=trial, duration_ms=time[at[-1]] - time[at[0]], samples=len(at),
                       valid_gaze_pct=round(100 * has_gaze[at].mean(), 1))
            if np.isfinite(pupil).any():
                row["valid_pupil_pct"] = round(100 * np.isfinite(pupil[at]).mean(), 1)
                row["pupil_mean"] = np.nanmean(pupil[at]) if np.isfinite(pupil[at]).any() else np.nan
            rows.append(row)
        out = trial_info(s).drop(columns="trial_start").merge(pd.DataFrame(rows), on=KEYS)

        def add(name, **measures):
            if name in data:
                grouped = data[name].groupby(KEYS, sort=False).agg(**measures).reset_index()
                merged = out.merge(grouped, on=KEYS, how="left")
                counts = [c for c in measures if c.endswith("_count")]
                merged[counts] = merged[counts].fillna(0).astype(int)
                return merged
            return out
        out = add("blinks", blink_count=("duration", "size"))
        out = add("fixations", fixation_count=("duration", "size"), fixation_mean_ms=("duration", "mean"), fixation_total_ms=("duration", "sum"))
        out = add("saccades", saccade_count=("duration", "size"), saccade_amplitude_deg=("amplitude_deg", "mean"))
        low = int((out["valid_gaze_pct"] < 75).sum())
        return data.update(f"{len(out)} trials summarised. {low} of them have less than 75% valid gaze.", trial_summary=out)

    def headline(self, out):
        return f"{len(out['trial_summary'])} trials"


@register
class Aggregate(Node):
    kind = "aggregate"
    title = "Build a table for statistics"
    group = "summarise"
    icon = "sheet"
    summary = "Average or sum any table per participant and condition; long or wide layout."
    explain = """
        The last step before statistics: collapse trials into the unit your test compares, usually one value per
        **participant and condition**.

        - **Mean** suits measures per trial (dwell time, fixation duration). **Sum** suits counts you want in total
          (how often did each pattern occur overall?).
        - **Long** layout has one row per participant and condition, as mixed models and R expect.
          **Wide** layout has one row per participant and one column per condition, as repeated-measures
          ANOVA and paired t-tests in JASP and jamovi expect.

        Download the result as CSV from the Output panel and open it directly in JASP (File → Open) or jamovi (☰ → Open).
    """
    question = "What is one row in your table, and is that the same unit your statistical test assumes?"
    makes = ("summary",)
    view = "table:summary"
    params = (
        TableName("table", "Table to summarise", "", help="Leave on automatic to use the most recent result table."),
        Columns("by", "One row per", table_from="table", help="Leave empty for participant and every describing column, averaging over trials."),
        Choice("stat", "Combine trials by", "mean", options=(("mean", "Mean"), ("sum", "Sum"), ("median", "Median"), ("count", "Count of rows"))),
        Choice("layout", "Layout", "long", options=(("long", "Long: one row per combination"), ("wide", "Wide: one row per participant"))),
    )

    def run(self, data, p, ctx):
        name = p["table"] or next((t for t in PREFERRED if t in data), None)
        if not name or name not in data:
            raise PipelineError("Choose a table to summarise. Result tables appear after steps such as “Measure attention per area” or “Summarise each trial”.")
        if name == "samples":
            raise PipelineError("Summarise events or measures, not raw samples. Add “Summarise each trial” first.")
        frame = data[name]
        numeric = [c for c in frame.columns if frame[c].dtype.kind in "fiu" and c not in NOT_MEASURES]
        by = p["by"] or [c for c in frame.columns if c not in numeric and c not in NOT_MEASURES and c != "stimulus" and frame[c].dtype.kind not in "fiu"]
        missing = [c for c in by if c not in frame.columns]
        if missing:
            raise PipelineError(f"The {name.replace('_', ' ')} table has no column “{missing[0]}”.")
        values = [c for c in numeric if c not in by]
        if not by or not values:
            raise PipelineError("Nothing to summarise: the table needs at least one describing column and one numeric measure.")
        grouped = frame.groupby(by, sort=False, dropna=False)
        out = (grouped[values].agg(p["stat"]) if p["stat"] != "count" else grouped[values[:1]].size().to_frame("rows")).reset_index()
        if p["stat"] != "count":
            out["n"] = grouped.size().to_numpy()
        layout = "one row per " + " × ".join(by)
        if p["layout"] == "wide":
            if "participant" not in by or len(by) < 2:
                raise PipelineError("A wide table has one row per participant and spreads another column (e.g. condition) across columns. Include both under “One row per”.")
            spread = [c for c in by if c != "participant"]
            wide = out.pivot(index="participant", columns=spread, values=[c for c in out.columns if c not in by and c != "n"])
            wide.columns = [re.sub(r"[^0-9A-Za-z]+", "_", "_".join(map(str, column))).strip("_") for column in wide.columns]
            out, layout = wide.reset_index(), f"one row per participant, columns per measure × {' × '.join(spread)}"
        note = f"{dict(mean='Mean', sum='Sum', median='Median', count='Count')[p['stat']]} of the {name.replace('_', ' ')} table: {layout}. {len(out)} rows × {len(out.columns)} columns."
        return data.update(note, meta=dict(summary_of=name), summary=out)

    def headline(self, out):
        return f"{len(out['summary'])} × {len(out['summary'].columns)} table"
