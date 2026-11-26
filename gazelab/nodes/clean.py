"""Cleaning the signal: off-screen gaze, blinks, gaps, noise, pupil baseline.

Off-screen gaze, blinks and smoothing are done by pymovements (see bridge.py).
pymovements has no gap filling with a length limit and no pupil baseline, so
those two steps are written here.
"""
import numpy as np

from ..bridge import GazeStep, call, cleaned_samples, events_table
from ..core import Choice, Node, Number, PipelineError, pct, register, runs, table, trials, num

table("blinks", "Blinks", "One row per blink that pymovements found in the pupil signal.",
      blink="Order of the blink within its trial.", start="Start, ms from the start of the trial.",
      end="Time of the blink's last sample, ms from the start of the trial.", duration="Length in ms.")

CHANNELS = Choice("channels", "Apply to", "both", options=(("both", "Gaze and pupil"), ("gaze", "Gaze only"), ("pupil", "Pupil only")))


def chosen(channels):
    return [c for c in ("x", "y", "pupil") if channels == "both" or (channels == "gaze") == (c != "pupil")]


def removed(before, after):
    """How many samples lost a value in a cleaning step."""
    return int((after["masked"].to_numpy() & ~before["masked"].to_numpy()).sum())


@register
class OffScreen(GazeStep):
    kind = "offscreen"
    title = "Remove off-screen gaze"
    group = "clean"
    icon = "frame"
    summary = "Treat gaze far outside the screen as missing."
    explain = """
        A tracker can report positions that are physically impossible, such as far beyond the edge of the screen.
        They appear when the tracker briefly locks onto an eyelash or a reflection, or just before it loses
        the eye in a blink. Such samples are not “looking away”; they are measurement errors.

        pymovements marks every stretch of gaze outside the screen (plus a tolerance) as an `out_of_screen`
        event and then empties the samples inside those events. The rows stay, so time keeps running evenly.
        Pupil size is emptied together with gaze, because a sample this wrong cannot be trusted for either.
    """
    question = "Is gaze 30 pixels beyond the edge an error, or a real look at the monitor's frame? What tolerance is defensible?"
    makes = ("samples",)
    view = "gaze"
    shows = "samples"
    params = (Number("margin_px", "Tolerance beyond the edge", 50, unit="px", min=0, max=5000, step=10),)

    def calls(self, p, data):
        margin, width, height = p["margin_px"], data.meta["width_px"], data.meta["height_px"]
        return [
            call("detect", "out_of_screen", x_min=-margin, x_max=width + margin, y_min=-margin, y_max=height + margin),
            call("nullify_event_samples", "out_of_screen", padding=0),
        ]

    def keep(self, data, gaze, p):
        samples = cleaned_samples(gaze, data.samples)
        off = removed(data.samples, samples)
        return data.update(f"{num(off)} samples ({pct(off, len(samples))}) lay outside the screen and were set to missing.", samples=samples)


