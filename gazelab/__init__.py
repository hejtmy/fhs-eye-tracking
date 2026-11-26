"""Gaze Lab: eye-tracking pipelines built from small, self-describing steps.

    from gazelab import run_pipeline
    results = run_pipeline("pipeline.json", data="data", out="results")
"""
from .core import (GROUPS, KEYS, NODES, TABLES, VIEWS, Bundle, Choice, Columns, Custom, Node, Number, Param, PipelineError, num,  # noqa: F401
                   TableName, Text, Toggle, register, runs, sample_period, table, trial_info, trials, view, with_trial_info)
from . import readers, views, nodes  # noqa: F401,E402  (registers readers, views and steps)
from .datasets import Context, Dataset, Library  # noqa: F401,E402
from .pipeline import Runner, changes, plan  # noqa: F401,E402
from .cli import run_pipeline  # noqa: F401,E402

__version__ = "2.0.0"
nodes.load_plugins()
