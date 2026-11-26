import io
import json
import subprocess
import sys
import zipfile

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from conftest import EXAMPLES, chain, recording, webgazer_workbook

import server.app as service

client = TestClient(service.app)


def csv_bytes(frame=None):
    return (recording() if frame is None else frame).to_csv(index=False).encode()


def upload(*files):
    response = client.post("/api/datasets", files=[("files", (name, content)) for name, content in (files or [("rec.csv", csv_bytes())])])
    assert response.status_code == 200, response.text
    return response.json()


def graph_for(dataset_id, *steps, **source):
    return chain(("load", dict(source=dict(dataset=dataset_id, **source), width_px=1000, height_px=800)), *steps)


def test_catalog_describes_everything_the_app_draws():
    catalog = client.get("/api/catalog").json()
    assert {n["kind"] for n in catalog["nodes"]} >= {"load", "fixations_ivt", "aoi_metrics", "aggregate"}
    assert all(n["group"] in {g["id"] for g in catalog["groups"]} for n in catalog["nodes"])
    assert {r["id"] for r in catalog["readers"]} == {"delimited", "tobii_prolab", "tobii_glasses2", "eyelink_asc", "webgazer"}
    assert len(catalog["examples"]["pipelines"]) == 6 and len(catalog["examples"]["datasets"]) == 4
    by_package = {n["kind"] for n in catalog["nodes"] if n["package"] == "pymovements"}
    assert by_package == {"offscreen", "blinks", "smooth", "fixations_ivt", "fixations_idt", "saccades", "fixations_file"} and catalog["packages"]["pymovements"]["version"]
    assert client.get("/api/health").json()["status"] == "ok"


def test_upload_probe_run_inspect_and_download():
    dataset = upload()
    assert dataset["files"] == [dict(name="rec.csv", label="rec")] and dataset["id"].startswith("u-")
    probe = client.post(f"/api/datasets/{dataset['id']}/probe", json={}).json()
    assert probe["reader"] == "delimited" and probe["suggestion"]["mapping"]["x"] == "x" and probe["rows"] == 200
    assert probe["columns"][0] == dict(name="time", type="number", example="0")

    graph = graph_for(dataset["id"], ("blinks", {}), ("fixations_ivt", dict(threshold=40)))
    run = client.post("/api/run", json=dict(graph=graph)).json()["steps"]
    assert 'gaze.detect("ivt", velocity_threshold=40.0, minimum_duration=60)' in run["n2"]["script"] and "script" not in run["n0"]
    assert [run[i]["status"] for i in ("n0", "n1", "n2")] == ["ok"] * 3 and run["n2"]["headline"] == "3 fixations"
    assert run["n0"]["inputs"][0]["name"] == "file: rec" and run["n0"]["is_source"]
    assert {t["name"]: t["change"] for t in run["n1"]["tables"]} == dict(samples="changed", blinks="new")
    assert run["n2"]["trials"] == {"rec": ["1"]} and "durations" in [v["id"] for v in run["n2"]["views"]]

    step = dict(graph=graph, node="n2")
    page = client.post("/api/table", json=dict(step, table="fixations", limit=2)).json()
    assert page["total"] == 3 and len(page["rows"]) == 2 and page["columns"][2]["about"].startswith("Order of the fixation")
    raw = client.post("/api/table", json=dict(graph=graph, node="n0", side="input", table="file: rec", offset=10, limit=5)).json()
    assert raw["total"] == 200 and raw["rows"][0][0] == 100
    before = client.post("/api/table", json=dict(step, side="input", table="blinks")).json()
    assert before["total"] == 1
    csv = client.post("/api/download", json=dict(step, table="fixations"))
    assert len(pd.read_csv(io.BytesIO(csv.content))) == 3 and "fixations.csv" in csv.headers["content-disposition"]
    excel = client.post("/api/download", json=dict(step, table="fixations", excel=True))
    assert excel.content.startswith(b"\xef\xbb\xbf") and pd.read_csv(io.BytesIO(excel.content), sep=";", decimal=",").shape == pd.read_csv(io.BytesIO(csv.content)).shape
    assert client.post("/api/table", json=dict(step, table="nope")).status_code == 422


