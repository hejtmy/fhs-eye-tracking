"""From samples to events: fixations and saccades, detected by pymovements (see bridge.py)."""
import numpy as np
import polars as pl
import pymovements as pm

from ..bridge import GazeStep, call, count, events_table, speed, to_gaze
from ..core import KEYS, Choice, Columns, Node, Number, PipelineError, Text, register, runs, table, trials, num

table("fixations", "Fixations", "One row per period in which the eye rested on one place.",
      fixation="Order of the fixation within its trial.", start="Start, ms from the start of the trial.",
      end="Time of the fixation's last sample, ms from the start of the trial.", duration="Length in ms.",
      x="Mean horizontal position, pixels.", y="Mean vertical position, pixels.",
      dispersion_deg="Spread of the gaze during the fixation: width plus height of its bounding box, in degrees.",
      aoi="Area of interest the fixation fell in (empty = none).")
table("saccades", "Saccades", "One row per fast jump of the eye.",
      saccade="Order of the saccade within its trial.", start="Start, ms from the start of the trial.",
      end="Time of the saccade's last sample, ms from the start of the trial.", duration="Length in ms.",
      amplitude_deg="Distance covered, degrees of visual angle.", peak_velocity="Highest speed during the jump, °/s.")

# What is worked out for every fixation: where the gaze rested (in pixels, to draw it on the stimulus) and how far it spread.
LOCATION = ("location", {"position_column": "pixel"})
FIXATION_PROPERTIES = ["dispersion", LOCATION]

VELOCITY = (
    Choice("velocity", "Speed is measured by", "savitzky_golay", options=(
        ("savitzky_golay", "Savitzky–Golay: a curve fitted through a few samples"),
        ("fivepoint", "Five-point: weighted difference over two samples each way"),
        ("neighbors", "Neighbours: the sample before and the sample after"),
        ("preceding", "Preceding: the sample before only"),
    ), help="Noisy recordings need a method that looks at more samples; slow trackers need one that looks at fewer."),
    Number("velocity_window", "Samples in the fitted curve", 5, unit="samples", min=3, max=51, step=2, integer=True, when=dict(velocity="savitzky_golay")),
)


def velocity_call(p):
    fit = dict(window_length=p["velocity_window"], degree=2) if p["velocity"] == "savitzky_golay" else {}
    return call("pos2vel", p["velocity"], **fit)


def found(table, what, extra=""):
    """What a detector reports about its result."""
    if not len(table):
        return f" No {what} were found: the settings are probably too strict for this recording."
    return f" Found {num(len(table))} {what} (median {table['duration'].median():.0f} ms){extra}."


@register
class FixationsIVT(GazeStep):
    kind = "fixations_ivt"
    title = "Detect fixations by speed (I-VT)"
    group = "detect"
    icon = "gauge"
    summary = "Slow samples are fixation, fast samples are saccade."
    explain = """
        The eye alternates between **fixations** (resting on a spot for 200–400 ms, when we actually see) and
        **saccades** (jumps of 20–80 ms, when we are practically blind). Nobody marks these in the recording:
        an algorithm has to decide which samples belong to which.

        I-VT, the *velocity-threshold* method, looks at how fast the gaze moves. pymovements first converts
        pixels to degrees of visual angle, then works out the speed at every sample. Samples slower than the
        threshold are fixation candidates; uninterrupted runs of candidates become fixations, and runs that
        are too short are discarded.

        Nothing is repaired afterwards: one noisy sample above the threshold splits a fixation in two. If
        you see that in the signal view, measure speed over more samples or smooth the gaze first.

        30 °/s is the usual threshold in front of a screen. With glasses the head moves and the eyes
        counter-rotate, so a higher threshold (about 100 °/s) is common.
    """
    question = "Halve the threshold, then double it. Do you get more fixations or fewer, longer or shorter? Which setting is “right”, and how would you know?"
    makes = ("samples", "fixations")
    view = "signal"
    params = (
        Number("threshold", "Speed threshold", 30, unit="°/s", min=0.1, max=2000, step=5,
               help="30 °/s is usual in front of a screen, about 100 °/s with glasses."),
        *VELOCITY,
        Number("min_duration_ms", "Shortest fixation", 60, unit="ms", min=1, max=2000, step=10, integer=True,
               help="Shorter candidates are discarded: the eye needs time to take anything in."),
    )

    def calls(self, p, data):
        return [
            call("pix2deg"),
            velocity_call(p),
            call("detect", "ivt", velocity_threshold=p["threshold"], minimum_duration=p["min_duration_ms"]),
            call("compute_event_properties", FIXATION_PROPERTIES, name="fixation"),
        ]

    def keep(self, data, gaze, p):
        fixations = events_table(gaze, "fixation", data.samples, "fixation")
        note = f"I-VT: samples slower than {p['threshold']:g} °/s are fixation; runs of at least {p['min_duration_ms']} ms are kept." + found(fixations, "fixations")
        return data.update(note, meta=dict(velocity_unit="°/s", velocity_threshold=p["threshold"]),
                           samples=data.samples.assign(velocity=speed(gaze)), fixations=fixations)


