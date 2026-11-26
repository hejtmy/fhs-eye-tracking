"""Reading delimited text robustly. Shared by the generic and the Tobii Pro Lab reader."""
from __future__ import annotations

import re

import pandas as pd

from . import head, open_text

SEPARATORS = {"tab": "\t", "comma": ",", "semicolon": ";", "space": r"\s+"}
COMMA_NUMBER = re.compile(r"[-+]?\d+,\d+(?:[eE][-+]?\d+)?")
DOT_NUMBER = re.compile(r"[-+]?\d*\.\d+(?:[eE][-+]?\d+)?")


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
        # Judge whole cells only: dates (26.11.2026) and times (11:29:59.691) contain dots but are not decimals.
        split = re.compile(SEPARATORS[separator])
        cells = [cell.strip() for line in body[1:] for cell in split.split(line)]
        commas = sum(bool(COMMA_NUMBER.fullmatch(c)) for c in cells) if separator != "comma" else 0
        decimal = "," if commas and commas > sum(bool(DOT_NUMBER.fullmatch(c)) for c in cells) else "."
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
