"""Reading delimited text robustly. Shared by the generic and the Tobii Pro Lab reader."""
from __future__ import annotations

import re

import pandas as pd

from . import head, open_text

SEPARATORS = {"tab": "\t", "comma": ",", "semicolon": ";", "space": r"\s+"}


def guess_format(path, separator="auto", decimal="auto"):
    """Work out the separator, the decimal mark and how many comment lines precede the header."""
    lines = head(path, 65536).splitlines()
    skip = 0
    while skip < len(lines) and (not lines[skip].strip() or lines[skip].lstrip().startswith(("#", "//"))):
        skip += 1
    body = lines[skip:skip + 40]
    header = body[0] if body else ""
    if separator == "auto":
        counts = {name: header.count(char) for name, char in (("tab", "\t"), ("semicolon", ";"), ("comma", ","))}
        separator = max(counts, key=counts.get) if max(counts.values()) else "space"
    if decimal == "auto":
        data = "\n".join(body[1:])
        commas = len(re.findall(r"\d,\d", data)) if separator != "comma" else 0
        decimal = "," if commas and commas > len(re.findall(r"\d\.\d", data)) else "."
    return separator, decimal, skip


def read_table(path, separator="auto", decimal="auto", missing=""):
    separator, decimal, skip = guess_format(path, separator, decimal)
    codes = [code.strip() for code in missing.split(",") if code.strip()]
    with open_text(path) as handle:
        frame = pd.read_csv(handle, sep=SEPARATORS[separator], decimal=decimal, skiprows=skip, skipinitialspace=True,
                            na_values=[".", "NA", "NaN", "nan", "N/A", *codes], low_memory=False,
                            engine="python" if separator == "space" else "c")
    frame.columns = [str(c).strip() for c in frame.columns]
    return frame, dict(separator=separator, decimal=decimal)
