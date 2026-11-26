"""Figures. Each view turns a bundle into a Plotly figure description (plain dicts),
so the same code serves the web app and anything else that can draw Plotly JSON.

Add a view with the @view decorator; it appears for every step whose output
contains the tables the view needs.
"""
import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter

from .core import KEYS, runs, sample_period, trials, view, num
from .datasets import match_stimulus, stimulus_key, stimulus_url

C = dict(x="#2563eb", y="#d97706", pupil="#0f766e", velocity="#7c3aed", before="#b6bcc6", fixation="#2563eb",
         saccade="#d97706", blink="#dc2626", removed="#f87171", filled="#38bdf8", marker="#64748b", path="#64748b")
AREAS = ["#2563eb", "#d97706", "#0f766e", "#be185d", "#7c3aed", "#65a30d", "#0891b2", "#b45309", "#4f46e5", "#dc2626"]
MAX_POINTS = 4000


def pick(data, sel):
    """The one trial a single-trial view shows: the selected one, else the first that fits."""
    groups = trials(data.samples)
    want = (sel.get("participant") or None, sel.get("trial") or None)
    key = want if want in groups else next((k for k in groups if want[0] in (None, k[0]) and want[1] in (None, k[1])), next(iter(groups)))
    return key, data.samples.iloc[groups[key]]


def select(frame, sel):
    """Rows of any table that match the chosen participant and trial (empty choice = all)."""
    for column in KEYS:
        if sel.get(column) and column in frame.columns:
            frame = frame[frame[column] == sel[column]]
    return frame


def own(frame, key):
    return frame[(frame["participant"] == key[0]) & (frame["trial"] == key[1])]


