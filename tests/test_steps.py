"""Each step against a recording whose true events are known exactly."""
import numpy as np
import pandas as pd
import pytest

from gazelab import NODES
from gazelab.bridge import GazeStep

from conftest import chain, recording

IVT = ("fixations_ivt", dict(threshold=30))
AREAS = [dict(name="Left", shape="rect", x=50, y=50, w=100, h=100), dict(name="Right", shape="ellipse", x=540, y=40, w=120, h=120),
         dict(name="Never", shape="rect", x=900, y=700, w=50, h=50)]


def run(workspace, *steps, frame=None, **load):
    runner, first = workspace(recording() if frame is None else frame, **load)
    results = runner.run(chain(first, *steps))
    failed = [r.error for r in results.values() if not r.ok]
    assert not failed, failed
    return results[f"n{len(steps)}"].bundle


def repeated(sequence):
    """One trial per participant in which gaze visits the given places for 300 ms each."""
    places = dict(A=(100, 100), B=(600, 100), C=(600, 500), o=(300, 700))
    rows = []
    for participant, order in sequence.items():
        for i, place in enumerate(order):
            for t in range(0, 300, 10):
                rows.append((participant, i * 300 + t, *places[place]))
    return pd.DataFrame(rows, columns=["participant", "time", "x", "y"])


@pytest.mark.parametrize("detector", [IVT, ("fixations_idt", dict(dispersion=1.0, min_duration_ms=100))])
def test_both_detectors_recover_the_three_true_fixations(workspace, detector):
    fixations = run(workspace, detector)["fixations"]
    assert len(fixations) == 3
    assert np.allclose(fixations[["x", "y"]].to_numpy(), [[100, 100], [600, 100], [600, 500]], atol=5)
    assert np.allclose(fixations["duration"], [490, 490, 750], atol=45)   # from the first to the last sample of each fixation
    assert fixations["fixation"].tolist() == [1, 2, 3]
    assert "dispersion_deg" not in fixations or (fixations["dispersion_deg"] < 0.5).all()   # reported by I-VT only


def test_saccades_come_with_amplitude_and_peak_velocity(workspace):
    data = run(workspace, IVT, ("saccades", {}), geometry="camera", fov_deg=50)
    assert data.meta["px_per_deg"] == pytest.approx(20) and data.meta["velocity_unit"] == "°/s"
    saccades = data["saccades"]
    assert len(data["fixations"]) == 3 and saccades["saccade"].tolist() == list(range(1, len(saccades) + 1))   # the fixations stay
    assert saccades["amplitude_deg"].iloc[0] == pytest.approx(25.8, abs=1.5) and saccades["peak_velocity"].iloc[0] > 300
    assert saccades["start"].iloc[0] == pytest.approx(500, abs=20)
    assert not ((saccades["start"] < 1210) & (saccades["end"] > 1020)).any()   # the blink is not a saccade


def test_a_noise_spike_splits_a_fixation_and_short_fixations_are_dropped(workspace):
    frame = recording(noise=0)
    frame.loc[frame.time == 250, ["x", "y"]] = [130, 100]   # a one-sample spike inside the first fixation
    assert len(run(workspace, ("fixations_ivt", dict(velocity="neighbors")), frame=frame)["fixations"]) == 4   # pymovements' I-VT does not merge
    assert len(run(workspace, IVT, frame=frame)["fixations"]) == 3   # measuring speed over more samples rides out the spike
    assert len(run(workspace, ("fixations_ivt", dict(threshold=30, min_duration_ms=600)))["fixations"]) == 1


@pytest.mark.parametrize("rate, counted", [(100, "10 samples"), (120, "12 samples"), (60, "6 samples")])
def test_idt_works_at_any_sampling_rate_and_across_missing_rows(workspace, rate, counted):
    frame = recording(rate=rate).round(1)
    frame = frame.drop(index=frame.index[(frame.time > 200) & (frame.time < 240)])   # the tracker dropped a few rows
    data = run(workspace, ("fixations_idt", dict(dispersion=1.0, min_duration_ms=100)), frame=frame)
    assert counted in data.notes[-1]
    fixations = data["fixations"]
    assert len(fixations) == 4 and fixations["end"].iloc[0] < 205 < 235 < fixations["start"].iloc[1]   # split where rows are missing
    assert np.allclose(fixations[["x", "y"]].to_numpy(), [[100, 100], [100, 100], [600, 100], [600, 500]], atol=12)   # pymovements' I-DT takes in the first saccade sample


