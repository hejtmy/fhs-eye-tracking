import gzip
import json

import numpy as np
import pandas as pd
import pytest

from gazelab import PipelineError
from gazelab.datasets import match_stimulus
from gazelab.readers import READERS, detect, read_file, suggest_mapping

from conftest import EXAMPLES, chain, recording, webgazer_workbook

SHELF = EXAMPLES / "datasets" / "glasses-shelf" / "shelf_P01.tsv"
LIVEDATA = EXAMPLES / "datasets" / "glasses-raw" / "livedata.json.gz"


def test_formats_are_recognised_from_their_content():
    assert detect(SHELF).id == "tobii_prolab"
    assert detect(LIVEDATA).id == "tobii_glasses2"
    assert detect(EXAMPLES / "datasets" / "visual-search" / "visual_search.csv").id == "delimited"


def test_column_names_of_common_trackers_are_mapped():
    tobii = suggest_mapping(["Recording timestamp [μs]", "Gaze point X [DACS px]", "Gaze point Y [DACS px]", "Gaze point 3D X", "Pupil diameter left [mm]", "Participant name"])
    assert tobii == dict(time="Recording timestamp [μs]", x="Gaze point X [DACS px]", y="Gaze point Y [DACS px]", pupil="Pupil diameter left [mm]",
                         participant="Participant name", trial="", condition="", stimulus="")
    assert suggest_mapping(["weird_time", "foo"])["time"] == ""


def test_tobii_pro_lab_export_separates_sensors_markers_and_decimal_commas():
    reader, raw = read_file(SHELF)
    text = pd.read_csv(SHELF, sep="\t", dtype=str, encoding="utf-8-sig")
    assert len(raw.frame) == (text["Sensor"] == "Eye Tracker").sum() and "Gyro X [°/s]" not in raw.frame.columns
    assert raw.frame["Pupil diameter left [mm]"].dtype.kind == "f" and 2 < raw.frame["Pupil diameter mean"].mean() < 6
    assert raw.events["label"].tolist() == ["RecordingStart", "freeview_start", "freeview_end", "cheapest_start", "cheapest_end", "choice_start", "choice_end", "RecordingEnd"]
    suggestion = reader.suggest(raw)
    assert suggestion["mapping"]["x"] == "Gaze point X [MCS px]" and suggestion["mapping"]["pupil"] == "Pupil diameter mean"
    assert suggestion["params"] == dict(time_unit="ms", gaze_unit="px", geometry="camera", fov_deg=82, width_px=1920, height_px=1080)
    assert sum(c.startswith("AOI hit") for c in suggestion["extra"]) == 6 and "Eye movement type" in suggestion["extra"]
    left_only = read_file(SHELF, "tobii_prolab", dict(pupil="left"))[1].frame
    assert left_only["Pupil diameter mean"].equals(left_only["Pupil diameter left [mm]"])


def test_czech_pro_lab_export_with_dotted_dates_is_read_with_decimal_commas(tmp_path):
    """Dates (26.11.2026) and times (11:29:59.691) sit on every row; they must not outvote the decimal commas."""
    header = "Recording timestamp [ms]\tSensor\tRecording date\tRecording start time\tEvent\tGaze point X [MCS px]\tGaze point Y [MCS px]\tPupil diameter left [mm]\tPupil diameter right [mm]\tGyro X [°/s]\n"
    rows = ["0\t\t20.11.2026\t11:29:59.691\tRecordingStart\t\t\t\t\t\n"]
    for t in range(0, 400, 10):
        rows.append(f"{t}\tEye Tracker\t20.11.2026\t11:29:59.691\t\t1020\t290\t3,904\t3,839\t\n")
        rows += [f"{t + 3}\tGyroscope\t20.11.2026\t11:29:59.691\t\t\t\t\t\t-1,3300\n"] * 3
    path = tmp_path / "export.tsv"
    path.write_text(header + "".join(rows), encoding="utf-8")
    raw = read_file(path, "tobii_prolab")[1]
    assert raw.frame["Pupil diameter mean"].iloc[0] == pytest.approx(3.8715)


def test_markers_follow_the_participant_name_used_for_the_samples(workspace):
    """The file is labelled P1 here, but the export names its participant P01: markers must end up with the samples."""
    runner, load = workspace(SHELF.read_bytes(), name="anything.tsv")
    data = runner.run(chain(load, ("trials_from_events", {})))["n1"]
    assert data.ok, data.error
    assert data.bundle["events"]["participant"].unique().tolist() == ["P01"] == data.bundle.samples["participant"].unique().tolist()
    assert data.bundle["trials"]["trial"].tolist() == ["freeview", "cheapest", "choice"]
    load[1]["source"]["mapping"] = dict(time="Recording timestamp [ms]", x="Gaze point X [MCS px]", y="Gaze point Y [MCS px]")
    unnamed = runner.run(chain(load, ("trials_from_events", {})))["n1"]
    assert unnamed.ok and unnamed.bundle["events"]["participant"].unique().tolist() == ["P1"]   # no participant column mapped: the file's label