def thin(frame, columns, limit=MAX_POINTS):
    """Keep at most ~limit rows but preserve every peak, trough and gap, so a zoomed-out trace looks like the full one."""
    n = len(frame)
    if n <= limit:
        return frame, False
    keep, edges = {0, n - 1}, np.linspace(0, n, limit // 4 + 1).astype(int)
    for column in columns:
        values = frame[column].to_numpy(float)
        for a, b in zip(edges[:-1], edges[1:]):
            if np.isfinite(values[a:b]).any():
                keep.update((a + int(np.nanargmin(values[a:b])), a + int(np.nanargmax(values[a:b]))))
        change = np.flatnonzero(np.isnan(values[1:]) != np.isnan(values[:-1]))
        keep.update(change.tolist())
        keep.update((change + 1).tolist())
    return frame.iloc[sorted(keep)], True


def numbers(values):
    """A column as a JSON-friendly list with gaps as None."""
    values = np.asarray(values, float)
    return [None if not np.isfinite(v) else round(float(v), 3) for v in values]


def label(key):
    return f"Participant {key[0]} · trial {key[1]}"


def empty(message):
    return dict(data=[], layout=dict(annotations=[dict(text=message, showarrow=False, font=dict(size=14, color="#64748b"))],
                                     xaxis=dict(visible=False), yaxis=dict(visible=False)), info=dict(title=""))


# ----------------------------------------------------------------------------- signal over time

@view("signal", "Signal over time", compares=True)
def signal(data, sel, before=None):
    key, trial = pick(data, sel)
    start = float(trial["time"].iloc[0])
    trial = trial.assign(t=trial["time"] - start)
    period, duration = sample_period(trial["t"].to_numpy()), float(trial["t"].iloc[-1])
    window = sel.get("window")
    lo, hi = (max(0.0, window[0]), min(duration, window[1])) if window else (0.0, duration)
    part = trial[(trial["t"] >= lo) & (trial["t"] <= hi)]
    has_pupil = bool(trial["pupil"].notna().any())
    has_speed = "velocity" in trial.columns and bool(trial["velocity"].notna().any())
    shown, thinned = thin(part, ["x", "y"] + ["pupil"] * has_pupil + ["velocity"] * has_speed)
    time = numbers(shown["t"])

    # lanes: what happened when, as coloured bars on a shared time axis
    lanes = []
    for flag, name in (("masked", "removed"), ("filled", "filled")):
        spans = [(float(trial["t"].iloc[a]), float(trial["t"].iloc[b - 1]) + period) for a, b in runs(trial[flag].to_numpy())]
        if spans:
            lanes.append((name, C[name], spans))
    for name, single in (("blinks", "blink"), ("saccades", "saccade"), ("fixations", "fixation")):
        if name in data:
            rows = own(data[name], key)
            lanes.append((single, C[single], list(zip(rows["start"], rows["end"] + period))))  # an event lasts until its last sample is over
    panels = [("gaze", "Gaze position (px)", 3.0)] + [("pupil", f"Pupil ({data.meta.get('pupil_unit', 'as recorded')})", 2.0)] * has_pupil
    panels += [("speed", f"Speed ({data.meta.get('velocity_unit', 'px/s')})", 2.0)] * has_speed + [("lanes", "", 0.25 + 0.27 * len(lanes))] * bool(lanes)
    total, top, axis, layout = sum(h for *_, h in panels) + 0.25 * (len(panels) - 1), 1.0, {}, {}
    for i, (name, title, height) in enumerate(panels):
        axis[name] = "y" if i == 0 else f"y{i + 1}"
        layout["yaxis" if i == 0 else f"yaxis{i + 1}"] = dict(domain=[max(0.0, top - height / total), top], title=dict(text=title), zeroline=False)
        top -= (height + 0.25) / total

    traces = []
    if before is not None and before.samples is not data.samples:  # what this step received, drawn underneath in grey
        groups = trials(before.samples)
        if key in groups:
            old = before.samples.iloc[groups[key]]
            old = old.assign(t=old["time"] - start)
            old, _ = thin(old[(old["t"] >= lo) & (old["t"] <= hi)], ["x", "y"] + ["pupil"] * has_pupil)
            for column, panel in (("x", "gaze"), ("y", "gaze"), ("pupil", "pupil")):
                if panel in axis and column in old:
                    traces.append(dict(type="scatter", mode="lines", x=numbers(old["t"]), y=numbers(old[column]), yaxis=axis[panel], hoverinfo="skip",
                                       line=dict(color=C["before"], width=2.5), name="before this step", legendgroup="before", showlegend=column == "x"))
    for column, panel, name in (("x", "gaze", "gaze x"), ("y", "gaze", "gaze y"), ("pupil", "pupil", "pupil"), ("velocity", "speed", "speed")):
        if panel in axis:
            traces.append(dict(type="scatter", mode="lines", x=time, y=numbers(shown[column]), yaxis=axis[panel], name=name,
                               line=dict(color=C[column], width=1.4), connectgaps=False))

    for i, (name, colour, spans) in enumerate(lanes):
        xs, ys = [], []
        for a, b in [(a, b) for a, b in spans if b >= lo and a <= hi][:4000]:
            xs += [round(float(a), 2), round(float(b), 2), None]
            ys += [i, i, None]
        traces.append(dict(type="scatter", mode="lines", x=xs, y=ys, yaxis=axis["lanes"], name=name, hoverinfo="skip", showlegend=False,
                           line=dict(color=colour, width=11)))
    if lanes:
        layout["yaxis" + axis["lanes"][1:]].update(tickvals=list(range(len(lanes))), ticktext=[name for name, *_ in lanes], range=[len(lanes) - 0.4, -0.6],
                                                   showgrid=False, fixedrange=True)

    shapes, notes = [], []
    if has_speed and data.meta.get("velocity_threshold"):
        level = data.meta["velocity_threshold"]
        shapes.append(dict(type="line", xref="paper", x0=0, x1=1, yref=axis["speed"], y0=level, y1=level, line=dict(color=C["velocity"], width=1, dash="dash")))
        notes.append(dict(xref="paper", x=1, xanchor="right", yref=axis["speed"], y=level, yanchor="bottom", text="threshold", showarrow=False, font=dict(size=10, color=C["velocity"])))
        speed_axis = "yaxis" + axis["speed"][1:]
        layout[speed_axis]["range"] = [0, float(max(level * 4, np.nanpercentile(trial["velocity"], 99)))]
    if "events" in data:
        marks = data["events"]
        marks = marks[(marks["participant"] == key[0]) & (marks["time"] >= start + lo) & (marks["time"] <= start + hi)].head(40)
        for when, text in zip(marks["time"] - start, marks["label"]):
            shapes.append(dict(type="line", xref="x", x0=when, x1=when, yref="paper", y0=0, y1=1, line=dict(color=C["marker"], width=1, dash="dot")))
            notes.append(dict(x=when, xref="x", yref="paper", y=1, yanchor="bottom", text=str(text)[:24], showarrow=False, textangle=-25, font=dict(size=10, color=C["marker"])))
    layout.update(xaxis=dict(title=dict(text="Time since trial start (ms)"), range=[lo, hi], anchor=axis[panels[-1][0]]), shapes=shapes, annotations=notes,
                  hovermode="x unified", legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0))
    return dict(data=traces, layout=layout, info=dict(title=label(key), thinned=thinned, zoomable=True,
                                                      hint="Drag to zoom into a moment; double-click to zoom out." if thinned else ""))