def test_blinks_are_found_and_their_edges_removed(workspace):
    data = run(workspace, ("blinks", dict(margin_ms=30)))
    blink = data["blinks"].iloc[0]
    assert len(data["blinks"]) == 1 and (blink.start, blink.end, blink.duration) == (1020, 1210, 190)   # first to last lost sample
    removed = data.samples[data.samples.masked]
    assert removed.time.min() == 990 and removed.time.max() == 1240 and removed[["x", "y", "pupil"]].isna().all().all()
    assert len(run(workspace, ("blinks", dict(max_ms=150)))["blinks"]) == 0   # too long to be a blink: left alone
    runner, load = workspace(recording().drop(columns="pupil"))
    assert "pupil signal" in runner.run(chain(load, ("blinks", {})))["n1"].error


def test_only_short_inner_gaps_are_filled(workspace):
    frame = recording(noise=0)
    frame.loc[frame.time.isin([300, 310]), ["x", "y", "pupil"]] = np.nan
    frame.loc[frame.time < 20, "pupil"] = np.nan
    data = run(workspace, ("interpolate", dict(max_gap_ms=75)), frame=frame)
    s = data.samples
    assert s.loc[s.time.isin([300, 310]), "x"].tolist() == [100, 100] and s.loc[s.time.isin([300, 310]), "filled"].all()
    assert s.loc[s.time < 20, "pupil"].isna().all()                       # a gap at the edge has only one neighbour
    assert s.loc[(s.time >= 1020) & (s.time < 1220), "x"].isna().all()    # the blink is longer than the limit
    only_pupil = run(workspace, ("interpolate", dict(max_gap_ms=400, channels="pupil")), frame=frame).samples
    assert only_pupil.loc[only_pupil.time == 1100, "pupil"].notna().all() and only_pupil.loc[only_pupil.time == 1100, "x"].isna().all()


@pytest.mark.parametrize("method", ["moving_average", "savitzky_golay"])
def test_smoothing_reduces_noise_within_trials(workspace, method):
    frame = recording(noise=4)
    before = run(workspace, frame=frame).samples
    after = run(workspace, ("smooth", dict(method=method, window=7)), frame=frame).samples
    steady = (before.time > 50) & (before.time < 450)
    assert after.x[steady].std() < 0.8 * before.x[steady].std()
    grown = after.x.isna() & before.x.notna()   # a window that touches the blink has no result
    assert grown.sum() <= 6 and after.masked[grown].all() and after.pupil.equals(before.pupil)
    assert abs(after.x[(after.time > 1220) & after.x.notna()].iloc[0] - 600) < 10   # nothing was dragged across the blink


def test_baseline_correction_and_its_exclusion_rule(workspace):
    data = run(workspace, ("baseline", dict(start_ms=0, end_ms=200)))
    assert data.samples.pupil[data.samples.time < 200].mean() == pytest.approx(0, abs=1e-9)
    assert data.meta["pupil_unit"] == "change from baseline"
    frame = recording()
    frame.loc[frame.time < 150, "pupil"] = np.nan
    assert run(workspace, ("baseline", dict(start_ms=0, end_ms=200)), frame=frame).samples.pupil.isna().all()
    runner, load = workspace(recording())
    twice = runner.run(chain(load, ("baseline", {}), ("baseline", {})))
    assert "already baseline-corrected" in twice["n2"].error


def test_offscreen_gaze_becomes_missing(workspace):
    frame = recording(noise=0)
    frame.loc[frame.time == 100, "x"] = 5000
    s = run(workspace, ("offscreen", dict(margin_px=10)), frame=frame).samples
    assert s.x.isna().sum() == frame.x.isna().sum() + 1 and bool(s.masked[s.time == 100].iloc[0])


def test_cropping_keeps_a_window_of_each_trial(workspace):
    s = run(workspace, ("crop", dict(start_ms=200, end_ms=700))).samples
    assert (s.time.min(), s.time.max()) == (200, 690)


