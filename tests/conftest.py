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