def test_views_are_plotly_figures_and_can_zoom_and_compare():
    dataset = upload(("rec.csv", csv_bytes(pd.concat([recording(rate=1000).assign(trial=t) for t in (1, 2)]))))
    graph = graph_for(dataset["id"], ("blinks", {}), ("fixations_ivt", dict(threshold=30)), ("aoi_draw", dict(aois=[dict(name="L", shape="rect", x=50, y=50, w=100, h=100)])),
                      ("aoi_metrics", {}), ("aoi_transitions", {}))
    step = dict(graph=graph, node="n2", trial="2")
    signal = client.post("/api/view", json=dict(step, view="signal", compare=True)).json()
    names = [t["name"] for t in signal["data"]]
    assert signal["info"]["title"] == "Participant rec · trial 2" and {"gaze x", "pupil", "speed", "before this step", "fixation", "blink"} <= set(names)
    zoomed = client.post("/api/view", json=dict(step, view="signal", window=[1000, 1300])).json()
    assert zoomed["layout"]["xaxis"]["range"] == [1000, 1300] and max(x for x in zoomed["data"][0]["x"] if x is not None) <= 1300
    for view, node in (("gaze", "n3"), ("heatmap", "n3"), ("durations", "n2"), ("aoi_bars", "n4"), ("transition_matrix", "n5")):
        figure = client.post("/api/view", json=dict(graph=graph, node=node, view=view)).json()
        assert "layout" in figure and "info" in figure, view
    assert client.post("/api/view", json=dict(graph=graph, node="n1", view="aoi_bars")).status_code == 422
    json.dumps(signal, allow_nan=False)


def test_several_files_labels_and_stimulus_images():
    dataset = upload(("livedata.csv", csv_bytes()), ("livedata.csv", csv_bytes()))
    assert [f["label"] for f in dataset["files"]] == ["livedata", "livedata-2"] and dataset["files"][1]["name"] == "livedata-2.csv"
    renamed = client.patch(f"/api/datasets/{dataset['id']}/files/livedata-2.csv", json=dict(label="Anna")).json()
    assert [f["label"] for f in renamed["files"]] == ["livedata", "Anna"]
    run = client.post("/api/run", json=dict(graph=graph_for(dataset["id"]))).json()["steps"]["n0"]
    assert run["trials"] == {"livedata": ["1"], "Anna": ["1"]}

    picture = io.BytesIO()
    Image.new("RGB", (40, 30), "red").save(picture, "JPEG")
    with_image = client.post(f"/api/datasets/{dataset['id']}/stimuli", files=[("files", ("scene.jpg", picture.getvalue()))]).json()
    assert with_image["stimuli"] == ["scene"]
    assert client.get(f"/api/datasets/{dataset['id']}/stimuli/scene").headers["content-type"] == "image/png"
    figure = client.post("/api/view", json=dict(graph=graph_for(dataset["id"]), node="n0", view="gaze")).json()
    assert figure["layout"]["images"][0]["source"].endswith("/stimuli/scene")   # the only image is used for every trial
    assert client.post(f"/api/datasets/{dataset['id']}/stimuli", files=[("files", ("x.png", b"not an image"))]).status_code == 415

    smaller = client.delete(f"/api/datasets/{dataset['id']}/files/livedata.csv").json()
    assert [f["label"] for f in smaller["files"]] == ["Anna"]
    assert client.delete(f"/api/datasets/{dataset['id']}").json() == dict(deleted=True)
    assert client.get(f"/api/datasets/{dataset['id']}").status_code == 422


def test_webgazer_workbook_with_a_large_photo_placed_as_it_was_shown(tmp_path):
    dataset = upload(("webgazer.xlsx", webgazer_workbook(tmp_path / "webgazer.xlsx").read_bytes()))
    photo = io.BytesIO()
    Image.new("RGB", (6000, 4000), "white").save(photo, "JPEG")
    assert client.post(f"/api/datasets/{dataset['id']}/stimuli", files=[("files", ("3333.jpg", photo.getvalue()))]).json()["stimuli"] == ["3333"]
    assert Image.open(io.BytesIO(client.get(f"/api/datasets/{dataset['id']}/stimuli/3333").content)).width == 2560   # shrunk, proportions kept

    probe = client.post(f"/api/datasets/{dataset['id']}/probe", json=dict(reader="auto", options={})).json()
    assert probe["reader"] == "webgazer" and probe["markers"] == 4
    params = probe["suggestion"]["params"]
    graph = chain(("load", dict(params, source=dict(dataset=dataset["id"], mapping=probe["suggestion"]["mapping"]))))
    image = client.post("/api/view", json=dict(graph=graph, node="n0", view="gaze", trial="s2")).json()["layout"]["images"][0]
    assert image["source"].endswith("/stimuli/3333") and image["sizing"] == "contain" and (image["x"], image["y"], image["xanchor"]) == (960, 540, "center")