# ----------------------------------------------------------------------------- gaze in space

def stage(data, trial):
    """Axes that match the screen (y grows downward) and the stimulus image behind them, if there is one."""
    width, height = data.meta["width_px"], data.meta["height_px"]
    shown = trial["stimulus"].dropna().iloc[0] if "stimulus" in trial and trial["stimulus"].notna().any() else None
    name = match_stimulus(data.meta.get("stimuli", {}), shown)
    layout = dict(xaxis=dict(range=[0, width], title=dict(text="x (px)"), constrain="domain", zeroline=False),
                  yaxis=dict(range=[height, 0], title=dict(text="y (px)"), scaleanchor="x", constrain="domain", zeroline=False),
                  shapes=[dict(type="rect", x0=0, y0=0, x1=width, y1=height, line=dict(color="#94a3b8", width=1), layer="below")],
                  annotations=[], hovermode="closest", legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0))
    if name:
        # “contain”: the image keeps its proportions and sits in the middle of the screen, as WebGazer experiments show it
        placed = dict(x=width / 2, y=height / 2, xanchor="center", yanchor="middle", sizing="contain") if data.meta.get("stimulus_fit") == "contain" \
            else dict(x=0, y=0, xanchor="left", yanchor="top", sizing="stretch")
        layout["images"] = [dict(source=stimulus_url(data.meta["dataset"], name), xref="x", yref="y", sizex=width, sizey=height,
                                 layer="below", opacity=0.85, **placed)]
    if "aois" in data and "w" in data["aois"]:
        for i, area in enumerate(data["aois"].to_dict("records")):
            if area.get("stimulus") and stimulus_key(area["stimulus"]) != stimulus_key(shown):
                continue
            colour = AREAS[list(dict.fromkeys(data["aois"]["name"])).index(area["name"]) % len(AREAS)]
            layout["shapes"].append(dict(type="circle" if area["shape"] == "ellipse" else "rect", x0=area["x"], y0=area["y"], x1=area["x"] + area["w"],
                                         y1=area["y"] + area["h"], line=dict(color=colour, width=2), fillcolor=colour, opacity=0.18))
            layout["shapes"].append(dict(type="circle" if area["shape"] == "ellipse" else "rect", x0=area["x"], y0=area["y"], x1=area["x"] + area["w"],
                                         y1=area["y"] + area["h"], line=dict(color=colour, width=2)))
            layout["annotations"].append(dict(x=area["x"] + area["w"] / 2, y=area["y"], yanchor="bottom", text=f"<b>{area['name']}</b>", showarrow=False,
                                              font=dict(size=11, color=colour), bgcolor="rgba(255,255,255,0.8)"))
    return layout, shown


