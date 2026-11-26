import pytest

from gazelab import NODES, VIEWS, PipelineError, plan
from gazelab.pipeline import changes

from conftest import chain, recording


def test_every_step_explains_itself_and_accepts_its_own_defaults():
    for node in NODES.values():
        description = node.describe()
        assert len(description["explain"]) > 150 and description["question"] and description["code"].lstrip().startswith(("def run", "def calls"))
        assert node.clean({}) == node.clean({p.key: p.default for p in node.params})
        assert not node.view or node.view.startswith("table:") or node.view in VIEWS


@pytest.mark.parametrize("graph, message", [
    (dict(nodes=[dict(id="a", kind="nope")], edges=[]), "Unknown step"),
    (dict(nodes=[dict(id="a", kind="blinks"), dict(id="b", kind="smooth")], edges=[dict(source="a", target="b"), dict(source="b", target="a")]), "loop"),
    (dict(nodes=[dict(id="a", kind="load"), dict(id="b", kind="load"), dict(id="c", kind="blinks")],
          edges=[dict(source="a", target="c"), dict(source="b", target="c")]), "two inputs"),
    (dict(nodes=[dict(id="a", kind="load"), dict(id="b", kind="load")], edges=[dict(source="a", target="b")]), "starts a pipeline"),
    (dict(nodes=[], edges=[]), "between 1 and"),
])
def test_malformed_graphs_are_rejected_with_a_readable_message(graph, message):
    with pytest.raises(PipelineError, match=message):
        plan(graph)


def test_a_failing_step_blocks_only_the_steps_after_it(workspace):
    runner, load = workspace(recording())
    graph = chain(load, ("blinks", {}), ("aoi_metrics", {}), ("aggregate", {}), branches=[(1, [("fixations_ivt", dict(threshold=30))])])
    results = runner.run(graph)
    assert results["n1"].ok and results["b00"].ok
    assert "needs fixations" in results["n2"].error and "Detect fixations" in results["n2"].error
    assert results["n3"].blocked and not results["n3"].ok


def test_a_step_without_data_says_so(workspace):
    runner, _ = workspace(recording())
    assert "Connect it after a Load step" in runner.run(dict(nodes=[dict(id="a", kind="blinks")], edges=[]))["a"].error


def test_changing_a_setting_recomputes_only_that_step_and_those_after_it(workspace):
    runner, load = workspace(recording())
    steps = [load, ("blinks", {}), ("interpolate", dict(max_gap_ms=75)), ("fixations_ivt", dict(threshold=30))]
    assert not any(r.cached for r in runner.run(chain(*steps)).values())
    steps[2] = ("interpolate", dict(max_gap_ms=300))
    again = runner.run(chain(*steps))
    assert [again[i].cached for i in ("n0", "n1", "n2", "n3")] == [True, True, False, False]


def test_running_to_a_target_skips_other_branches(workspace):
    runner, load = workspace(recording())
    graph = chain(load, ("blinks", {}), branches=[(0, [("crop", dict(start_ms=5000))])])
    assert set(runner.run(graph, "n1")) == {"n0", "n1"}
    assert "No samples" in runner.run(graph)["b00"].error


def test_steps_never_modify_the_data_they_receive(workspace):
    runner, load = workspace(recording())
    first = runner.run(chain(load))["n0"].bundle
    before = first.samples.copy(deep=True)
    runner.run(chain(load, ("blinks", {}), ("interpolate", dict(max_gap_ms=400)), ("smooth", dict(window=5)), ("baseline", {}),
                     ("fixations_ivt", dict(threshold=30))))
    assert first.samples.equals(before)


def test_changes_describe_what_a_step_did(workspace):
    runner, load = workspace(recording())
    results = runner.run(chain(load, ("blinks", dict(margin_ms=30))))
    described = {c["table"]: c for c in changes(results["n1"].parent, results["n1"].bundle)}
    assert described["blinks"]["change"] == "new"
    assert described["samples"]["change"] == "changed" and "pupil: 6 removed" in described["samples"]["detail"]
    assert results["n1"].notes and all(note not in results["n0"].notes for note in results["n1"].notes)


def test_wrong_settings_are_reported_on_the_step(workspace):
    runner, load = workspace(recording())
    results = runner.run(chain(load, ("blinks", dict(min_ms=200, max_ms=100)), ("smooth", {})))
    assert "longer than the shortest" in results["n1"].error
    assert results["n2"].blocked
    assert "between 1 and 1000" in runner.run(chain(load, ("blinks", dict(min_ms=-5))))["n1"].error
