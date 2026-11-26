"""Run a graph of steps. Results are cached per step, so changing one setting
only recomputes that step and the ones after it."""
from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from threading import Lock

import numpy as np

from .core import NODES, Bundle, PipelineError, makers, num

MAX_NODES = 60
log = logging.getLogger("gazelab")


@dataclass
class Result:
    id: str
    kind: str
    fingerprint: str = ""
    bundle: Bundle | None = None
    parent: Bundle | None = None
    error: str = ""
    blocked: bool = False   # an earlier step failed, so this one did not run
    ms: int = 0
    cached: bool = False
    params: dict = field(default_factory=dict)

    @property
    def ok(self):
        return self.bundle is not None

    @property
    def notes(self):
        """What this step itself reported (not the steps before it)."""
        before = len(self.parent.notes) if self.parent else 0
        return list(self.bundle.notes[before:]) if self.bundle else []


def plan(graph):
    """Check the shape of a graph and return its steps parents-first, plus each step's parent."""
    if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list) or not isinstance(graph.get("edges", []), list):
        raise PipelineError("A pipeline is an object with a list of nodes and a list of edges.")
    nodes, edges = graph["nodes"], graph.get("edges", [])
    if not 1 <= len(nodes) <= MAX_NODES:
        raise PipelineError(f"A pipeline has between 1 and {MAX_NODES} steps.")
    by_id = {}
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get("id"), str) or not 0 < len(node["id"]) <= 80:
            raise PipelineError("Every step needs a short text id.")
        if node["id"] in by_id:
            raise PipelineError(f"Two steps share the id {node['id']!r}.")
        if node.get("kind") not in NODES:
            raise PipelineError(f"Unknown step type {node.get('kind')!r}. It may come from a plug-in that is not installed here.")
        by_id[node["id"]] = node
    parent = {i: None for i in by_id}
    for edge in edges:
        source, target = (edge.get("source"), edge.get("target")) if isinstance(edge, dict) else (None, None)
        if source not in by_id or target not in by_id or source == target:
            raise PipelineError("A connection must join two different steps of this pipeline.")
        if parent[target] is not None:
            raise PipelineError(f"“{NODES[by_id[target]['kind']].title}” has two inputs. Each step continues from exactly one step.")
        parent[target] = source
    order, placed = [], set()
    for start in by_id:
        chain, current = [], start
        while current is not None and current not in placed:
            if current in chain:
                raise PipelineError("The connections form a loop. Data must flow forward.")
            chain.append(current)
            current = parent[current]
        for node_id in reversed(chain):
            placed.add(node_id)
            order.append(by_id[node_id])
    for node in order:
        is_source = not NODES[node["kind"]].needs
        if is_source and parent[node["id"]]:
            raise PipelineError(f"“{NODES[node['kind']].title}” starts a pipeline; nothing can be connected into it.")
    return order, parent


def ancestors(parent, target):
    keep, current = set(), target
    while current is not None:
        keep.add(current)
        current = parent[current]
    return keep


class Cache:
    """A small least-recently-used store of step results, shared by all requests."""

    def __init__(self, size=64):
        self.size, self.items, self.lock = size, OrderedDict(), Lock()

    def get(self, key):
        with self.lock:
            if key in self.items:
                self.items.move_to_end(key)
                return self.items[key]

    def put(self, key, value):
        with self.lock:
            self.items[key] = value
            self.items.move_to_end(key)
            while len(self.items) > self.size:
                self.items.popitem(last=False)


