import json
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

os.environ["GAZELAB_DATA_DIR"] = tempfile.mkdtemp(prefix="gazelab-tests-")

from gazelab import Context, Library, Runner  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def chain(*steps, branches=()):
    """A graph from [(kind, settings), …]; branches are (index to branch from, [(kind, settings), …])."""
    nodes = [dict(id=f"n{i}", kind=kind, params=params) for i, (kind, params) in enumerate(steps)]
    edges = [dict(source=a["id"], target=b["id"]) for a, b in zip(nodes, nodes[1:])]
    for b, (origin, extra) in enumerate(branches):
        previous = f"n{origin}"
        for i, (kind, params) in enumerate(extra):
            nodes.append(dict(id=f"b{b}{i}", kind=kind, params=params))
            edges.append(dict(source=previous, target=nodes[-1]["id"]))
            previous = nodes[-1]["id"]
    return dict(nodes=nodes, edges=edges)


@pytest.fixture
def examples():
    return Runner(Context(Library(examples=EXAMPLES / "datasets")))


@pytest.fixture
def workspace(tmp_path):
    """Write a table as a one-file dataset and get a runner plus the Load step for it."""
    def make(frame, name="rec.csv", stimuli=None, **load):
        folder = tmp_path / "data" / "d1"
        folder.mkdir(parents=True, exist_ok=True)
        if isinstance(frame, (bytes, str)):
            (folder / name).write_bytes(frame if isinstance(frame, bytes) else frame.encode())
        else:
            frame.to_csv(folder / name, index=False)
        (folder / "dataset.json").write_text(json.dumps(dict(name="test", files=[dict(name=name, label="P1")], stimuli=stimuli or {})))
        settings = dict(source=dict(dataset="d1"), width_px=1000, height_px=800, **load)
        return Runner(Context(Library(examples=tmp_path / "data"))), ("load", settings)
    return make


def recording(rate=100, noise=0.5, seed=1):
    """Three fixations of 500 ms with a 200 ms blink before the third. Positions and timing are exact, so tests can check them."""
    rng = np.random.default_rng(seed)
    step = 1000 / rate
    time = np.arange(0, 2000, step)
    x, y = np.full(len(time), 100.0), np.full(len(time), 100.0)
    x[time >= 520], y[time >= 1240] = 600.0, 500.0
    jump = (time >= 500) & (time < 520)
    x[jump] = np.linspace(100, 600, jump.sum() + 2)[1:-1]
    x, y = x + rng.normal(0, noise, len(time)), y + rng.normal(0, noise, len(time))
    pupil = 4 + 0.001 * time / 10
    blink = (time >= 1020) & (time < 1220)
    x[blink], y[blink], pupil[blink] = np.nan, np.nan, np.nan
    return pd.DataFrame(dict(time=time, x=x, y=y, pupil=pupil))


def webgazer_workbook(path):
    """A small workbook laid out like the ones the WebGazer experiment saves: two images, each after a fixation cross."""
    phases = (("cross1", "fixační kříž", 300), ("s1", "Přednáška – Lukavský (12x6 in, na šířku).png", 1000),
              ("cross2", "fixační kříž", 300), ("s2", "3333.jpg", 1000))
    rows, start = [], 0
    for phase, stimulus, length in phases:
        rows += [(start + t, phase, stimulus, t, 960 + t % 7, 540 - t % 5) for t in range(5, length, 33)]
        start += length
    calibration = [["SOUHRN POKUSŮ O KALIBRACI"] + [None] * 7,
                   ["pokus", "zacatek", "okno_sirka_px", "okno_vyska_px", "pocet_kliknuti", "prumerna_odchylka_px", "presnost_pct", "pouzito_pro_experiment"],
                   [1, "26. 11. 2026 10:50:01", 1280, 598, 45, 140, 55, "ne"], [2, "26. 11. 2026 10:54:52", 1280, 598, 45, 88, 71, "ano"],
                   [None] * 8, ["KLIKNUTÍ NA KALIBRAČNÍ BODY"] + [None] * 7,
                   ["pokus", "bod", "cil_x_px", "cil_y_px", "kliknuti_c", "cas_ms", "odhad_x_px", "odhad_y_px"], [2, 1, 130, 62, 1, 2829, 653, 74]]
    with pd.ExcelWriter(path) as book:
        pd.DataFrame([["List / sloupec", "Význam"]]).to_excel(book, sheet_name="Legenda", index=False, header=False)
        pd.DataFrame([[1, "3333.jpg", 3.0, 0.03, 100]], columns=["poradi", "obrazek", "doba_pohledu_s", "prvni_pohled_s", "pocet_vzorku"]).to_excel(
            book, sheet_name="AOI", index=False)
        pd.DataFrame(rows, columns=["cas_ms", "faze", "stimul", "cas_ve_fazi_ms", "x_1920", "y_1080"]).to_excel(book, sheet_name="Vzorky", index=False)
        pd.DataFrame(calibration).to_excel(book, sheet_name="Kalibrace", index=False, header=False)
    return path
