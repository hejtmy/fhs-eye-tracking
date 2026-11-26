"""Datasets on disk. An example and an upload are the same thing: a folder holding
`dataset.json`, the recording files and (optionally) `stimuli/` images."""
from __future__ import annotations

import json
import re
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from .core import PipelineError

ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
MANIFEST = "dataset.json"
USED = ".used"


def safe_name(name, fallback="file"):
    """A file name without folders or awkward characters."""
    name = re.sub(r"[^\w.\- ()\[\]]+", "_", Path(str(name)).name).strip(" .")
    return name[:120] or fallback


def match_stimulus(names, value):
    """Match a stimulus label from the data to an image name: exact, without extension, ignoring case, or the only image."""
    if value is not None and value == value:
        stem = Path(str(value)).stem
        lowered = {n.casefold(): n for n in names}
        for candidate in (str(value), stem):
            if candidate in names:
                return candidate
        if stem.casefold() in lowered:
            return lowered[stem.casefold()]
    return next(iter(names)) if len(names) == 1 else None


@dataclass
class Dataset:
    id: str
    root: Path
    info: dict
    example: bool = False

    @property
    def files(self):
        return self.info.get("files", [])

    @property
    def stimuli(self):
        """{name: path relative to the dataset folder}"""
        return self.info.get("stimuli", {})

    def path(self, name):
        path = (self.root / name).resolve()
        if not path.is_relative_to(self.root.resolve()) or not path.is_file():
            raise PipelineError(f"The file “{name}” is missing from this dataset.")
        return path

    def stimulus_for(self, value):
        return match_stimulus(self.stimuli, value)

    def stamp(self):
        manifest = self.root / MANIFEST
        return f"{self.id}:{manifest.stat().st_mtime_ns}"

    def save(self):
        (self.root / MANIFEST).write_text(json.dumps(self.info, indent=2, ensure_ascii=False))

    def unique_label(self, label):
        taken = {f["label"] for f in self.files}
        base, n = label, 2
        while label in taken:
            label, n = f"{base}-{n}", n + 1
        return label

    def describe(self):
        return dict(id=self.id, example=self.example, **{k: self.info.get(k) for k in ("name", "description", "provider", "synthetic", "created")},
                    files=self.files, stimuli=sorted(self.stimuli), defaults=self.info.get("defaults", {}))


def _touch(folder):
    """Remember that an upload is still in use, at most once every ten minutes."""
    marker = folder / USED
    try:
        if not marker.exists() or time.time() - marker.stat().st_mtime > 600:
            marker.touch()
    except OSError:
        pass


def stimulus_url(dataset_id, name):
    """Where the web app can fetch a stimulus image. Standalone runs ignore it."""
    return f"/api/datasets/{dataset_id}/stimuli/{name}"


class Library:
    """Finds datasets by id in the bundled examples and in the folder that holds uploads."""

    def __init__(self, examples: Path | None = None, uploads: Path | None = None):
        self.examples_root, self.uploads_root = examples, uploads
        if uploads:
            uploads.mkdir(parents=True, exist_ok=True)

    def get(self, dataset_id) -> Dataset:
        if not isinstance(dataset_id, str) or not dataset_id:
            raise PipelineError("Choose a dataset: pick an example or upload your own recording.")
        if ID.match(dataset_id):
            for root, example in ((self.examples_root, True), (self.uploads_root, False)):
                folder = root / dataset_id if root else None
                if folder and (folder / MANIFEST).is_file():
                    if not example:
                        _touch(folder)
                    return Dataset(dataset_id, folder, json.loads((folder / MANIFEST).read_text()), example)
        raise PipelineError("This dataset is no longer on the server. Uploads are removed after a while; upload the files again.")

    def examples(self):
        if not self.examples_root or not self.examples_root.is_dir():
            return []
        return [self.get(p.parent.name) for p in sorted(self.examples_root.glob(f"*/{MANIFEST}"))]

    def create(self, name):
        dataset_id = "u-" + uuid.uuid4().hex
        root = self.uploads_root / dataset_id
        root.mkdir()
        dataset = Dataset(dataset_id, root, dict(name=name[:120], files=[], stimuli={}, created=time.time()))
        dataset.save()
        return dataset

    def delete(self, dataset_id):
        dataset = self.get(dataset_id)
        if dataset.example:
            raise PipelineError("Example datasets cannot be deleted.")
        shutil.rmtree(dataset.root)

    def purge(self, older_than_hours):
        """Remove uploads that have not been touched for a while. Returns how many were removed."""
        if not self.uploads_root or older_than_hours <= 0:
            return 0
        removed, limit = 0, time.time() - older_than_hours * 3600
        for folder in self.uploads_root.iterdir():
            if not folder.is_dir():
                continue
            used = [f.stat().st_mtime for f in (folder / MANIFEST, folder / USED) if f.exists()]
            if not used or max(used) < limit:
                shutil.rmtree(folder, ignore_errors=True)
                removed += 1
        return removed


class Context:
    """What steps may ask their surroundings for. Passed to Node.run as `ctx`."""

    def __init__(self, library: Library, max_rows=3_000_000):
        self.library, self.max_rows = library, max_rows

    def dataset(self, dataset_id) -> Dataset:
        return self.library.get(dataset_id)