@register
class Blinks(GazeStep):
    kind = "blinks"
    title = "Detect and remove blinks"
    group = "clean"
    icon = "eye-off"
    summary = "Find blinks in the pupil signal and remove the distorted samples around them."
    explain = """
        When the eyelid closes the tracker loses the pupil, so a blink shows up as a short stretch of missing
        pupil data, typically 100 to 400 ms. The damage is wider than the gap: while the lid is moving it
        covers part of the pupil, so the pupil seems to shrink and the gaze seems to dive. Those samples look
        valid but are not.

        pymovements looks for samples where the pupil is missing or changes impossibly fast, joins neighbouring
        candidates, and keeps the stretches whose length fits a blink. Longer losses (the person looked away,
        or the tracker lost the eye) are not blinks and stay as they are. The samples inside each blink, plus
        a margin on both sides, are then emptied.
    """
    question = "Open the signal view and zoom into one blink. How many samples around the gap look distorted? Is your margin wide enough, or too wide?"
    makes = ("samples", "blinks")
    view = "signal"
    params = (
        Number("min_ms", "Shortest blink", 60, unit="ms", min=1, max=1000, step=10, integer=True, help="Shorter losses are treated as flicker, not blinks."),
        Number("max_ms", "Longest blink", 500, unit="ms", min=50, max=5000, step=50, integer=True, help="Longer losses are treated as lost tracking."),
        Number("margin_ms", "Margin removed on each side", 50, unit="ms", min=0, max=500, step=10, integer=True),
    )

    def calls(self, p, data):
        if p["max_ms"] <= p["min_ms"]:
            raise PipelineError("The longest blink must be longer than the shortest.")
        if not data.samples["pupil"].notna().any():
            raise PipelineError("pymovements finds blinks in the pupil signal, and this recording has none. Map a pupil column in the Load step.")
        return [
            call("detect", "blink", minimum_duration=p["min_ms"], maximum_duration=p["max_ms"]),
            call("nullify_event_samples", "blink", padding=(p["margin_ms"], p["margin_ms"])),
        ]

    def keep(self, data, gaze, p):
        s = data.samples
        samples, blinks = cleaned_samples(gaze, s), events_table(gaze, "blink", s, "blink")
        minutes = sum(s["time"].iloc[at[-1]] - s["time"].iloc[at[0]] for at in trials(s).values()) / 60000
        newly = removed(s, samples)
        note = (f"{num(len(blinks))} blink{'s' * (len(blinks) != 1)} ({len(blinks) / minutes:.1f} per minute). {num(newly)} samples in and around them were removed "
                f"({pct(newly, len(s))} of the data).")
        return data.update(note, samples=samples, blinks=blinks)


@register
class Interpolate(Node):
    kind = "interpolate"
    title = "Fill short gaps"
    group = "clean"
    icon = "spline"
    summary = "Bridge brief losses with a straight line between the neighbouring samples."
    explain = """
        One or two lost samples in the middle of a fixation would split it in two. Trackers lose single samples
        all the time, so short gaps are usually bridged by drawing a straight line from the last valid sample
        to the next one. Tobii's default is to fill gaps up to 75 ms, shorter than any blink.

        Filling is an **estimate**, not a measurement. A long gap can hide a saccade to somewhere else and
        back. Filled samples are flagged in the `filled` column so they can be told apart later.
    """
    question = "Raise the limit to 500 ms and look at a blink. What does the straight line claim the eye was doing while it was closed?"
    makes = ("samples",)
    view = "signal"
    params = (
        Number("max_gap_ms", "Longest gap to fill", 75, unit="ms", min=0, max=5000, step=25,
               help="Measured between the valid samples on either side."),
        CHANNELS,
    )

    def run(self, data, p, ctx):
        s = data.samples
        time, filled, columns = s["time"].to_numpy(float), s["filled"].to_numpy().copy(), {}
        for channel in chosen(p["channels"]):
            values = s[channel].to_numpy(float).copy()
            for at in trials(s).values():
                t, v = time[at], values[at]
                for a, b in runs(~np.isfinite(v)):
                    if a > 0 and b < len(v) and t[b] - t[a - 1] <= p["max_gap_ms"]:
                        v[a:b] = np.interp(t[a:b], [t[a - 1], t[b]], [v[a - 1], v[b]])
                        filled[at[a:b]] = True
                values[at] = v
            columns[channel] = values
        count = int((filled & ~s["filled"].to_numpy()).sum())
        note = f"{num(count)} samples estimated by linear interpolation ({pct(count, len(s))}). Gaps longer than {p['max_gap_ms']:g} ms and gaps at the edge of a trial stay empty."
        return data.update(note, samples=s.assign(**columns, filled=filled))