def test_aoi_measures_include_areas_that_were_never_looked_at(workspace):
    data = run(workspace, IVT, ("aoi_draw", dict(aois=AREAS)), ("aoi_metrics", {}))
    assert data["fixations"]["aoi"].tolist() == ["Left", "Right", ""]
    metrics = data["aoi_metrics"].set_index("aoi")
    assert metrics.loc["Never", ["fixation_count", "dwell_ms", "visits"]].tolist() == [0, 0, 0] and np.isnan(metrics.loc["Never", "first_fixation_ms"])
    assert metrics.loc["Right", "first_fixation_ms"] == pytest.approx(520, abs=25)
    assert metrics.loc["Left", "dwell_pct"] == pytest.approx(100 * 500 / 1760, abs=2)


def test_areas_can_belong_to_one_stimulus(workspace):
    frame = pd.concat([recording().assign(trial=1, stimulus="a"), recording().assign(trial=2, stimulus="b")])
    areas = [dict(AREAS[0], stimulus="a"), AREAS[1]]
    data = run(workspace, IVT, ("aoi_draw", dict(aois=areas)), ("aoi_metrics", {}), frame=frame)
    assert data["fixations"].query("trial == '2'")["aoi"].tolist() == ["", "Right", ""]
    assert len(data["aoi_metrics"]) == 3   # Left applies to trial 1 only; Right to both


def test_visits_transitions_and_patterns_follow_the_viewing_order(workspace):
    frame = repeated(dict(P1="AABAoC", P2="CBA"))
    areas = [dict(name=n, shape="rect", x=x - 40, y=y - 40, w=80, h=80) for n, (x, y) in dict(A=(100, 100), B=(600, 100), C=(600, 500)).items()]
    steps = [("fixations_idt", dict(dispersion=1.0)), ("aoi_draw", dict(aois=areas))]
    metrics = run(workspace, *steps, ("aoi_metrics", {}), frame=frame)["aoi_metrics"].set_index(["participant", "aoi"])
    assert metrics.loc[("P1", "A"), "visits"] == 2 and metrics.loc[("P1", "A"), "dwell_ms"] == pytest.approx(900, abs=25)

    moves = run(workspace, *steps, ("aoi_transitions", {}), frame=frame)["transitions"].set_index(["participant", "source", "target"])["count"]
    assert moves[("P1", "A", "B")] == 1 and moves[("P1", "B", "A")] == 1 and moves[("P1", "A", "C")] == 1 and moves[("P2", "A", "B")] == 0
    assert len(moves) == 2 * 6   # every ordered pair for every trial, zeros included
    kept = run(workspace, *steps, ("aoi_transitions", dict(keep_outside=True)), frame=frame)["transitions"]
    assert kept.query("participant == 'P1' and source == 'A' and target == 'C'")["count"].iloc[0] == 0

    found = run(workspace, *steps, ("aoi_patterns", dict(length=2)), frame=frame)
    assert found["sequences"].set_index("participant")["sequence"].to_dict() == dict(P1="A → B → A → C", P2="C → B → A")
    assert found["patterns"].query("participant == 'P1'").set_index("pattern")["count"].to_dict() == {"A → B": 1, "B → A": 1, "A → C": 1}


def test_aoi_hits_from_file_columns_label_fixations_by_majority(workspace):
    frame = recording()
    frame["AOI hit [Snap - Left]"] = (frame.x < 300).astype(int)
    frame["AOI hit [Snap - Right]"] = ((frame.x > 300) & (frame.y < 300) & (frame.time < 800)).astype(int)
    runner, load = workspace(frame)
    load[1]["source"].update(mapping=dict(time="time", x="x", y="y", pupil="pupil"), extra=list(frame.columns[-2:]))
    data = runner.run(chain(load, IVT, ("aoi_columns", {})))["n2"].bundle
    assert data["aois"]["name"].tolist() == ["Left", "Right"]
    assert data["fixations"]["aoi"].tolist() == ["Left", "Right", ""]
    strict = runner.run(chain(load, IVT, ("aoi_columns", dict(majority=90))))["n2"].bundle
    assert strict["fixations"]["aoi"].tolist() == ["Left", "", ""]


