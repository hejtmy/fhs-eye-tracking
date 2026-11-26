"""Run a saved pipeline without the web app.

    python -m gazelab run pipeline.json --data data --out results
    python -m gazelab steps
"""
import argparse
import json
import sys
from pathlib import Path

from .core import GROUPS, NODES
from .datasets import Context, Library
from .pipeline import Runner, changes, plan


def result_files(graph, results):
    """(relative path, text) for everything worth keeping from a run: each step's
    new or changed tables as CSV, what it reported, and an index."""
    order, _ = plan(graph)
    index, number = [], 0
    for spec in order:
        result = results.get(spec["id"])
        if result is None:
            continue
        number += 1
        folder = f"{number:02d}_{spec['kind']}"
        entry = dict(step=number, id=spec["id"], kind=spec["kind"], title=NODES[spec["kind"]].title, settings=result.params,
                     status="ok" if result.ok else "error", error=result.error, notes=result.notes, tables=[])
        if result.ok:
            for change in changes(result.parent, result.bundle):
                if change["change"] in ("new", "changed"):
                    entry["tables"].append(f"{folder}/{change['table']}.csv")
                    yield f"{folder}/{change['table']}.csv", result.bundle[change["table"]].to_csv(index=False)
            yield f"{folder}/notes.txt", "\n".join(result.notes) + "\n"
        index.append(entry)
    yield "steps.json", json.dumps(index, indent=2, ensure_ascii=False, default=str)


def run_pipeline(pipeline, data=None, out=None, cache=None):
    """Run a pipeline file (or graph dict). Datasets are looked up in the `data` folder. Returns {step id: Result}."""
    folder = Path.cwd()
    if not isinstance(pipeline, dict):
        folder = Path(pipeline).resolve().parent
        pipeline = json.loads(Path(pipeline).read_text())
    graph = pipeline.get("graph", pipeline)
    results = Runner(Context(Library(examples=Path(data) if data else folder / "data")), cache).run(graph)
    if out:
        for name, text in result_files(graph, results):
            target = Path(out) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(prog="gazelab", description="Run eye-tracking pipelines built in Gaze Lab.")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run a pipeline file and write every step's tables as CSV")
    run.add_argument("pipeline")
    run.add_argument("--data", help="folder that holds the dataset folders (default: data/ next to the pipeline)")
    run.add_argument("--out", default="results", help="where to write results (default: results/)")
    commands.add_parser("steps", help="list the available steps")
    args = parser.parse_args(argv)
    if args.command == "steps":
        for group in GROUPS:
            print(f"\n{group['title']}")
            for node in NODES.values():
                if node.group == group["id"]:
                    print(f"  {node.kind:<20} {node.title}: {node.summary}")
        return 0
    results = run_pipeline(args.pipeline, args.data, args.out)
    failed = 0
    for result in results.values():
        mark = "ok " if result.ok else "ERR"
        print(f"[{mark}] {NODES[result.kind].title}: {'; '.join(result.notes) if result.ok else result.error}")
        failed += not result.ok
    print(f"\nResults written to {Path(args.out).resolve()}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