def test_glasses_2_livedata_is_assembled_from_packets(tmp_path):
    packets = [dict(ts=1000, s=0, gidx=1, gp=[0.5, 0.25]), dict(ts=1000, s=0, gidx=1, pd=3.0, eye="left"), dict(ts=1000, s=0, gidx=1, pd=4.0, eye="right"),
               dict(ts=1500, s=0, gy=[1, 2, 3]), dict(ts=11000, s=1, gidx=2, gp=[0, 0]), dict(ts=11000, s=1, gidx=2, pd=0, eye="left"),
               dict(ts=15000, s=0, type="JsonEvent", tag="go"), dict(ts=21000, s=0, gidx=3, gp=[1.0, 1.0]), dict(ts=21000, s=0, gidx=3, pd=3.2, eye="left")]
    path = tmp_path / "livedata.json.gz"
    with gzip.open(path, "wt") as handle:
        handle.write("\n".join(map(json.dumps, packets)) + "\nnot json\n")
    _, raw = read_file(path)
    frame = raw.frame
    assert frame["time_ms"].tolist() == [0, 10, 20] and frame["gaze_x"].tolist()[::2] == [960, 1920] and np.isnan(frame["gaze_x"][1])
    assert frame["pupil_mean"].tolist()[::2] == [3.5, 3.2] and np.isnan(frame["pupil_mean"][1])
    assert raw.events[["time", "label"]].to_numpy().tolist() == [[14, "go"]]
    assert any("1 unreadable" in note for note in raw.notes)
    whole = read_file(LIVEDATA)[1]
    assert len(whole.frame) > 2000 and whole.hints["fov_deg"] == 82 and list(whole.events["label"])[:2] == ["freeview_start", "freeview_end"]


def asc(binocular=False):
    lines = ["** CONVERTED FROM test.edf", "MSG 0 DISPLAY_COORDS 0 0 1279 1023", "MSG 0 GAZE_COORDS 0.00 0.00 1279.00 1023.00",
             f"SAMPLES GAZE {'LEFT RIGHT' if binocular else 'LEFT'} RATE 100"]
    for trial, start in (("A", 100), ("B", 1000), ("A", 2000)):
        lines += [f"MSG {start} TRIALID {trial}", f"START {start} {'LEFT RIGHT' if binocular else 'LEFT'} SAMPLES EVENTS"]
        for i in range(10):
            lines.append(f"{start + i * 10}\t  100.0\t  200.0\t 3000.0" + ("\t  500.0\t  600.0\t 4000.0" if binocular else "") + "\t...")
        lines += [f"{start + 100}\t   .\t   .\t    0.0" + ("\t   .\t   .\t    0.0" if binocular else "") + "\t...", f"MSG {start + 110} TRIAL_RESULT 0",
                  f"{start + 110}\t  101.0\t  201.0\t 3001.0" + ("\t  501.0\t  601.0\t 4001.0" if binocular else "") + "\t...", f"END {start + 110} SAMPLES EVENTS"]
    return "\n".join(lines) + "\n"


def test_eyelink_asc_trials_screen_and_missing_values(workspace):
    runner, load = workspace(asc(), name="rec.asc")
    data = runner.run(chain(load))["n0"].bundle
    assert data.samples.groupby("trial", sort=False).size().to_dict() == {"A": 11, "B": 11, "A#2": 11}   # samples after TRIAL_RESULT are outside
    assert data.samples.pupil.isna().sum() == 3 and data.samples.x.isna().sum() == 3
    assert "3 samples that belong to no trial" in " ".join(data.notes)
    assert read_file(runner.ctx.dataset("d1").path("rec.asc"))[1].hints == dict(time_unit="ms", gaze_unit="px", geometry="screen", width_px=1280, height_px=1024)
    assert "TRIALID A" in data["events"]["label"].tolist()


def test_eyelink_binocular_recordings_let_you_choose_the_eye(workspace):
    runner, load = workspace(asc(binocular=True), name="rec.asc")
    assert runner.run(chain(load))["n0"].bundle.samples.x.dropna().iloc[0] == 100
    load[1]["source"]["options"] = dict(eye="right")
    assert runner.run(chain(load))["n0"].bundle.samples.x.dropna().iloc[0] == 500