def even_clock(samples, period):
    """Timestamps the way pymovements' I-DT needs them: whole numbers, evenly spaced.

    Where the tracker's period is a whole number of milliseconds the clock counts milliseconds,
    otherwise it counts samples. It restarts in every trial, and wherever samples are missing from
    the file, so that each uninterrupted stretch is even. Returns (time, stretch number, units per sample).
    """
    time = samples["time"].to_numpy(float)
    step = round(period) if round(period) >= 1 and abs(period - round(period)) < 0.02 * period else 1
    since = np.rint(np.diff(time, prepend=time[0]) / period)   # samples since the previous row
    breaks = (samples[KEYS] != samples[KEYS].shift()).any(axis=1).to_numpy() | (since != 1)
    row = np.arange(len(time))
    return (row - np.maximum.accumulate(np.where(breaks, row, 0))) * step, np.cumsum(breaks), step


@register
class FixationsIDT(GazeStep):
    kind = "fixations_idt"
    title = "Detect fixations by spread (I-DT)"
    group = "detect"
    icon = "focus"
    summary = "Samples that stay within a small area long enough are a fixation."
    explain = """
        I-DT, the *dispersion-threshold* method, asks a different question from I-VT: not “how fast is the
        gaze moving?” but “do these samples stay together?”.

        It slides a window over the signal that is as long as the shortest allowed fixation. If the samples in
        the window are spread over less than the threshold (width plus height of their bounding box), the
        window grows sample by sample until the spread becomes too large. That stretch is one fixation.
        Otherwise the window moves on by one sample.

        I-DT copes well with slow trackers (30–60 samples per second), where speed is hard to estimate.
        Its two settings interact strongly: a generous spread with a short duration turns almost everything into fixation.

        pymovements' I-DT counts the shortest duration in whole samples and needs evenly spaced timestamps.
        The step reports how many samples your duration became. It also closes each fixation on the sample
        that broke the limit, so a fixation reaches one sample into the saccade that follows it. For that
        reason the spread of the finished fixations is not reported here.
    """
    question = "Run I-VT and I-DT as two branches from the same step and compare the fixation counts. Both are “fixation detection”. Why do they disagree?"
    makes = ("fixations",)
    view = "gaze"
    params = (
        Number("dispersion", "Largest spread", 1.0, unit="°", min=0.01, max=90, step=0.1, help="Width plus height of the box around the samples."),
        Number("min_duration_ms", "Shortest fixation", 100, unit="ms", min=10, max=2000, step=10, integer=True),
    )

    def clock_of(self, p, data):
        """(time, stretch, units per sample, shortest fixation in samples) for this recording."""
        period = 1000 / data.meta["sampling_hz"]
        time, stretch, step = even_clock(data.samples, period)
        return time, stretch, step, max(2, round(p["min_duration_ms"] / period))

    def used(self, p, data):
        """(time, stretch, alone): the samples I-DT is given, and which ones it is not.

        A sample alone between two gaps in the timestamps (common with webcam trackers, whose frames
        arrive unevenly) can never be a fixation, and pymovements' I-DT cannot take a stretch of one sample.
        """
        time, stretch, *_ = self.clock_of(p, data)
        alone = np.bincount(stretch)[stretch] < 2
        return time[~alone], stretch[~alone], alone

    def gaze(self, data, p):
        time, stretch, alone = self.used(p, data)
        return to_gaze(data.update(samples=data.samples[~alone].reset_index(drop=True)), time=time, stretch=stretch)

    def clock(self, p, data):
        step = self.clock_of(p, data)[2]
        if step == 1 and abs(data.meta["sampling_hz"] - 1000) > 20:
            return 'samples["time"] = samples.groupby(["participant", "trial"]).cumcount()   # I-DT needs an even clock: time is counted in samples'
        return f'samples["time"] = samples.groupby(["participant", "trial"]).cumcount() * {step}   # I-DT needs an even clock: one sample every {step} ms'

    def calls(self, p, data):
        *_, step, shortest = self.clock_of(p, data)
        return [
            call("pix2deg"),
            call("detect", "idt", dispersion_threshold=p["dispersion"], minimum_duration=shortest * step),
            call("compute_event_properties", [LOCATION], name="fixation"),
        ]

    def keep(self, data, gaze, p):
        alone = self.used(p, data)[2]
        given = data.samples[~alone].reset_index(drop=True)
        fixations = events_table(gaze, "fixation", given, "fixation")
        if alone.any() and len(fixations):  # times count from the first sample of the trial, also when I-DT was not given it
            late = (given.groupby(KEYS, sort=False)["time"].min() - data.samples.groupby(KEYS, sort=False)["time"].min()).rename("late")
            late = fixations[KEYS].merge(late.reset_index(), on=KEYS, how="left")["late"].fillna(0).to_numpy()
            fixations["start"] += late
            fixations["end"] += late
        period, shortest = 1000 / data.meta["sampling_hz"], self.clock_of(p, data)[3]
        note = (f"I-DT: samples spread over less than {p['dispersion']:g}° for at least {shortest} samples "
                f"({shortest * period:.0f} ms at this tracker's {period:.3g} ms per sample) are a fixation.") + found(fixations, "fixations")
        if alone.any():
            n = int(alone.sum())
            note += f" {num(n)} sample{'s' if n > 1 else ''} stood alone between two gaps in the timestamps and could not be part of a fixation."
        return data.update(note, fixations=fixations)