@register
class Smooth(GazeStep):
    kind = "smooth"
    title = "Reduce noise"
    group = "clean"
    icon = "waves"
    summary = "Smooth the gaze signal with a small moving window."
    explain = """
        Even a perfectly still eye produces a jittery signal, because every measurement carries a small random
        error. Smoothing replaces each sample by a summary of its neighbours. Two of pymovements' methods are offered:

        - **Moving average**: the mean of the window. Simple, but it blurs saccades and makes them look slower.
        - **Savitzky–Golay**: fits a small curve through each window and preserves peaks best.

        More smoothing is not better: a wide window swallows short fixations and small saccades. The window
        is counted in samples, so its length in time depends on the tracker's speed. A window that touches
        missing data has no result, so gaps grow by a few samples; fill short gaps first.

        Only gaze is smoothed. pymovements does not smooth pupil size.
    """
    question = "Compare input and output around one saccade. At which window size does the saccade's peak speed visibly drop?"
    makes = ("samples",)
    view = "signal"
    shows = "samples"
    params = (
        Choice("method", "Method", "savitzky_golay", options=(("moving_average", "Moving average"), ("savitzky_golay", "Savitzky–Golay"))),
        Number("window", "Window", 5, unit="samples", min=3, max=201, step=2, integer=True, help="At 100 samples per second, 5 samples span 50 ms."),
    )

    def calls(self, p, data):
        fit = dict(degree=2) if p["method"] == "savitzky_golay" else {}
        return [call("smooth", p["method"], window_length=p["window"], column="pixel", **fit)]

    def keep(self, data, gaze, p):
        samples = cleaned_samples(gaze, data.samples)
        period = 1000 / data.meta["sampling_hz"]
        name = self.param("method").options[[v for v, _ in self.param("method").options].index(p["method"])][1]
        note = (f"{name} over {p['window']} samples (about {p['window'] * period:.0f} ms), within each trial. "
                f"{num(removed(data.samples, samples))} samples next to missing data lost their value.")
        return data.update(note, samples=samples)


@register
class Baseline(Node):
    kind = "baseline"
    title = "Baseline-correct pupil"
    group = "clean"
    icon = "align-vertical"
    summary = "Express pupil size as change from the start of each trial."
    explain = """
        Pupil size differs between people and drifts over minutes with light, fatigue and arousal. What an
        experiment usually cares about is the **change** a stimulus causes. So each trial's pupil trace is
        compared with a short baseline window at its start.

        *Subtractive* correction (pupil − baseline) is the recommended default; *divisive* correction
        (percent change) inflates noise when the baseline happens to be small. A blink inside the baseline
        window ruins the whole trial, so trials with too little valid baseline are excluded rather than corrected badly.
    """
    question = "Move the baseline window later, into the response itself. What happens to the apparent size of the effect?"
    makes = ("samples",)
    view = "signal"
    params = (
        Number("start_ms", "Baseline from", 0, unit="ms", min=0, max=60000, step=50, help="Counted from the start of each trial."),
        Number("end_ms", "Baseline until", 200, unit="ms", min=1, max=60000, step=50),
        Choice("method", "Correction", "subtract", options=(("subtract", "Subtract (change in tracker units)"), ("divide", "Divide (percent change)"))),
    )

    def run(self, data, p, ctx):
        if p["end_ms"] <= p["start_ms"]:
            raise PipelineError("The baseline must end after it starts.")
        if data.meta.get("pupil_unit") != "as recorded":
            raise PipelineError("The pupil signal is already baseline-corrected. Correcting twice has no meaning.")
        s = data.samples
        time, pupil, measured = s["time"].to_numpy(float), s["pupil"].to_numpy(float).copy(), ~s["filled"].to_numpy()
        if not np.isfinite(pupil).any():
            raise PipelineError("This recording has no pupil signal. Map a pupil column in the Load step.")
        excluded = 0
        for at in trials(s).values():
            since = time[at] - time[at[0]]
            window = (since >= p["start_ms"]) & (since < p["end_ms"])
            usable = window & np.isfinite(pupil[at]) & measured[at]
            if window.sum() < 2 or usable.sum() < max(2, 0.5 * window.sum()):
                pupil[at], excluded = np.nan, excluded + 1
                continue
            base = pupil[at][usable].mean()
            pupil[at] = pupil[at] - base if p["method"] == "subtract" else 100 * (pupil[at] - base) / base
        unit = "change from baseline" if p["method"] == "subtract" else "% change from baseline"
        note = (f"Each trial's pupil is now {unit} (mean of {p['start_ms']:g}–{p['end_ms']:g} ms). "
                f"{excluded} trial(s) had less than half a valid baseline and were excluded.")
        return data.update(note, meta=dict(pupil_unit=unit), samples=s.assign(pupil=pupil))
