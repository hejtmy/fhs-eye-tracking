"""WebGazer experiments exported as an Excel workbook (`webgazer_*.xlsx`).

The workbook has four sheets: *Legenda* (what the columns mean), *AOI* (dwell
per image, computed by the experiment page), *Vzorky* (the samples) and
*Kalibrace* (calibration clicks and the accuracy check). Only *Vzorky* holds
samples: `cas_ms` from the start of the experiment, `faze` (crossN = fixation
cross before image N, sN = image N), `stimul` (image file name, or
“fixační kříž”), `cas_ve_fazi_ms` and gaze `x_1920`, `y_1080` already scaled
to a 1920 × 1080 screen. Images were shown fitted inside that screen, centred,
on a grey background.
"""
import zipfile

import pandas as pd

from ..core import num
from . import Raw, Reader, reader

SAMPLES = "Vzorky"
SCREEN = (1920, 1080)
COLUMNS = dict(time="cas_ms", x="x_1920", y="y_1080", trial="faze", stimulus="stimul")


def sheets(path):
    """Sheet names of a workbook, read cheaply from its index; empty when the file is not one."""
    try:
        with zipfile.ZipFile(path) as archive:
            return archive.read("xl/workbook.xml").decode("utf-8", "replace")
    except (zipfile.BadZipFile, KeyError, OSError):
        return ""


def calibration_notes(path):
    """The accuracy check of the calibration that was used, in one sentence."""
    try:
        table = pd.read_excel(path, sheet_name="Kalibrace", header=None)
    except (ValueError, KeyError):
        return []
    header = table.index[table[0].astype(str).eq("pokus") & table[1].astype(str).eq("zacatek")]
    if not len(header):
        return []
    attempts = table.iloc[header[0] + 1:]
    attempts = attempts[pd.to_numeric(attempts[0], errors="coerce").notna()]
    attempts = attempts[attempts[1].astype(str).str.contains(":")]   # the summary block ends at the first blank row
    if attempts.empty:
        return []
    used = attempts[attempts[7].astype(str).str.casefold().eq("ano")]
    last = (used if len(used) else attempts).iloc[-1]
    return [f"Calibration: {len(attempts)} attempt(s); the one used was off by {last[5]} px on average in a "
            f"{last[2]} × {last[3]} px browser window ({last[6]} % accuracy as WebGazer reports it)."]


@reader
class WebGazer(Reader):
    id = "webgazer"
    title = "WebGazer experiment (Excel workbook)"
    about = ("Upload the .xlsx the experiment page saves, one per participant, and the images that were shown. "
             "Samples come from the sheet “Vzorky”; images are placed as they were shown, fitted inside the screen.")
    extensions = (".xlsx",)

    def sniff(self, path, head):
        names = sheets(path)
        return 0.95 if f'name="{SAMPLES}"' in names else 0.0

    def read(self, path, o):
        if f'name="{SAMPLES}"' not in sheets(path):
            raise ValueError(f"the workbook has no sheet “{SAMPLES}”. Is it the file a WebGazer experiment saved?")
        frame = pd.read_excel(path, sheet_name=SAMPLES)
        frame.columns = [str(c).strip() for c in frame.columns]
        missing = [c for c in COLUMNS.values() if c not in frame.columns]
        if missing:
            raise ValueError(f"the sheet “{SAMPLES}” lacks the column(s) {', '.join(missing)}.")
        frame = frame.dropna(subset=["cas_ms"]).reset_index(drop=True)

        # One marker where each phase began: time of a sample minus its time within the phase.
        onsets = frame.assign(start=frame["cas_ms"] - frame["cas_ve_fazi_ms"]).groupby("faze", sort=False).agg(
            time=("start", "min"), value=("stimul", "first")).reset_index()
        events = pd.DataFrame(dict(time=onsets["time"].to_numpy(), label=onsets["faze"].astype(str).to_numpy(), value=onsets["value"].to_numpy()))

        shown = frame.loc[~frame["faze"].astype(str).str.startswith("cross"), "stimul"].dropna().unique()
        notes = [f"WebGazer workbook: {num(len(frame))} gaze estimates in {frame['faze'].nunique()} phases "
                 f"({len(shown)} image(s) and the fixation crosses before them).",
                 "Gaze is already in pixels of a 1920 × 1080 screen. Webcam estimates are off by hundreds of pixels, "
                 "more so vertically, and arrive only about 30 times per second.",
                 *calibration_notes(path)]
        if len(shown):
            notes.append("Upload the images under exactly these names to see them behind the gaze: " + ", ".join(f"“{s}”" for s in shown) + ".")
        hints = dict(time_unit="ms", gaze_unit="px", width_px=SCREEN[0], height_px=SCREEN[1], geometry="screen", stimulus_fit="contain")
        return Raw(frame, events, notes, hints)

    def suggest(self, raw):
        mapping = {**dict.fromkeys(("time", "x", "y", "pupil", "participant", "trial", "condition", "stimulus"), ""), **COLUMNS}
        return dict(mapping=mapping, extra=[], params=dict(raw.hints))