@register
class Saccades(GazeStep):
    kind = "saccades"
    title = "Detect saccades (Engbert & Kliegl)"
    group = "detect"
    icon = "zap"
    summary = "Find the fast jumps of the eye with a threshold that adapts to each trial's noise."
    explain = """
        A fixed speed threshold is too strict for a clean recording and too lenient for a noisy one. Engbert
        and Kliegl's method measures how much the speed scatters within each trial, horizontally and
        vertically, and sets the threshold to a multiple of that scatter. Samples faster than the threshold
        are saccade candidates; runs that last long enough become saccades.

        It was designed for the tiny *microsaccades* that happen during fixation, on fast trackers, but
        it is used for ordinary saccades too. For each saccade pymovements then works out the **amplitude**
        (how far the eye travelled, in degrees) and the **peak velocity**. In healthy eyes the two are tightly
        linked: larger saccades are faster. This relation is called the *main sequence*.

        Slow trackers (50–60 samples per second) catch only a sample or two of each saccade, so durations
        and peak velocities from them are rough.
    """
    question = "Sort the saccades by amplitude. Does peak velocity rise with it? What would a saccade far off that line suggest?"
    makes = ("samples", "saccades")
    view = "signal"
    params = (
        Number("factor", "Threshold: multiples of the speed scatter", 6, min=1, max=50, step=0.5,
               help="6 is the usual value. Lower finds more and smaller saccades, and more noise."),
        Number("min_duration_ms", "Shortest saccade", 10, unit="ms", min=1, max=200, step=2, integer=True),
        *VELOCITY,
    )

    def calls(self, p, data):
        return [
            call("pix2deg"),
            velocity_call(p),
            call("detect", "microsaccades", threshold_factor=p["factor"], minimum_duration=p["min_duration_ms"]),
            call("compute_event_properties", ["amplitude", "peak_velocity"], name="saccade"),
        ]

    def keep(self, data, gaze, p):
        saccades = events_table(gaze, "saccade", data.samples, "saccade")
        size = f", median amplitude {saccades['amplitude_deg'].median():.1f}°" if len(saccades) else ""
        note = f"Engbert & Kliegl: samples faster than {p['factor']:g} times the speed scatter of their trial are saccade." + found(saccades, "saccades", size)
        return data.update(note, meta=dict(velocity_unit="°/s", velocity_threshold=None),
                           samples=data.samples.assign(velocity=speed(gaze)), saccades=saccades)