def test_uploads_are_checked(monkeypatch):
    assert client.post("/api/datasets", files=[("files", ("virus.exe", b"MZ"))]).status_code == 415
    with monkeypatch.context() as patch:
        patch.setattr(service, "MAX_UPLOAD", 1000)
        assert client.post("/api/datasets", files=[("files", ("big.csv", csv_bytes()))]).status_code == 413
    assert not [p for p in service.library.uploads_root.iterdir() if not (p / "dataset.json").exists() or not json.loads((p / "dataset.json").read_text())["files"]]
    for bad in ("..%2F..%2Fetc", "visual-search%2F..%2Fx", "U-ABC", "a.b", "." * 3):
        assert client.get(f"/api/datasets/{bad}").status_code in (404, 422)
        with pytest.raises(Exception):
            service.library.get(bad.replace("%2F", "/"))
    assert client.get("/../../etc/passwd").status_code in (200, 404) and "root:" not in client.get("/..%2F..%2Fetc/passwd").text
    assert client.post("/api/datasets/visual-search/files", files=[("files", ("a.csv", csv_bytes()))]).status_code == 403
    assert client.delete("/api/datasets/visual-search").status_code == 422
    dataset = upload(("../../escape.csv", csv_bytes()))
    assert dataset["files"][0]["name"] == "escape.csv"


def test_old_uploads_are_removed(tmp_path):
    from gazelab import Library
    library = Library(uploads=tmp_path)
    old, fresh = library.create("old"), library.create("fresh")
    import os
    for name in ("dataset.json", ".used"):
        (old.root / name).touch()
        os.utime(old.root / name, (0, 0))
    assert library.purge(older_than_hours=1) == 1 and not old.root.exists() and fresh.root.exists()


def test_example_dataset_defaults_reach_the_probe():
    probe = client.post("/api/datasets/glasses-shelf/probe", json={}).json()
    assert probe["reader"] == "tobii_prolab" and probe["markers"] == 8
    assert probe["suggestion"]["mapping"]["x"] == "Mapped gaze data X [Shelf]" and probe["suggestion"]["params"]["geometry"] == "camera"


def test_export_is_a_self_contained_copy_that_reruns_to_the_same_numbers(tmp_path):
    spec = json.loads((EXAMPLES / "pipelines" / "04-glasses-shelf.json").read_text())
    response = client.post("/api/export", json=dict(graph=spec["graph"], name="Shelf study"))
    assert response.status_code == 200 and "shelf-study.zip" in response.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = archive.namelist()
        archive.extractall(tmp_path)
    assert {"run.py", "pipeline.json", "requirements.txt", "README.txt", "results/steps.json", "gazelab/core.py", "data/glasses-shelf/dataset.json"} <= set(names)
    steps = json.loads((tmp_path / "results" / "steps.json").read_text())
    assert [s["kind"] for s in steps][:4] == ["load", "trials_from_events", "interpolate", "fixations_ivt"] and all(s["status"] == "ok" for s in steps)
    assert "06_aoi_metrics/samples.csv" not in names and "06_aoi_metrics/aoi_metrics.csv" in "".join(names)   # only what a step changed
    served = {name: (tmp_path / "results" / name).read_text() for s in steps for name in s["tables"]}
    for name in served:
        (tmp_path / "results" / name).unlink()
    done = subprocess.run([sys.executable, "run.py"], cwd=tmp_path, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    for name, text in served.items():
        pd.testing.assert_frame_equal(pd.read_csv(io.StringIO(text)), pd.read_csv(tmp_path / "results" / name))


def test_plugins_add_steps_without_touching_the_package(tmp_path):
    (tmp_path / "double.py").write_text('''
from gazelab import Node, Number, register

@register
class Scale(Node):
    kind = "plugin_scale"
    title = "Scale pupil"
    group = "clean"
    summary = "Multiply the pupil signal."
    explain = "An example plug-in step."
    params = (Number("factor", "Factor", 2, min=0, max=10),)

    def run(self, data, p, ctx):
        return data.update(f"Pupil multiplied by {p['factor']:g}.", samples=data.samples.assign(pupil=data.samples.pupil * p["factor"]))
''')
    from gazelab import NODES
    from gazelab.nodes import load_plugins
    try:
        assert load_plugins(tmp_path) == ["double"]
        dataset = upload()
        run = client.post("/api/run", json=dict(graph=graph_for(dataset["id"], ("plugin_scale", dict(factor=3))))).json()["steps"]["n1"]
        assert run["status"] == "ok" and run["notes"] == ["Pupil multiplied by 3."] and "pupil: 180 changed" in run["tables"][0]["detail"]
        assert "plugin_scale" in [n["kind"] for n in client.get("/api/catalog").json()["nodes"]]
    finally:
        NODES.pop("plugin_scale", None)


@pytest.mark.parametrize("body", [dict(graph=dict(nodes=[], edges=[])), dict(graph="x")])
def test_bad_requests_get_readable_errors(body):
    response = client.post("/api/run", json=body)
    assert response.status_code == 422 and response.json()["detail"]