def test_trials_from_markers(workspace):
    marks = {100: ["search_start"], 500: ["search_end", "rest_start"], 1500: ["rest_end"]}
    lines = ["MSG 0 GAZE_COORDS 0 0 999 799", "START 0 LEFT SAMPLES EVENTS"]
    for t in range(0, 2000, 10):
        lines += [f"MSG {t} {mark}" for mark in marks.get(t, [])] + [f"{t}\t100.0\t100.0\t900.0\t..."]
    asc = "\n".join(lines) + "\n"
    runner, load = workspace(asc, name="r.asc")
    data = runner.run(chain(load, ("trials_from_events", {})))["n1"].bundle
    assert data["trials"][["trial", "start", "end"]].to_numpy().tolist() == [["search", 100, 490], ["rest", 500, 1490]]
    assert data.samples.groupby("trial", sort=False).size().to_dict() == dict(search=40, rest=100)
    assert data.samples.condition.unique().tolist() == ["search", "rest"]
    kept = runner.run(chain(load, ("trials_from_events", dict(outside="keep", end=""))))["n1"].bundle.samples
    assert kept.groupby("trial", sort=False).size().to_dict() == {"(between)": 10, "search": 40, "rest": 150}
    assert "No markers are named like" in runner.run(chain(load, ("trials_from_events", dict(start="go*"))))["n1"].error


def test_trial_information_is_joined_from_a_pasted_table(workspace):
    frame = pd.concat([recording().assign(trial=t) for t in (1, 2, 3)])
    data = run(workspace, ("trial_info", dict(rows="trial; condition\n1; easy\n2; hard\n")), frame=frame)
    assert data.samples.groupby("trial").condition.first().fillna("-").to_dict() == {"1": "easy", "2": "hard", "3": "-"}
    assert "1 trials have no row" in data.notes[-1]


def test_summary_tables_for_statistics(workspace):
    frame = pd.concat([recording(seed=s).assign(participant=p, trial=t, condition=c)
                       for s, (p, t, c) in enumerate([("A", 1, "easy"), ("A", 2, "hard"), ("B", 1, "easy"), ("B", 2, "hard")])])
    steps = [("blinks", {}), IVT, ("aoi_draw", dict(aois=AREAS)), ("aoi_metrics", {})]
    summary = run(workspace, *steps[:2], ("saccades", {}), ("trial_summary", {}), frame=frame)["trial_summary"]
    assert summary[["blink_count", "fixation_count"]].to_numpy().tolist() == [[1, 3]] * 4
    assert (summary.saccade_count >= 1).all() and summary.saccade_amplitude_deg.notna().all()
    assert summary.valid_gaze_pct.between(85, 90).all()

    long = run(workspace, *steps, ("aggregate", {}), frame=frame)["summary"]
    assert list(long.columns[:3]) == ["participant", "condition", "aoi"] and len(long) == 2 * 2 * 3 and (long.n == 1).all()
    wide = run(workspace, *steps, ("aggregate", dict(by=["participant", "condition", "aoi"], layout="wide")), frame=frame)["summary"]
    assert len(wide) == 2 and "dwell_ms_easy_Left" in wide.columns and wide["dwell_ms_hard_Never"].tolist() == [0, 0]
    totals = run(workspace, *steps, ("aggregate", dict(by=["aoi"], stat="sum")), frame=frame)["summary"].set_index("aoi")
    assert totals.loc["Left", "fixation_count"] == 4 and totals.loc["Left", "n"] == 4
    runner, load = workspace(frame)
    assert "wide table has one row per participant" in runner.run(chain(load, *steps, ("aggregate", dict(by=["aoi"], layout="wide"))))["n5"].error