class Runner:
    def __init__(self, ctx, cache=None):
        self.ctx, self.cache = ctx, cache or Cache()

    def run(self, graph, target=None) -> dict[str, Result]:
        """Run every step (or only `target` and the steps it depends on).

        A failing step does not stop the others: its error is reported on that
        step and the steps after it are marked as blocked.
        """
        order, parent = plan(graph)
        if target is not None:
            if target not in parent:
                raise PipelineError("The selected step is not part of this pipeline.")
            keep = ancestors(parent, target)
            order = [n for n in order if n["id"] in keep]
        results = {}
        for spec in order:
            node, before = NODES[spec["kind"]], results.get(parent[spec["id"]])
            result = Result(spec["id"], spec["kind"], parent=before.bundle if before else None)
            results[spec["id"]] = result
            if not node.needs and before is None:
                pass
            elif before is None:
                result.error = f"“{node.title}” needs data. Connect it after a Load step."
                continue
            elif not before.ok:
                result.blocked, result.error = True, "Waiting for an earlier step to succeed."
                continue
            try:
                result.params = node.clean(spec.get("params"))
                stamp = node.stamp(result.params, self.ctx)
                text = json.dumps([spec["kind"], result.params, before.fingerprint if before else "", stamp], sort_keys=True, default=str)
                result.fingerprint = hashlib.sha1(text.encode()).hexdigest()
                hit = self.cache.get(result.fingerprint)
                if hit is not None:
                    result.bundle, result.error, result.ms, result.cached = hit.bundle, hit.error, hit.ms, True
                    continue
                for name in node.needs:
                    if name not in before.bundle:
                        made_by = " or ".join(f"“{t}”" for t in makers(name)[:2]) or "a step that creates it"
                        raise PipelineError(f"“{node.title}” needs {name.replace('_', ' ')}. Add {made_by} before it.")
                started = time.perf_counter()
                result.bundle = node.run(before.bundle if before else Bundle(), result.params, self.ctx)
                result.ms = round((time.perf_counter() - started) * 1000)
            except PipelineError as exc:
                result.error = str(exc)
            except Exception as exc:  # a bug in a step, or data it was not written for: report it on the step, keep the app alive
                log.exception("step %s (%s) failed", spec["id"], spec["kind"])
                result.error = f"This step failed unexpectedly ({type(exc).__name__}: {str(exc)[:200]}). The data may have a shape the step was not written for."
            if result.fingerprint:
                self.cache.put(result.fingerprint, result)
        return results


def changes(before: Bundle | None, after: Bundle):
    """Describe what a step did to each table: new, changed (and how), or untouched."""
    out = []
    for name, frame in after.tables.items():
        old = before.get(name) if before else None
        if old is None:
            out.append(dict(table=name, change="new", detail=f"{num(len(frame))} rows"))
        elif old is frame:
            out.append(dict(table=name, change="same", detail=""))
        else:
            parts = []
            if len(old) != len(frame):
                parts.append(f"{num(len(old))} → {num(len(frame))} rows")
            added = [c for c in frame.columns if c not in old.columns]
            if added:
                parts.append("new column" + ("s " if len(added) > 1 else " ") + ", ".join(added[:4]) + ("…" if len(added) > 4 else ""))
            if len(old) == len(frame):
                for column in frame.columns:
                    if column not in old.columns:
                        continue
                    a, b = old[column].to_numpy(), frame[column].to_numpy()
                    if a.dtype.kind in "fiub" and b.dtype.kind in "fiub":
                        a, b = a.astype(float), b.astype(float)
                        lost = int((np.isnan(b) & ~np.isnan(a)).sum())
                        gained = int((~np.isnan(b) & np.isnan(a)).sum())
                        altered = int((~((a == b) | (np.isnan(a) & np.isnan(b)))).sum()) - lost - gained
                        bits = [f"{num(n)} {word}" for n, word in ((lost, "removed"), (gained, "filled in"), (altered, "changed")) if n]
                        if bits:
                            parts.append(f"{column}: " + ", ".join(bits))
                    elif not old[column].equals(frame[column]):
                        parts.append(f"{column} rewritten")
            out.append(dict(table=name, change="changed" if parts else "same", detail=" · ".join(parts)))
    for name in (before.tables if before else {}):
        if name not in after.tables:
            out.append(dict(table=name, change="removed", detail=""))
    return out
