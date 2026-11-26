"""Any table of gaze samples: CSV, TSV or other delimited text. The fallback for custom data."""
from ..core import Choice, Text
from . import Raw, Reader, reader
from ._tables import read_table

SEPARATOR = Choice("separator", "Column separator", "auto",
                   options=(("auto", "Detect"), ("comma", "Comma"), ("tab", "Tab"), ("semicolon", "Semicolon"), ("space", "Spaces")))
DECIMAL = Choice("decimal", "Decimal mark", "auto", options=(("auto", "Detect"), (".", "Dot (3.14)"), (",", "Comma (3,14)")),
                 help="Software set to Czech or German often writes decimal commas.")


@reader
class Delimited(Reader):
    id = "delimited"
    title = "Table of samples (CSV, TSV, text)"
    about = "One row per gaze sample, one column per measurement. Works for exports from most eye trackers and for your own files."
    extensions = (".csv", ".tsv", ".txt", ".dat")
    options = (SEPARATOR, DECIMAL, Text("missing", "Codes for missing values", "", placeholder="e.g. -1, 9999",
                                         help="Values the tracker writes when it lost the eye, separated by commas."))

    def sniff(self, path, head):
        return 0.3

    def read(self, path, o):
        frame, used = read_table(path, o["separator"], o["decimal"], o["missing"])
        names = dict(tab="tabs", comma="commas", semicolon="semicolons", space="spaces")
        return Raw(frame, notes=[f"Read {path.name}: columns separated by {names[used['separator']]}, decimal mark “{used['decimal']}”."])
