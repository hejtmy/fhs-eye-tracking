"""An example plug-in step. Rename the file without the leading underscore to switch it on.

It shows everything a step needs: a description students can read, settings
with validation, a requirement on earlier steps, and a `run` that returns a
new bundle instead of changing the one it received.
"""
import numpy as np

from gazelab import Node, Number, PipelineError, num, register


@register
class RemoveFastSamples(Node):
    kind = "example_remove_fast"          # stored in pipeline files; never change it afterwards
    title = "Remove fast samples"
    group = "clean"                       # where it appears in the step library
    icon = "gauge"
    summary = "Treat samples that move impossibly fast as missing."
    explain = """
        The eye cannot move faster than about 900 degrees per second. A sample that would require a faster
        movement is a tracker glitch, not behaviour. This step removes such samples.

        It needs a speed for every sample, so place it after fixation detection by speed (I-VT).
    """
    question = "After removing these samples, does the number of fixations change when you detect again?"
    needs = ("samples", "fixations")      # tables that must exist; the app explains what to add if they do not
    makes = ()                            # tables this step creates; this one only changes the samples
    view = "signal"                       # the figure opened first
    params = (Number("limit", "Fastest plausible speed", 900, unit="per second", min=1, max=100000, step=50),)

    def run(self, data, p, ctx):
        samples = data.samples
        if "velocity" not in samples:
            raise PipelineError("This step needs sample speeds. Add “Detect fixations by speed (I-VT)” before it.")
        too_fast = samples["velocity"].to_numpy(float) > p["limit"]
        cleaned = samples.assign(x=samples["x"].where(~too_fast), y=samples["y"].where(~too_fast), masked=samples["masked"].to_numpy() | too_fast)
        return data.update(f"{num(np.count_nonzero(too_fast))} samples moved faster than {p['limit']:g} per second and were removed.", samples=cleaned)