def test_semicolons_decimal_commas_and_missing_codes_are_handled(workspace):
    text = "# exported by SomeTracker\nTime;GazeX;GazeY;Pupil\n" + "".join(f"{t};{100 + t / 10:.1f};-1;3,5\n".replace(".", ",") for t in range(0, 500, 10))
    runner, load = workspace(text, name="rec.txt")
    load[1]["source"].update(options=dict(missing="-1"), mapping=dict(time="Time", x="GazeX", y="GazeY", pupil="Pupil"))
    samples = runner.run(chain(load))["n0"].bundle.samples
    assert samples.x.iloc[1] == 101 and samples.y.isna().all() and samples.pupil.iloc[0] == 3.5


def test_units_are_detected_and_converted(workspace):
    frame = recording()
    frame["time"], frame["x"], frame["y"] = frame.time / 1000, frame.x / 1000, frame.y / 800
    runner, load = workspace(frame)
    data = runner.run(chain(load))["n0"].bundle
    assert data.samples.time.iloc[-1] == pytest.approx(1990) and data.samples.x.iloc[0] == pytest.approx(100, abs=3)
    assert data.meta["sampling_hz"] == pytest.approx(100) and "seconds" in data.notes[0] and "screen fractions" in data.notes[0]
    micro = recording().assign(time=lambda f: f.time * 1000)
    runner, load = workspace(micro)
    assert runner.run(chain(load))["n0"].bundle.samples.time.iloc[-1] == pytest.approx(1990)


def test_loading_problems_are_explained(workspace):
    runner, load = workspace(pd.concat([recording(), recording()]))
    assert "Time jumps backwards" in runner.run(chain(load))["n0"].error
    runner, load = workspace(recording().rename(columns=dict(x="horizontal")))
    assert "Choose which column holds Gaze X" in runner.run(chain(load))["n0"].error
    runner, load = workspace(recording().assign(x="left"))
    assert "mostly text" in runner.run(chain(load))["n0"].error
    load[1]["source"]["dataset"] = "gone"
    assert "no longer on the server" in runner.run(chain(load))["n0"].error
    assert "Choose a dataset" in runner.run(chain(("load", {})))["n0"].error


def test_webgazer_workbook_gives_phases_markers_and_calibration(workspace, tmp_path):
    path = webgazer_workbook(tmp_path / "webgazer_vlastni_stimuly.xlsx")
    assert detect(path).id == "webgazer"
    reader, raw = read_file(path)
    suggestion = reader.suggest(raw)
    assert suggestion["mapping"] == dict(time="cas_ms", x="x_1920", y="y_1080", pupil="", participant="", trial="faze", condition="", stimulus="stimul")
    assert suggestion["params"] == dict(time_unit="ms", gaze_unit="px", width_px=1920, height_px=1080, geometry="screen", stimulus_fit="contain")
    assert raw.events["label"].tolist() == ["cross1", "s1", "cross2", "s2"] and raw.events["time"].tolist() == [0, 300, 1300, 1600]   # where each phase began
    assert any("2 attempt(s); the one used was off by 88 px" in note for note in raw.notes)   # the calibration marked “ano”, not the last row read

    runner, load = workspace(path.read_bytes(), name="webgazer.xlsx", stimulus_fit="contain")
    data = runner.run(chain(load))["n0"].bundle
    assert data.samples.groupby("trial", sort=False)["stimulus"].first().to_dict() == {
        "cross1": "fixační kříž", "s1": "Přednáška – Lukavský (12x6 in, na šířku).png", "cross2": "fixační kříž", "s2": "3333.jpg"}
    assert data.meta["stimulus_fit"] == "contain" and len(data["events"]) == 4

    other = tmp_path / "other.xlsx"
    pd.DataFrame(dict(time=[1, 2])).to_excel(other, index=False)
    with pytest.raises(PipelineError, match="not one saved by the WebGazer experiment"):
        read_file(other)


def test_stimulus_labels_find_their_uploaded_images():
    images = {"3333": "", "Přednáška _ Lukavský 15.12.2026 (12x6 in_ na šířku)": "", "easy_1": ""}   # names as uploads store them
    assert match_stimulus(images, "3333.jpg") == "3333"
    assert match_stimulus(images, "Přednáška – Lukavský 15.12.2026 (12x6 in, na šířku).png") == "Přednáška _ Lukavský 15.12.2026 (12x6 in_ na šířku)"
    assert match_stimulus(images, "EASY_1") == "easy_1" and match_stimulus(images, "fixační kříž") is None
    assert match_stimulus({"scene": ""}, "anything") == "scene"   # a single image serves every trial


def test_every_reader_describes_itself():
    for reader in READERS.values():
        described = reader.describe()
        assert described["title"] and described["about"] and reader.clean({}) == {p.key: p.default for p in reader.options}