@pytest.mark.parametrize("rate", [100, 120])
@pytest.mark.parametrize("kind", [kind for kind, node in NODES.items() if isinstance(node, GazeStep)])
def test_the_script_shown_for_a_step_reproduces_it_without_gaze_lab(workspace, tmp_path, monkeypatch, kind, rate):
    frame = recording(rate=rate).round(2)
    frame.loc[5, "x"] = 5000   # one sample far off the screen
    runner, load = workspace(frame)
    results = runner.run(chain(load, (kind, {})))
    before, after = results["n0"].bundle, results["n1"].bundle
    before.samples.to_csv(tmp_path / "samples.csv", index=False)   # what “Download CSV” on the Input tab gives
    monkeypatch.chdir(tmp_path)
    scope = {}
    exec(NODES[kind].script(results["n1"].params, before), scope)
    gaze = scope["gaze"]

    x = gaze.samples["pixel"].list.get(0).to_numpy()
    assert np.allclose(x, after.samples.x, equal_nan=True) and np.allclose(gaze.samples["pupil"].to_numpy().astype(float), after.samples.pupil, equal_nan=True)
    made = [name for name in NODES[kind].makes if name != "samples"]
    if kind == "offscreen":
        assert np.isnan(x[5]) and np.isnan(x).sum() == before.samples.x.isna().sum() + 1
    for name in made:
        events = gaze.events.frame.filter(name=name.rstrip("s"))
        assert len(events) == len(after[name]) > 0
        tick = 1 if rate == 100 or kind != "fixations_idt" else 1000 / rate   # I-DT counts in samples when a sample is not a whole ms
        assert (events["duration"] * tick).sum() == pytest.approx(after[name]["duration"].sum(), abs=2 * len(events))
        # the script lets pymovements compute the event properties; the app computes them in one pass and must agree
        if "location" in events.columns:
            assert np.allclose(np.array(events["location"].to_list()), after[name][["x", "y"]].to_numpy())
        for theirs, ours in (("amplitude", "amplitude_deg"), ("peak_velocity", "peak_velocity"), ("dispersion", "dispersion_deg")):
            assert (theirs in events.columns) == (ours in after[name].columns)
            if theirs in events.columns:
                assert np.allclose(events[theirs].to_numpy(), after[name][ours].to_numpy())


@pytest.mark.filterwarnings("ignore:Overlapping events")
def test_the_one_pass_shortcuts_give_what_pymovements_gives(examples):
    from gazelab import bridge
    load = ("load", dict(source=dict(dataset="visual-search"), width_px=1920, height_px=1080, screen_width_cm=53, distance_cm=60))
    data = examples.run(chain(load))["n0"].bundle
    data = data.update(samples=data.samples[data.samples.participant.isin(["P01", "P06"])].reset_index(drop=True))   # many trials, one of them noisy
    theirs, ours = bridge.to_gaze(data), bridge.to_gaze(data)
    for gaze in (theirs, ours):
        gaze.detect("blink", minimum_duration=60, maximum_duration=500)
        gaze.detect("out_of_screen", x_min=200, x_max=1700, y_min=100, y_max=900)   # a small “screen”, so that many events exist
    assert bridge.count(ours, "blink") > 5 and bridge.count(ours, "out_of_screen") > 50
    theirs.nullify_event_samples("blink", padding=(120, 30))
    theirs.nullify_event_samples("out_of_screen", padding=40)   # padded events overlap here
    bridge.nullify_event_samples(ours, "blink", padding=(120, 30))
    bridge.nullify_event_samples(ours, "out_of_screen", padding=40)
    assert ours.samples.equals(theirs.samples) and ours.samples["pixel"].null_count() > 500

    measures = ["amplitude", "peak_velocity", "dispersion", ("location", {"position_column": "pixel"})]
    for gaze in (theirs, ours):
        gaze.pix2deg()
        gaze.pos2vel("fivepoint")
        gaze.detect("ivt", velocity_threshold=30, minimum_duration=60)
    theirs.compute_event_properties(measures, name="fixation")
    bridge.compute_event_properties(ours, measures, name="fixation")
    keys = ["participant", "trial", "name", "onset"]
    a, b = ours.events.frame.sort(keys), theirs.events.frame.select(ours.events.frame.columns).sort(keys)
    assert bridge.count(ours, "fixation") > 50 and a.drop("location").equals(b.drop("location"))
    where = [np.array(frame.filter(name="fixation")["location"].to_list()) for frame in (a, b)]
    assert np.allclose(*where, rtol=0, atol=1e-9) and a["location"].null_count() == b["location"].null_count()   # means differ by rounding only
