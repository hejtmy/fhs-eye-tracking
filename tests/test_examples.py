"""The shipped examples must run, and the effects built into the simulated data must be recoverable."""
import json
import subprocess
import sys

import pandas as pd
import pytest

from gazelab import NODES

from conftest import EXAMPLES, ROOT

PIPELINES = sorted((EXAMPLES / "pipelines").glob("*.json"))


@pytest.fixture(scope="module")
def ran():
    from gazelab import Context, Library, Runner
    runner = Runner(Context(Library(examples=EXAMPLES / "datasets")))
    return {path.stem: runner.run(json.loads(path.read_text())["graph"]) for path in PIPELINES}


@pytest.mark.parametrize("name", [p.stem for p in PIPELINES])
def test_example_pipeline_runs_and_has_a_guide(ran, name):
    spec = json.loads((EXAMPLES / "pipelines" / f"{name}.json").read_text())
    assert spec["name"] and spec["description"] and len(spec["tasks"]) >= 3
    assert all(result.ok for result in ran[name].values()), {NODES[r.kind].title: r.error for r in ran[name].values() if not r.ok}


def test_examples_are_reproducible_from_the_generator(tmp_path):
    before = {p: p.read_bytes() for p in (EXAMPLES / "datasets").rglob("*") if p.suffix in (".csv", ".tsv", ".json")}
    subprocess.run([sys.executable, str(EXAMPLES / "generate.py")], check=True, capture_output=True, cwd=ROOT)
    assert all(path.read_bytes() == content for path, content in before.items())


def test_detected_fixations_match_the_simulated_truth(ran):
    truth = pd.read_csv(EXAMPLES / "datasets" / "visual-search" / "truth" / "fixations.csv")
    for step in ("s4", "b11"):   # I-VT and I-DT
        found = ran["01-samples-to-fixations"][step].bundle["fixations"]
        assert 0.75 * len(truth) < len(found) < 1.05 * len(truth)
        assert abs(found["duration"].median() - truth["duration"].median()) < 40


def test_hard_searches_take_longer_to_reach_the_target(ran):
    table = ran["02-search-difficulty"]["s7"].bundle["summary"]
    target = table[table.aoi == "Target"].pivot(index="participant", columns="condition", values="first_fixation_ms")
    assert len(target) == 8 and (target["hard"] > target["easy"]).all()


def test_the_pupil_dilates_more_in_hard_trials(ran):
    table = ran["03-pupil-and-effort"]["s6"].bundle["summary"]
    assert (table["pupil_mean_hard"] > table["pupil_mean_easy"]).sum() >= 7


def test_the_cheapest_product_draws_most_attention_when_searching_for_it(ran):
    table = ran["04-glasses-shelf"]["s7"].bundle["summary"]
    cheapest = table[table.condition == "cheapest"].set_index("aoi")["dwell_ms"]
    assert cheapest.idxmax() == "Porridge"
    patterns = ran["04-glasses-shelf"]["b12"].bundle["summary"]
    assert patterns["count"].sum() > 50 and patterns["pattern"].str.count("→").eq(2).all()
    assert ran["04-glasses-shelf"]["s2"].bundle["trials"]["trial"].nunique() == 3


def test_raw_glasses_recording_yields_fixations_per_task(ran):
    summary = ran["05-glasses-raw"]["s6"].bundle["trial_summary"]
    assert summary["trial"].tolist() == ["freeview", "cheapest"] and (summary["fixation_count"] > 8).all()
    assert summary["fixation_mean_ms"].between(150, 500).all()


def test_tobii_fixations_from_the_file_agree_with_our_own(ran):
    from gazelab import Context, Library, Runner
    graph = json.loads((EXAMPLES / "pipelines" / "04-glasses-shelf.json").read_text())["graph"]
    graph["nodes"].append(dict(id="tobii", kind="fixations_file", params={}))
    graph["edges"].append(dict(source="s3", target="tobii"))
    theirs = Runner(Context(Library(examples=EXAMPLES / "datasets"))).run(graph, "tobii")["tobii"]
    assert theirs.ok, theirs.error
    ours = ran["04-glasses-shelf"]["s4"].bundle["fixations"]
    assert abs(len(theirs.bundle["fixations"]) - len(ours)) < 0.25 * len(ours)