@register
class FixationsFromFile(Node):
    kind = "fixations_file"
    title = "Use the tracker's own fixations"
    group = "detect"
    icon = "file-check"
    summary = "Take fixations that the manufacturer's software already marked in the file."
    explain = """
        Tobii Pro Lab, EyeLink Data Viewer and others run their own detector and can export its verdict for
        every sample, for example the column *Eye movement type* with the values Fixation, Saccade and
        Unclassified. This step rebuilds the fixations from that column instead of detecting them again.

        Use it to compare the manufacturer's result with your own detector on a parallel branch. The
        manufacturer's settings (often an “attention” filter at 100 °/s for glasses) are part of that result,
        and they are stored in the recording software, not in the file.
    """
    question = "Where the manufacturer's fixations and your own disagree, look at the signal. Whose decision would you defend?"
    makes = ("fixations",)
    view = "signal"
    package = "pymovements"
    params = (
        Columns("column", "Column with the eye movement type", multiple=False, pattern="eye movement type*",
                help="Keep this column in the Load step under “Extra columns”."),
        Text("value", "Value that means fixation", "Fixation"),
        Number("min_duration_ms", "Shortest fixation", 60, unit="ms", min=0, max=2000, step=10, integer=True),
    )

    def run(self, data, p, ctx):
        s = data.samples
        column = self.param("column").resolve(p["column"], s)
        if not column:
            raise PipelineError("No column with eye movement types was found. In the Load step, keep “Eye movement type” as an extra column.")
        is_fixation = s[column].astype("str").str.casefold().eq(p["value"].strip().casefold()).fillna(False).to_numpy()
        if not is_fixation.any():
            seen = ", ".join(map(str, s[column].dropna().unique()[:6]))
            raise PipelineError(f"No sample in “{column}” has the value “{p['value']}”. It contains: {seen}.")
        index = next((c for c in s.columns if c.casefold().startswith("eye movement type index")), None)
        number = s[index].to_numpy() if index else None

        # The marked stretches become pymovements events, so that their position and spread are worked out the same way as for a detector.
        gaze = to_gaze(data)
        time, rows = gaze.samples["time"].to_numpy(), []
        for (participant, trial), at in trials(s).items():
            for a, b in runs(is_fixation[at]):
                # consecutive fixations are told apart by their running number
                cuts = [] if number is None else a + 1 + np.flatnonzero(number[at[a:b]][1:] != number[at[a:b]][:-1])
                for first, last in zip([a, *cuts], [*cuts, b]):
                    if time[at[last - 1]] - time[at[first]] >= p["min_duration_ms"]:
                        rows.append((participant, trial, "fixation", time[at[first]], time[at[last - 1]]))
        events = pl.DataFrame(rows, schema=[*KEYS, "name", "onset", "offset"], orient="row").with_columns(duration=pl.col("offset") - pl.col("onset"))
        gaze.events = pm.Events(events, trial_columns=KEYS)
        if count(gaze, "fixation"):
            gaze.pix2deg()
            gaze.compute_event_properties(FIXATION_PROPERTIES, name="fixation")
        fixations = events_table(gaze, "fixation", s, "fixation")
        return data.update(f"Fixations as marked in the file (column “{column}”)." + found(fixations, "fixations"), fixations=fixations)
