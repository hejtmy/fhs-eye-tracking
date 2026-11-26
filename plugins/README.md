# Plug-in steps

Any `.py` file in this folder is loaded when Gaze Lab starts and can add steps,
views or file readers without touching the application itself. Files whose
name starts with `_` are ignored.

`_example_velocity_filter.py` is a complete, working example: remove the
leading underscore, restart the server, and “Remove fast samples” appears in
the step library under Clean. See `docs/extending.md` for the full contract.