@view("gaze", "Gaze on the stimulus", compares=True)
def gaze(data, sel, before=None):
    key, trial = pick(data, sel)
    layout, shown = stage(data, trial)
    stride = max(1, len(trial) // MAX_POINTS)
    traces = []
    if before is not None and before.samples is not data.samples:  # what this step received, drawn underneath in grey
        groups = trials(before.samples)
        if key in groups:
            old = before.samples.iloc[groups[key]]
            traces.append(dict(type="scatter", mode="lines+markers", x=numbers(old["x"].to_numpy()[::stride]), y=numbers(old["y"].to_numpy()[::stride]),
                               name="before this step", line=dict(color=C["before"], width=0.8), marker=dict(size=3, color=C["before"]), hoverinfo="skip"))
    traces += [dict(type="scatter", mode="lines+markers", x=numbers(trial["x"].to_numpy()[::stride]), y=numbers(trial["y"].to_numpy()[::stride]), name="gaze samples",
                   line=dict(color=C["path"], width=0.8), marker=dict(size=3, color=C["path"]), opacity=0.55, hoverinfo="skip")]
    if "fixations" in data:
        fixations = own(data["fixations"], key)
        names = list(dict.fromkeys(data["aois"]["name"])) if "aois" in data else []
        area = fixations["aoi"].tolist() if "aoi" in fixations else [""] * len(fixations)
        colours = [AREAS[names.index(a) % len(AREAS)] if a in names else C["fixation"] for a in area]
        traces.append(dict(type="scatter", mode="lines", x=numbers(fixations["x"]), y=numbers(fixations["y"]), name="scanpath", hoverinfo="skip",
                           line=dict(color=C["fixation"], width=1, dash="dot")))
        traces.append(dict(type="scatter", mode="markers+text" if len(fixations) <= 60 else "markers", x=numbers(fixations["x"]), y=numbers(fixations["y"]),
                           name="fixations (size = duration)", text=[str(n) for n in fixations["fixation"]], textfont=dict(size=9, color="#ffffff"),
                           customdata=[[round(float(d)), round(float(s)), a or "none"] for d, s, a in zip(fixations["duration"], fixations["start"], area)],
                           hovertemplate="fixation %{text}<br>%{customdata[0]} ms, starting at %{customdata[1]} ms<br>area: %{customdata[2]}<extra></extra>",
                           marker=dict(size=[float(np.clip(np.sqrt(d) * 1.5, 7, 60)) for d in fixations["duration"]], color=colours, opacity=0.8,
                                       line=dict(color="#ffffff", width=1))))
    title = label(key) + (f" · {shown}" if shown else "")
    return dict(data=traces, layout=layout, info=dict(title=title))


@view("heatmap", "Heatmap", single_trial=False)
def heatmap(data, sel, before=None):
    key, trial = pick(data, sel)
    layout, shown = stage(data, trial)
    rows = select(data.samples, sel)
    if shown is not None and "stimulus" in rows:
        rows = rows[rows["stimulus"] == shown]
    width, height, cell = data.meta["width_px"], data.meta["height_px"], max(8, data.meta["width_px"] // 160)
    valid = rows[rows["x"].notna() & rows["y"].notna()]
    grid, _, _ = np.histogram2d(valid["y"], valid["x"], bins=[height // cell, width // cell], range=[[0, height], [0, width]])
    blur = gaussian_filter(grid, sigma=max(1.5, data.meta.get("px_per_deg", 40) / cell))  # about one degree of visual angle
    scaled = blur / blur.max() if blur.max() > 0 else blur
    scale = [[0, "rgba(37,99,235,0)"], [0.08, "rgba(37,99,235,0.35)"], [0.35, "rgba(16,185,129,0.6)"], [0.65, "rgba(250,204,21,0.75)"], [1, "rgba(220,38,38,0.85)"]]
    trace = dict(type="heatmap", z=np.round(scaled, 3).tolist(), x0=cell / 2, dx=cell, y0=cell / 2, dy=cell, colorscale=scale, zmin=0, zmax=1,
                 zsmooth="best", showscale=False, hoverinfo="skip")
    who = f"{rows['participant'].nunique()} participant(s), {rows.groupby(KEYS).ngroups} trial(s)"
    return dict(data=[trace], layout=layout, info=dict(title=who + (f" · {shown}" if shown else ""),
                                                       hint="Colour shows where gaze samples accumulate, blurred by about one degree. Choose “All” participants to pool people."))


# ----------------------------------------------------------------------------- summaries

@view("durations", "Fixation durations", needs=("fixations",), single_trial=False, compares=True)
def durations(data, sel, before=None):
    rows = select(data["fixations"], sel)
    if rows.empty:
        return empty("No fixations in this selection.")
    traces = []
    if before is not None and "fixations" in before and before["fixations"] is not data["fixations"]:
        traces.append(dict(type="histogram", x=numbers(select(before["fixations"], sel)["duration"]), xbins=dict(start=0, size=25), name="before this step",
                           marker=dict(color=C["before"]), opacity=0.6))
    traces.append(dict(type="histogram", x=numbers(rows["duration"]), xbins=dict(start=0, size=25), name="fixations", marker=dict(color=C["fixation"]), opacity=0.85))
    median = float(rows["duration"].median())
    layout = dict(barmode="overlay", xaxis=dict(title=dict(text="Fixation duration (ms)"), range=[0, float(rows["duration"].quantile(0.99)) * 1.1]),
                  yaxis=dict(title=dict(text="Number of fixations")), legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0),
                  shapes=[dict(type="line", x0=median, x1=median, yref="paper", y0=0, y1=1, line=dict(color="#0f172a", width=1, dash="dash"))],
                  annotations=[dict(x=median, yref="paper", y=1, yanchor="bottom", text=f"median {median:.0f} ms", showarrow=False, font=dict(size=11))])
    return dict(data=traces, layout=layout, info=dict(title=f"{num(len(rows))} fixations"))


@view("aoi_bars", "Dwell time per area", needs=("aoi_metrics",), single_trial=False)
def aoi_bars(data, sel, before=None):
    rows = select(data["aoi_metrics"], sel)
    if rows.empty:
        return empty("No AOI measures in this selection.")
    split = "condition" if "condition" in rows and rows["condition"].notna().any() else None
    per_person = rows.groupby(["participant", "aoi"] + ([split] if split else []), sort=False)["dwell_ms"].mean().reset_index()
    traces = []
    for i, (level, part) in enumerate(per_person.groupby(split, sort=False) if split else [("all trials", per_person)]):
        stats = part.groupby("aoi", sort=False)["dwell_ms"].agg(["mean", "sem"]).reset_index()
        traces.append(dict(type="bar", x=stats["aoi"].tolist(), y=numbers(stats["mean"]), name=str(level), marker=dict(color=AREAS[i % len(AREAS)]),
                           error_y=dict(type="data", array=numbers(stats["sem"].fillna(0)), thickness=1, width=3, color="#334155")))
    layout = dict(barmode="group", xaxis=dict(title=dict(text="Area of interest")), yaxis=dict(title=dict(text="Mean dwell time per trial (ms)")),
                  legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0))
    return dict(data=traces, layout=layout, info=dict(title=f"{rows['participant'].nunique()} participant(s)",
                                                      hint="Bars are means of participants' means; whiskers show ±1 standard error between participants."))


@view("transition_matrix", "Transition matrix", needs=("transitions",), single_trial=False)
def transition_matrix(data, sel, before=None):
    rows = select(data["transitions"], sel)
    if rows.empty or not rows["count"].sum():
        return empty("No transitions in this selection.")
    order = list(dict.fromkeys(rows["source"]))
    matrix = rows.groupby(["source", "target"], sort=False)["count"].sum().unstack("target").reindex(index=order, columns=order)
    z = [[None if pd.isna(v) else int(v) for v in line] for line in matrix.to_numpy()]
    trace = dict(type="heatmap", z=z, x=order, y=order, colorscale=[[0, "#f8fafc"], [1, "#1d4ed8"]], texttemplate="%{z}", hoverongaps=False,
                 hovertemplate="from %{y} to %{x}: %{z}<extra></extra>", colorbar=dict(title=dict(text="count"), thickness=12))
    layout = dict(xaxis=dict(title=dict(text="to"), side="top"), yaxis=dict(title=dict(text="from"), autorange="reversed"))
    return dict(data=[trace], layout=layout, info=dict(title=f"{num(int(rows['count'].sum()))} transitions", hint="Read a row as: from this area, where did gaze go next?"))


@view("pattern_bars", "Most common patterns", needs=("patterns",), single_trial=False)
def pattern_bars(data, sel, before=None):
    rows = select(data["patterns"], sel)
    if rows.empty:
        return empty("No patterns in this selection.")
    split = "condition" if "condition" in rows and rows["condition"].notna().any() else None
    top = rows.groupby("pattern")["count"].sum().nlargest(15).index.tolist()[::-1]
    traces = []
    for i, (level, part) in enumerate(rows.groupby(split, sort=False) if split else [("all trials", rows)]):
        totals = part.groupby("pattern")["count"].sum().reindex(top).fillna(0)
        traces.append(dict(type="bar", orientation="h", y=top, x=[int(v) for v in totals], name=str(level), marker=dict(color=AREAS[i % len(AREAS)])))
    layout = dict(barmode="stack", xaxis=dict(title=dict(text="Occurrences")), yaxis=dict(automargin=True), legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0))
    return dict(data=traces, layout=layout, info=dict(title=f"{rows['pattern'].nunique()} different patterns"))
