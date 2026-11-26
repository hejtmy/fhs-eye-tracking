"""Pipeline steps. Every module in this folder is imported at start-up, and each
class decorated with @register becomes a step in the app.

Extra steps can also live outside the package: point the environment variable
GAZELAB_PLUGINS at a folder of .py files and they are loaded the same way.
"""
import os
import sys
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from pkgutil import iter_modules

for module in sorted(iter_modules(__path__), key=lambda m: m.name):
    if not module.name.startswith("_"):
        import_module(f"{__name__}.{module.name}")


def load_plugins(folder=None):
    """Import every .py file in the plug-in folder. Returns the names loaded."""
    folder = folder or os.environ.get("GAZELAB_PLUGINS")
    loaded = []
    if not folder or not Path(folder).is_dir():
        return loaded
    for path in sorted(Path(folder).glob("*.py")):
        if path.name.startswith("_"):
            continue
        name = f"gazelab_plugin_{path.stem}"
        spec = spec_from_file_location(name, path)
        module = module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        loaded.append(path.stem)
    return loaded
