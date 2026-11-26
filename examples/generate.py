"""Generate the example datasets and example pipelines.

    python examples/generate.py

Everything here is SYNTHETIC and deterministic (fixed random seed). The eye
movements are simulated from a simple but realistic model: fixations of
log-normal duration, saccades whose duration grows with their size, tracker
noise, blinks with distorted edges, lost tracking, and a pupil that reacts to
task difficulty. Because the true fixations are known, students can check how
well a pipeline recovers them (see truth/ in each dataset).

The files imitate real export formats so that the same pipelines work on real
recordings:

    visual-search/   a plain CSV, as from any screen-based tracker
    glasses-shelf/   Tobii Pro Lab data export (TSV) of Tobii Pro Glasses 2
    glasses-raw/     livedata.json.gz as found on a Glasses 2 SD card
    four-faces/      a plain CSV of a free-viewing task with four pictures per screen
"""
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
DATA, PIPELINES = HERE / "datasets", HERE / "pipelines"
W, H = 1920, 1080


# ----------------------------------------------------------------------------- the eye model

def eye(rng, plan, rate, px_per_deg, noise_deg=0.25, start=(W / 2, H / 2)):
    """Samples for a planned sequence of fixations [(x, y, duration_ms), …].

    Returns time (ms), x, y, a per-sample code (fixation number, 0 during saccades) and the true fixations.
    """
    segments, clock, here = [], 0.0, start
    for x, y, duration in plan:
        size = np.hypot(x - here[0], y - here[1]) / px_per_deg
        if size > 0.05:
            flight = 21 + 2.2 * size  # saccade duration grows with amplitude (the "main sequence")
            segments.append((clock, clock + flight, here, (x, y), False))
            clock += flight
        segments.append((clock, clock + duration, (x, y), (x, y), True))
        clock, here = clock + duration, (x, y)
    time = np.arange(int(clock * rate / 1000)) * 1000 / rate
    gx, gy, code, truth = np.zeros(len(time)), np.zeros(len(time)), np.zeros(len(time), int), []
    for t0, t1, a, b, is_fixation in segments:
        at = (time >= t0) & (time < t1)
        if is_fixation:
            drift = np.cumsum(rng.normal(0, 0.012 * px_per_deg, (at.sum(), 2)), axis=0)  # slow wander while fixating
            gx[at], gy[at] = a[0] + drift[:, 0], a[1] + drift[:, 1]
            truth.append(dict(start=t0, end=t1, duration=t1 - t0, x=a[0], y=a[1]))
            code[at] = len(truth)
        else:
            s = (time[at] - t0) / (t1 - t0)
            s = 10 * s**3 - 15 * s**4 + 6 * s**5  # smooth acceleration and braking
            gx[at], gy[at] = a[0] + s * (b[0] - a[0]), a[1] + s * (b[1] - a[1])
    noise = rng.normal(0, noise_deg * px_per_deg, (len(time), 2))
    return time, gx + noise[:, 0], gy + noise[:, 1], code, truth


def pupil_size(rng, time, base, effort):
    """Pupil diameter (mm): a slow drift plus a dilation that peaks ~1.2 s after trial start and scales with effort."""
    s = time / 1200
    response = np.where(s > 0, s**10.1 * np.exp(-10.1 * (s - 1)), 0)
    drift = 0.05 * np.sin(2 * np.pi * (time / 9000 + rng.uniform()))
    return base + drift + effort * response + rng.normal(0, 0.015, len(time))


def lose_signal(rng, time, x, y, pupil, blinks_per_s=0.22, loss_chance=0.06, dropout=0.004):
    """Blinks (with distorted samples around them), occasional long losses and single dropped samples."""
    x, y, pupil, lost = x.copy(), y.copy(), pupil.copy(), np.zeros(len(time), bool)
    clock, blinks = rng.exponential(1 / blinks_per_s) * 1000 + 300, []
    while clock < time[-1] - 400:
        length = rng.uniform(110, 280)
        closing = (time >= clock - 45) & (time < clock)          # the lid slides over the pupil…
        opening = (time >= clock + length) & (time < clock + length + 60)
        for edge, depth in ((closing, np.linspace(0.1, 0.55, closing.sum())), (opening, np.linspace(0.5, 0.05, opening.sum()))):
            pupil[edge] *= 1 - depth                              # …so the pupil seems to shrink
            y[edge] += depth * 140                                # …and the gaze seems to dive
        lost |= (time >= clock) & (time < clock + length)
        blinks.append((clock, clock + length))
        clock += length + rng.exponential(1 / blinks_per_s) * 1000 + 400
    if rng.uniform() < loss_chance and time[-1] > 2500:
        begin = rng.uniform(600, time[-1] - 1500)
        lost |= (time >= begin) & (time < begin + rng.uniform(600, 1300))
    lost |= rng.uniform(size=len(time)) < dropout
    x[lost], y[lost], pupil[lost] = np.nan, np.nan, np.nan
    return x, y, pupil, lost, blinks


def duration(rng, median=230, minimum=90):
    return max(minimum, rng.lognormal(np.log(median), 0.35))


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow
        return ImageFont.load_default()


# ----------------------------------------------------------------------------- 1 · visual search on a screen

SCREEN_PPD = W / (2 * np.degrees(np.arctan(53 / 2 / 60)))  # 53 cm wide screen seen from 60 cm
BLUE, ORANGE = "#2f6fb5", "#e07b22"


def search_display(rng, hard):
    """Item positions on a jittered grid. The first item is the target (an orange disc)."""
    cells = [(c, r) for c in range(6) for r in range(4) if (c, r) not in ((2, 1), (3, 1), (2, 2), (3, 2))]
    chosen = rng.permutation(len(cells))[:22 if hard else 10]
    items = []
    for n, index in enumerate(chosen):
        c, r = cells[index]
        x, y = 160 + c * 320 + rng.uniform(-70, 70), 135 + r * 270 + rng.uniform(-60, 60)
        if n == 0:
            items.append((x, y, "disc", ORANGE))
        elif hard:  # conjunction search: the target shares a feature with every distractor
            items.append((x, y, *(("disc", BLUE) if n % 2 else ("square", ORANGE))))
        else:       # feature search: the target pops out
            items.append((x, y, "disc", BLUE))
    return items


def draw_search(items, path):
    image = Image.new("RGB", (W, H), "#eceef0")
    draw = ImageDraw.Draw(image)
    draw.line([(W / 2 - 14, H / 2), (W / 2 + 14, H / 2)], fill="#555", width=3)
    draw.line([(W / 2, H / 2 - 14), (W / 2, H / 2 + 14)], fill="#555", width=3)
    for x, y, shape, colour in items:
        box = [x - 32, y - 32, x + 32, y + 32]
        draw.ellipse(box, fill=colour) if shape == "disc" else draw.rounded_rectangle(box, radius=6, fill=colour)
    image.save(path, optimize=True)


def search_plan(rng, items, hard, speed):
    """Look at the centre, inspect some distractors (more when the search is hard), then find the target."""
    tx, ty = items[0][:2]
    plan, here = [(W / 2, H / 2, rng.uniform(260, 360))], (W / 2, H / 2)
    todo = [item[:2] for item in items[1:]]
    for _ in range(int(rng.integers(3, 10)) if hard else int(rng.integers(0, 3))):
        distance = np.array([np.hypot(x - here[0], y - here[1]) for x, y in todo])
        weights = np.exp(-distance / 350)
        here = todo.pop(int(rng.choice(len(todo), p=weights / weights.sum())))
        plan.append((here[0] + rng.normal(0, 14), here[1] + rng.normal(0, 14), duration(rng, 200 * speed)))
    plan.append((tx + rng.normal(0, 16), ty + rng.normal(0, 16), duration(rng, 240 * speed)))
    plan.append((tx + rng.normal(0, 6), ty + rng.normal(0, 6), rng.uniform(380, 620)))  # verify, then respond
    return plan


def make_visual_search(rng):
    folder = DATA / "visual-search"
    (folder / "stimuli").mkdir(parents=True, exist_ok=True)
    (folder / "truth").mkdir(exist_ok=True)
    displays = {}
    for hard in (False, True):
        for n in (1, 2, 3):
            name = f"{'hard' if hard else 'easy'}_{n}"
            displays[name] = (search_display(rng, hard), hard)
            draw_search(displays[name][0], folder / "stimuli" / f"{name}.png")
    rows, truth, rate = [], [], 120
    for p in range(1, 9):
        participant = f"P{p:02d}"
        careless = p == 6  # one participant with poor data, as in every real study
        speed, base, reactive, clock = rng.uniform(0.85, 1.2), rng.uniform(3.1, 4.3), rng.uniform(0.8, 1.25), 0.0
        order = rng.permutation([name for name in displays for _ in range(2)])
        for trial, name in enumerate(order, 1):
            items, hard = displays[name]
            time, x, y, _, fixations = eye(rng, search_plan(rng, items, hard, speed), rate, SCREEN_PPD, 0.32 if careless else rng.uniform(0.05, 0.11))
            pupil = pupil_size(rng, time, base, (0.30 if hard else 0.10) * reactive)
            x, y, pupil, _, _ = lose_signal(rng, time, x, y, pupil, 0.45 if careless else 0.2, 0.3 if careless else 0.05)
            rows.append(pd.DataFrame(dict(participant=participant, trial=trial, condition="hard" if hard else "easy", stimulus=name,
                                          time_ms=np.round(clock + time, 1), gaze_x=np.round(x, 1), gaze_y=np.round(y, 1), pupil_mm=np.round(pupil, 3))))
            truth += [dict(participant=participant, trial=trial, condition="hard" if hard else "easy", fixation=i, **{k: round(v, 1) for k, v in f.items()})
                      for i, f in enumerate(fixations, 1)]
            clock += time[-1] + rng.uniform(800, 1200)
    pd.concat(rows).to_csv(folder / "visual_search.csv", index=False)
    pd.DataFrame(truth).to_csv(folder / "truth" / "fixations.csv", index=False)
    info = dict(
        name="Visual search on a screen", provider="Generic CSV (any screen-based tracker)", synthetic=True,
        description=("8 simulated participants look for an orange disc among distractors, 12 trials each. In easy trials the target pops out; "
                     "in hard trials it shares a feature with every distractor. 120 samples per second, 1920 × 1080 screen (53 cm wide) at 60 cm. "
                     "Participant P06 has noisy data. The true fixations are in truth/fixations.csv."),
        files=[dict(name="visual_search.csv", label="visual_search")],
        stimuli={name: f"stimuli/{name}.png" for name in displays},
        defaults=dict(width_px=W, height_px=H, geometry="screen", screen_width_cm=53, distance_cm=60))
    (folder / "dataset.json").write_text(json.dumps(info, indent=2))
    areas = [dict(name="Target", shape="ellipse", x=round(items[0][0] - 85), y=round(items[0][1] - 85), w=170, h=170, stimulus=name)
             for name, (items, _) in displays.items()]
    return areas + [dict(name="Centre", shape="rect", x=W // 2 - 75, y=H // 2 - 75, w=150, h=150, stimulus="")]


# ----------------------------------------------------------------------------- 2 · glasses in front of a shelf

PRODUCTS = [("Oat flakes", 39.90, "#c98d4b"), ("Muesli", 64.90, "#7a9e58"), ("Cornflakes", 45.90, "#d9a829"),
            ("Granola", 89.90, "#8a5a44"), ("Porridge", 29.90, "#5b8fb0"), ("Bran", 52.90, "#a9744f")]
CENTRES = [(360 + 600 * c, 290 + 500 * r) for r in range(2) for c in range(3)]
SHELF_PPD = (W / 82) / 0.62      # the snapshot of the shelf fills ~62% of the scene camera's 82° view
CHEAPEST = min(range(6), key=lambda i: PRODUCTS[i][1])


def draw_shelf(path):
    image = Image.new("RGB", (W, H), "#e7e2da")
    draw = ImageDraw.Draw(image)
    for board in (560, 1060):
        draw.rectangle([0, board - 22, W, board], fill="#b9a88f")
    for (name, price, colour), (cx, cy) in zip(PRODUCTS, CENTRES):
        draw.rounded_rectangle([cx - 150, cy - 170, cx + 150, cy + 150], radius=14, fill=colour, outline="#5c5348", width=3)
        draw.rounded_rectangle([cx - 120, cy - 60, cx + 120, cy + 20], radius=8, fill="#fbf8f2")
        draw.text((cx, cy - 20), name, fill="#2b2620", font=font(34), anchor="mm")
        draw.rounded_rectangle([cx - 95, cy + 185, cx + 95, cy + 245], radius=6, fill="#fff7c2", outline="#8a7d3a", width=2)
        draw.text((cx, cy + 215), f"{price:.2f} Kč".replace(".", ","), fill="#2b2620", font=font(30), anchor="mm")
    image.save(path, optimize=True)


def on(rng, product, part="package"):
    cx, cy = CENTRES[product]
    return (cx + rng.normal(0, 45), cy - 20 + rng.normal(0, 50)) if part == "package" else (cx + rng.normal(0, 30), cy + 215 + rng.normal(0, 8))


def shelf_tasks(rng, favourites):
    """Three marked tasks with different viewing strategies, separated by looking away from the shelf."""
    away = lambda: (float(rng.choice([rng.uniform(-520, -180), rng.uniform(2100, 2440)])), rng.uniform(150, 900))  # noqa: E731
    pause = lambda seconds: [(*away(), duration(rng, 420)) for _ in range(int(seconds * 2.2))]  # noqa: E731
    free = []
    for product in rng.choice(6, size=11, p=[0.14, 0.24, 0.14, 0.16, 0.2, 0.12]):
        free += [(*on(rng, product, "price" if rng.uniform() < 0.2 else "package"), duration(rng, 260)) for _ in range(int(rng.integers(1, 4)))]
    cheapest = [(*on(rng, product, "price"), duration(rng, 300)) for product in range(6)]  # read every price in order…
    rivals = sorted(range(6), key=lambda i: PRODUCTS[i][1])[:3]
    for product in (rivals[1], rivals[0], rivals[2], rivals[0], rivals[1], rivals[0]):     # …then compare the low ones
        cheapest += [(*on(rng, product, "price"), duration(rng, 280)), (*on(rng, product), duration(rng, 200))][:int(rng.integers(1, 3))]
    cheapest.append((*on(rng, CHEAPEST, "price"), 700))
    a, b = favourites
    choice = []
    for product in (a, b, a, b, a, int(rng.integers(0, 6)), b, a):                          # weigh two favourites against each other
        choice += [(*on(rng, product), duration(rng, 300)), (*on(rng, product, "price"), duration(rng, 250)), (*on(rng, product), duration(rng, 230))][:int(rng.integers(2, 4))]
    choice.append((*on(rng, a), 800))
    return [("", pause(2.5)), ("freeview", free), ("", pause(2)), ("cheapest", cheapest), ("", pause(2)), ("choice", choice), ("", pause(1.5))]


def glasses_recording(rng, rate, favourites, tasks=None):
    """One simulated Glasses 2 recording: gaze in the scene video, gaze mapped onto the shelf snapshot, pupils, markers."""
    tasks = tasks or shelf_tasks(rng, favourites)
    plan, markers, clock = [], [], 0.0
    for name, part in tasks:
        if name:
            markers.append((clock, f"{name}_start"))
        plan += part
        clock = sum(d for *_, d in plan) + sum(21 + 2.2 * np.hypot(b[0] - a[0], b[1] - a[1]) / SHELF_PPD
                                               for a, b in zip([(W / 2, H / 2)] + plan[:-1], plan))
        if name:
            markers.append((clock - 1, f"{name}_end"))
    time, sx, sy, code, truth = eye(rng, plan, rate, SHELF_PPD, 0.18)
    pupil = pupil_size(rng, time % 12000, rng.uniform(3.2, 4.2), 0.15)
    sx, sy, pupil, lost, _ = lose_signal(rng, time, sx, sy, pupil, 0.25, 0.0, 0.006)
    head = lambda phase: 110 * np.sin(2 * np.pi * (time / 7000 + phase)) + 50 * np.sin(2 * np.pi * (time / 2300 + 2 * phase))  # noqa: E731
    hx, hy = head(rng.uniform()), 0.5 * head(rng.uniform())
    scene_x, scene_y = W / 2 + (sx - W / 2) * 0.62 + hx, H / 2 + (sy - H / 2) * 0.62 + hy
    on_shelf = (sx > -40) & (sx < W + 40) & (sy > -40) & (sy < H + 40) & (rng.uniform(size=len(time)) > 0.03)
    mapped_x = np.where(on_shelf, sx + rng.normal(0, 5, len(time)), np.nan)
    mapped_y = np.where(on_shelf, sy + rng.normal(0, 5, len(time)), np.nan)
    return dict(time=time, scene_x=scene_x, scene_y=scene_y, mapped_x=mapped_x, mapped_y=mapped_y, pupil=pupil, lost=lost, code=code,
                truth=truth, markers=markers, head=(hx, hy))


def area_box(product):
    cx, cy = CENTRES[product]
    return cx - 230, cy - 210, 460, 480


def prolab_table(rng, rec, participant):
    """Lay a recording out like a Tobii Pro Lab data export of Glasses 2: eye rows, sensor rows and marker rows interleaved."""
    n, time = len(rec["time"]), rec["time"]
    kind = np.where(rec["lost"], "EyesNotFound", np.where(rec["code"] > 0, "Fixation", "Saccade"))
    starts = np.r_[True, (kind[1:] != kind[:-1]) | (rec["code"][1:] != rec["code"][:-1])]
    run = np.cumsum(starts) - 1
    length = pd.Series(time).groupby(run).transform(lambda t: t.iloc[-1] - t.iloc[0] + 1000 / 50).to_numpy()
    index = pd.Series(run).groupby(kind).transform(lambda r: pd.factorize(r)[0] + 1).to_numpy()
    fix_x = pd.Series(rec["scene_x"]).groupby(run).transform("mean").where(kind == "Fixation").to_numpy()
    fix_y = pd.Series(rec["scene_y"]).groupby(run).transform("mean").where(kind == "Fixation").to_numpy()
    eye_rows = pd.DataFrame({
        "Recording timestamp [ms]": np.round(time).astype(int), "Sensor": "Eye Tracker",
        "Gaze point X [MCS px]": np.round(rec["scene_x"]), "Gaze point Y [MCS px]": np.round(rec["scene_y"]),
        "Pupil diameter left [mm]": np.round(rec["pupil"] + rng.normal(0.04, 0.02, n), 2),
        "Pupil diameter right [mm]": np.round(rec["pupil"] - rng.normal(0.04, 0.02, n), 2),
        "Validity left": np.where(rec["lost"], "Invalid", "Valid"), "Validity right": np.where(rec["lost"], "Invalid", "Valid"),
        "Eye movement type": kind, "Gaze event duration [ms]": np.round(length).astype(int), "Eye movement type index": index,
        "Fixation point X [MCS px]": np.round(fix_x), "Fixation point Y [MCS px]": np.round(fix_y),
        "Mapped gaze data X [Shelf]": np.round(rec["mapped_x"]), "Mapped gaze data Y [Shelf]": np.round(rec["mapped_y"]),
    })
    for product, (name, *_) in enumerate(PRODUCTS):
        x, y, w, h = area_box(product)
        hit = (rec["mapped_x"] >= x) & (rec["mapped_x"] <= x + w) & (rec["mapped_y"] >= y) & (rec["mapped_y"] <= y + h)
        eye_rows[f"AOI hit [Shelf - {name}]"] = pd.array(np.where(np.isnan(rec["mapped_x"]), pd.NA, hit.astype(int)), dtype="Int64")
    sensor_time = time[::1] + 7
    hx, hy = rec["head"]
    gyro = pd.DataFrame({"Recording timestamp [ms]": np.round(sensor_time).astype(int), "Sensor": "Gyroscope",
                         "Gyro X [°/s]": np.round(np.gradient(hy, time) * 1000 / 23.4 + rng.normal(0, 0.6, n), 2),
                         "Gyro Y [°/s]": np.round(np.gradient(hx, time) * 1000 / 23.4 + rng.normal(0, 0.6, n), 2),
                         "Gyro Z [°/s]": np.round(rng.normal(0, 0.5, n), 2)})
    accel = pd.DataFrame({"Recording timestamp [ms]": np.round(sensor_time + 5).astype(int), "Sensor": "Accelerometer",
                          "Accelerometer X [m/s²]": np.round(rng.normal(0.1, 0.05, n), 2), "Accelerometer Y [m/s²]": np.round(rng.normal(-9.78, 0.05, n), 2),
                          "Accelerometer Z [m/s²]": np.round(rng.normal(0.9, 0.05, n), 2)})
    marks = pd.DataFrame({"Recording timestamp [ms]": [0] + [round(t) for t, _ in rec["markers"]] + [round(time[-1]) + 20],
                          "Event": ["RecordingStart"] + [label for _, label in rec["markers"]] + ["RecordingEnd"]})
    table = pd.concat([eye_rows, gyro, accel, marks]).sort_values("Recording timestamp [ms]", kind="stable")
    front = {"Recording timestamp [ms]": table.pop("Recording timestamp [ms]"), "Sensor": table.pop("Sensor"), "Project name": "Shelf study",
             "Participant name": participant, "Recording name": f"Recording {participant}", "Recording resolution width [px]": W,
             "Recording resolution height [px]": H, "Event": table.pop("Event")}
    return pd.concat([pd.DataFrame(front, index=table.index), table], axis=1)


def write_livedata(rng, rec, path):
    """Lay a recording out like livedata.json.gz on the SD card of Tobii Pro Glasses 2 (one JSON packet per line)."""
    lines, base = [], 1_000_000
    markers = sorted(rec["markers"])
    for i, t in enumerate(rec["time"]):
        ts, status = base + int(t * 1000), 1 if rec["lost"][i] else 0
        while markers and markers[0][0] <= t:
            lines.append(dict(ts=ts, s=0, type="JsonEvent", tag=markers.pop(0)[1]))
        gp = [0.0, 0.0] if status else [round(rec["scene_x"][i] / W, 4), round(rec["scene_y"][i] / H, 4)]
        for side, sign in (("left", -1), ("right", 1)):
            lines.append(dict(ts=ts, s=status, gidx=i + 1, pc=[0.0, 0.0, 0.0] if status else [round(31.5 * sign + rng.normal(0, 0.05), 2), -21.4, -28.9], eye=side))
            lines.append(dict(ts=ts, s=status, gidx=i + 1, pd=0.0 if status else round(rec["pupil"][i] - 0.04 * sign + rng.normal(0, 0.01), 2), eye=side))
            lines.append(dict(ts=ts, s=status, gidx=i + 1, gd=[0.0, 0.0, 0.0] if status else [round((gp[0] - 0.5) * 1.4, 4), round((0.5 - gp[1]) * 0.9, 4), 0.95], eye=side))
        lines.append(dict(ts=ts, s=status, gidx=i + 1, l=82000 + int(rng.integers(0, 900)), gp=gp))
        lines.append(dict(ts=ts, s=status, gidx=i + 1, gp3=[0.0, 0.0, 0.0] if status else [round((gp[0] - 0.5) * 1560, 2), round((0.5 - gp[1]) * 880, 2), 900.0]))
        lines.append(dict(ts=ts + 3100, s=0, gy=[round(v, 3) for v in rng.normal(0, 0.8, 3)]))
        lines.append(dict(ts=ts + 6200, s=0, ac=[round(v, 3) for v in rng.normal([0.1, -9.78, 0.9], 0.05)]))
        if i % 4 == 0:
            lines.append(dict(ts=ts, s=0, pts=int(t * 90), pv=1))
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write("\n".join(json.dumps(line, separators=(",", ":")) for line in lines) + "\n")


def make_glasses(rng):
    shelf, raw = DATA / "glasses-shelf", DATA / "glasses-raw"
    for folder in (shelf / "stimuli", shelf / "truth", raw):
        folder.mkdir(parents=True, exist_ok=True)
    draw_shelf(shelf / "stimuli" / "Shelf.png")
    files, truth = [], []
    for p, favourites in enumerate([(1, 3), (4, 0), (1, 4), (3, 5)], 1):
        participant = f"P{p:02d}"
        rec = glasses_recording(rng, 50, favourites)
        prolab_table(rng, rec, participant).to_csv(shelf / f"shelf_{participant}.tsv", sep="\t", index=False, decimal=",", encoding="utf-8-sig")
        files.append(dict(name=f"shelf_{participant}.tsv", label=participant))
        truth += [dict(participant=participant, fixation=i, **{k: round(v, 1) for k, v in f.items()}) for i, f in enumerate(rec["truth"], 1)]
    pd.DataFrame(truth).to_csv(shelf / "truth" / "fixations_snapshot_coordinates.csv", index=False)
    (shelf / "dataset.json").write_text(json.dumps(dict(
        name="Glasses in front of a shelf (Tobii Pro Lab export)", provider="Tobii Pro Glasses 2 via Tobii Pro Lab data export", synthetic=True,
        description=("4 simulated shoppers wear Tobii Pro Glasses 2 (50 samples per second) in front of a cereal shelf and do three marked tasks: look around freely, "
                     "find the cheapest product, choose one to buy. The files are laid out like a Tobii Pro Lab data export with Czech number format (decimal commas): "
                     "eye-tracker, gyroscope and accelerometer rows interleaved, markers in the Event column, gaze mapped onto the snapshot “Shelf” and one "
                     "“AOI hit” column per product."),
        files=files, stimuli={"Shelf": "stimuli/Shelf.png"},
        defaults=dict(width_px=W, height_px=H, geometry="camera", fov_deg=82,
                      source=dict(mapping=dict(time="Recording timestamp [ms]", x="Mapped gaze data X [Shelf]", y="Mapped gaze data Y [Shelf]",
                                               pupil="Pupil diameter mean", participant="Participant name", trial="", condition="", stimulus="")))), indent=2, ensure_ascii=False))

    tasks = shelf_tasks(rng, (1, 4))[:5]
    rec = glasses_recording(rng, 100, (1, 4), tasks)
    write_livedata(rng, rec, raw / "livedata.json.gz")
    (raw / "dataset.json").write_text(json.dumps(dict(
        name="Glasses, raw from the SD card (livedata.json.gz)", provider="Tobii Pro Glasses 2, raw recording", synthetic=True,
        description=("One simulated Glasses 2 recording at 100 samples per second in the raw format the recording unit writes to its SD card: one JSON packet per line "
                     "for gaze position, gaze direction, pupil diameter, gyroscope and accelerometer, plus two marked tasks. Gaze is in scene-video coordinates, "
                     "which move with the head; there is no stimulus image."),
        files=[dict(name="livedata.json.gz", label="P01")], stimuli={},
        defaults=dict(width_px=W, height_px=H, geometry="camera", fov_deg=82)), indent=2, ensure_ascii=False))


# ----------------------------------------------------------------------------- 3 · four faces on a screen

EMOTIONS = ("Angry", "Sad", "Happy", "Neutral")
QUADRANTS = [(480, 290), (1440, 290), (480, 790), (1440, 790)]
TILE = (560, 400)   # width and height of each picture
FIRST_LOOK = dict(Angry=0.64, Sad=0.08, Happy=0.16, Neutral=0.12)   # vigilance: the threatening face captures the first look…
LATER_LOOK = dict(Angry=0.07, Sad=0.22, Happy=0.45, Neutral=0.26)   # …and is avoided afterwards


def draw_face(draw, cx, cy, emotion):
    ink = "#2b2620"
    draw.ellipse([cx - 120, cy - 120, cx + 120, cy + 120], fill="#f1d9a7", outline=ink, width=5)
    for side in (-1, 1):
        draw.ellipse([cx + side * 45 - 13, cy - 38, cx + side * 45 + 13, cy - 12], fill=ink)
        inner, outer = dict(Angry=(-52, -78), Sad=(-76, -56), Happy=(-66, -66), Neutral=(-62, -62))[emotion]
        draw.line([(cx + side * 22, cy + inner), (cx + side * 72, cy + outer)], fill=ink, width=7)
    if emotion == "Happy":
        draw.arc([cx - 62, cy - 10, cx + 62, cy + 78], 20, 160, fill=ink, width=7)
    elif emotion == "Neutral":
        draw.line([(cx - 48, cy + 55), (cx + 48, cy + 55)], fill=ink, width=7)
    else:
        draw.arc([cx - 56, cy + 38, cx + 56, cy + 112], 200, 340, fill=ink, width=7)
        if emotion == "Sad":
            draw.ellipse([cx + 62, cy - 4, cx + 76, cy + 22], fill="#5b8fb0")


def draw_faces(layout, path):
    image = Image.new("RGB", (W, H), "#eceef0")
    draw = ImageDraw.Draw(image)
    for emotion, (cx, cy) in zip(layout, QUADRANTS):
        draw.rounded_rectangle([cx - TILE[0] / 2, cy - TILE[1] / 2, cx + TILE[0] / 2, cy + TILE[1] / 2], radius=18, fill="#fbf8f2", outline="#b9b4aa", width=3)
        draw_face(draw, cx, cy, emotion)
    draw.line([(W / 2 - 14, H / 2), (W / 2 + 14, H / 2)], fill="#555", width=3)
    draw.line([(W / 2, H / 2 - 14), (W / 2, H / 2 + 14)], fill="#555", width=3)
    image.save(path, optimize=True)


def faces_plan(rng, layout, speed, length=6000, distracted=False):
    """Start at the centre, let one face capture the first look, then wander with changing preferences.

    A distracted participant now and then glances below the screen, at the keyboard.
    """
    where = dict(zip(layout, QUADRANTS))
    spot = lambda emotion: (where[emotion][0] + rng.normal(0, 75), where[emotion][1] + rng.normal(0, 60))  # noqa: E731
    plan, clock = [(W / 2, H / 2, rng.uniform(220, 330))], 300.0
    current = str(rng.choice(EMOTIONS, p=[FIRST_LOOK[e] for e in EMOTIONS]))
    while clock < length + 400:
        stay = duration(rng, 250 * speed)
        plan.append((*spot(current), stay))
        clock += stay + 45
        if distracted and clock > 1500 and rng.uniform() < 0.07:
            glance = rng.uniform(280, 520)
            plan.append((rng.uniform(700, 1250), rng.uniform(1170, 1330), glance))
            clock += glance + 60
        if rng.uniform() > 0.62:   # move on to another face
            others = [e for e in EMOTIONS if e != current]
            weights = np.array([(FIRST_LOOK if clock < 700 else LATER_LOOK)[e] for e in others])
            current = str(rng.choice(others, p=weights / weights.sum()))
    return plan


def make_faces(rng):
    folder = DATA / "four-faces"
    (folder / "stimuli").mkdir(parents=True, exist_ok=True)
    (folder / "truth").mkdir(exist_ok=True)
    layouts = {f"set_{n}": [str(e) for e in rng.permutation(EMOTIONS)] for n in range(1, 9)}
    for name, layout in layouts.items():
        draw_faces(layout, folder / "stimuli" / f"{name}.png")
    rows, truth, rate, length = [], [], 60, 6000
    for p in range(1, 11):
        participant = f"P{p:02d}"
        speed, base, clock = rng.uniform(0.85, 1.2), rng.uniform(3.1, 4.3), 0.0
        for trial, name in enumerate(rng.permutation(list(layouts)), 1):
            time, x, y, _, fixations = eye(rng, faces_plan(rng, layouts[name], speed, length, distracted=p == 7), rate, SCREEN_PPD, rng.uniform(0.08, 0.16))
            keep = time < length
            time, x, y = time[keep], x[keep], y[keep]
            pupil = pupil_size(rng, time, base, 0.08)
            x, y, pupil, _, _ = lose_signal(rng, time, x, y, pupil, 0.2, 0.04)
            rows.append(pd.DataFrame(dict(participant=participant, trial=trial, stimulus=name, time_ms=np.round(clock + time, 1),
                                          gaze_x=np.round(x, 1), gaze_y=np.round(y, 1), pupil_mm=np.round(pupil, 3))))
            truth += [dict(participant=participant, trial=trial, stimulus=name, fixation=i, **{k: round(v, 1) for k, v in f.items()})
                      for i, f in enumerate(fixations, 1) if f["start"] < length]
            clock += length + rng.uniform(900, 1300)
    pd.concat(rows).to_csv(folder / "four_faces.csv", index=False)
    pd.DataFrame(truth).to_csv(folder / "truth" / "fixations.csv", index=False)
    (folder / "dataset.json").write_text(json.dumps(dict(
        name="Four faces on a screen (free viewing)", provider="Generic CSV (any screen-based tracker)", synthetic=True,
        description=("10 simulated participants look freely at four schematic faces (angry, sad, happy, neutral) for 6 seconds, 8 screens each; "
                     "the faces change places from screen to screen. 60 samples per second, 1920 × 1080 screen (53 cm wide) at 60 cm. "
                     "Participant P07 sometimes glances below the screen. The true fixations are in truth/fixations.csv."),
        files=[dict(name="four_faces.csv", label="four_faces")],
        stimuli={name: f"stimuli/{name}.png" for name in layouts},
        defaults=dict(width_px=W, height_px=H, geometry="screen", screen_width_cm=53, distance_cm=60)), indent=2))
    return [dict(name=emotion, shape="rect", x=round(cx - TILE[0] / 2), y=round(cy - TILE[1] / 2), w=TILE[0], h=TILE[1], stimulus=name)
            for name, layout in layouts.items() for emotion, (cx, cy) in zip(layout, QUADRANTS)]


# ----------------------------------------------------------------------------- example pipelines

def pipeline(name, title, description, dataset, steps, tasks, branches=()):
    """steps: [(kind, settings)] in a chain; branches: [(index of the step to branch from, [(kind, settings)])]."""
    nodes = [dict(id=f"s{i + 1}", kind=kind, params=params) for i, (kind, params) in enumerate(steps)]
    edges = [dict(source=a["id"], target=b["id"]) for a, b in zip(nodes, nodes[1:])]
    for b, (origin, extra) in enumerate(branches, 1):
        previous = nodes[origin]["id"]
        for i, (kind, params) in enumerate(extra, 1):
            nodes.append(dict(id=f"b{b}{i}", kind=kind, params=params))
            edges.append(dict(source=previous, target=nodes[-1]["id"]))
            previous = nodes[-1]["id"]
    PIPELINES.mkdir(exist_ok=True)
    (PIPELINES / f"{name}.json").write_text(json.dumps(dict(name=title, description=description, dataset=dataset, tasks=tasks,
                                                            graph=dict(nodes=nodes, edges=edges)), indent=2, ensure_ascii=False))


def make_pipelines(areas, face_areas):
    search = ("load", dict(source=dict(dataset="visual-search"), width_px=W, height_px=H, geometry="screen", screen_width_cm=53, distance_cm=60))
    clean = [("blinks", dict(margin_ms=50)), ("interpolate", dict(max_gap_ms=75))]
    pipeline("01-samples-to-fixations", "From samples to fixations",
             "What the tracker records, what a blink does to it, and how two classic algorithms turn samples into fixations and saccades.",
             "visual-search", [search, *clean, ("fixations_ivt", dict(threshold=30)), ("saccades", {})],
             ["Select “Load recording”. Compare “File as read” with “Output” (standard columns). What is one row?",
              "Select “Detect and remove blinks”. In the signal view, zoom into a red bar. What happens to the pupil just before the gap?",
              "Select the I-VT step. Change the speed threshold from 30 to 10 and to 100 °/s. Watch the fixation count on the card.",
              "Two branches detect fixations in different ways. Compare their counts and the “Fixation durations” view. Why do they differ?",
              "Select “Detect saccades” and open the Saccades table. Sort it by amplitude_deg. Does peak_velocity rise with it?",
              "Open “Do this step in your own Python script” on any detection step. Which lines would you change for a different tracker?",
              "Participant P06 has poor data. Choose P06 in the data panel. Which steps cope well, and which do not?"],
             branches=[(2, [("fixations_idt", dict(dispersion=1.0, min_duration_ms=100))])])
    pipeline("02-search-difficulty", "Is a hard search slower? (AOI measures)",
             "Draw an area around the target, measure time to first fixation, and build the table for a paired t-test.",
             "visual-search", [search, *clean, ("fixations_ivt", dict(threshold=30)), ("aoi_draw", dict(aois=areas)), ("aoi_metrics", {}),
                               ("aggregate", dict(table="aoi_metrics", by=["participant", "condition", "aoi"], stat="mean", layout="long"))],
             ["Select “Draw areas of interest” and open the editor. Each stimulus has its own Target area. Why not one area for all?",
              "Select “Measure attention per area”. Which measure captures how quickly the target was found?",
              "In the last step, switch the layout to Wide. What is one row now? Download the CSV.",
              "Open the CSV in JASP or jamovi and run a paired t-test on first_fixation_ms for Target, easy against hard.",
              "Go back and enlarge every Target area by 40 px. Does the conclusion change?"])
    pipeline("03-pupil-and-effort", "Does effort show in the pupil?",
             "Clean a pupil trace step by step and compare easy with hard trials.",
             "visual-search", [search, ("blinks", dict(margin_ms=80)), ("interpolate", dict(max_gap_ms=400, channels="pupil")),
                               ("baseline", dict(start_ms=0, end_ms=200)),
                               ("trial_summary", {}), ("aggregate", dict(table="trial_summary", by=["participant", "condition"], stat="mean", layout="wide"))],
             ["Select “Detect and remove blinks” and switch on “Show input in grey”. How far around a blink is the pupil distorted?",
              "Select “Fill short gaps”. The limit is 400 ms here, far more than for gaze. Why is that acceptable for the pupil but not for gaze position?",
              "Select “Baseline-correct pupil”. Move the baseline to 400–600 ms. What happens to the difference between conditions?",
              "In the final table, compare pupil_mean for easy and hard. Then ask: hard trials also last longer. Is this a fair comparison?"])
    shelf_load = ("load", dict(source=dict(dataset="glasses-shelf", reader="tobii_prolab",
                                           mapping=dict(time="Recording timestamp [ms]", x="Mapped gaze data X [Shelf]", y="Mapped gaze data Y [Shelf]",
                                                        pupil="Pupil diameter mean", participant="Participant name"),
                                           extra=[f"AOI hit [Shelf - {name}]" for name, *_ in PRODUCTS] + ["Eye movement type", "Eye movement type index"]),
                               width_px=W, height_px=H, geometry="camera", fov_deg=82))
    shelf = [shelf_load, ("trials_from_events", dict(start="*_start", end="*_end")), ("interpolate", dict(max_gap_ms=75, channels="gaze")),
             ("fixations_ivt", dict(threshold=50, min_duration_ms=60)), ("aoi_columns", {}), ("aoi_metrics", {}),
             ("aggregate", dict(table="aoi_metrics", by=["condition", "aoi"], stat="mean", layout="long"))]
    pipeline("04-glasses-shelf", "Glasses: which product gets attention?",
             "A Tobii Pro Lab export of Glasses 2: cut tasks from markers, use mapped gaze and AOI hits, and find comparison patterns.",
             "glasses-shelf", shelf,
             ["Select “Load recording” and open “File as read”. The export mixed eye, gyroscope and marker rows. Under “What this step did”, see where each kind went.",
              "Gaze here is “mapped gaze” on the shelf snapshot, not gaze in the moving scene video. Why does that matter for areas of interest, and why are degrees only approximate here?",
              "Select “Cut trials from markers”. The three tasks become trials and conditions. What happened to the samples between tasks?",
              "Select “Find viewing patterns”. Which pattern dominates in the choice task? What does it say about how people decide?",
              "Add “Use the tracker's own fixations” as a new branch after “Fill short gaps” and compare it with I-VT."],
             branches=[(4, [("aoi_patterns", dict(length=3)), ("aggregate", dict(table="patterns", by=["condition", "pattern"], stat="sum", layout="long"))]),
                       (4, [("aoi_transitions", {})])])
    pipeline("05-glasses-raw", "Glasses: straight from the SD card",
             "Read livedata.json.gz without any Tobii software and get from raw packets to fixations per task.",
             "glasses-raw", [("load", dict(source=dict(dataset="glasses-raw"), width_px=W, height_px=H, geometry="camera", fov_deg=82)),
                             ("trials_from_events", dict(start="*_start", end="*_end")), ("blinks", dict(margin_ms=40)),
                             ("interpolate", dict(max_gap_ms=75)), ("fixations_ivt", dict(threshold=100)), ("trial_summary", {})],
             ["Select “Load recording” and open “File as read”. Each row was assembled from several packets. Which columns come from which packet type?",
              "The gaze view has no picture: gaze is in scene-video coordinates and the video is not loaded. What can and cannot be concluded from positions?",
              "The I-VT threshold is 100 °/s here instead of 30. Lower it to 30. What happens, and why is head movement the reason?",
              "Compare fixation_mean_ms between the two tasks in the trial summary."])
    faces = [("load", dict(source=dict(dataset="four-faces"), width_px=W, height_px=H, geometry="screen", screen_width_cm=53, distance_cm=60)),
             ("offscreen", dict(margin_px=50)), *clean]
    measure = [("fixations_ivt", dict(threshold=30)), ("aoi_draw", dict(aois=face_areas)), ("aoi_metrics", {})]
    per_face = dict(table="aoi_metrics", by=["participant", "aoi"], stat="mean")
    pipeline("06-four-faces", "Four faces: first look and lasting look",
             "A free-viewing task with four pictures per screen: which face is looked at first, which one longest, and how that changes within a trial.",
             "four-faces", [*faces, *measure, ("aggregate", dict(**per_face, layout="long"))],
             ["Select “Remove off-screen gaze” and choose participant P07. Where was this person looking, and is that a measurement error or behaviour?",
              "Select “Draw areas of interest” and open the editor. The faces change places between screens. What would go wrong with one fixed set of areas?",
              "Select “Measure attention per area”. Which column tells you where gaze went first, and which one where it stayed longest?",
              "In “Build a table for statistics”, which face has the shortest first_fixation_ms, and which the largest dwell_pct? Are they the same face?",
              "The branch “Trim trials in time” keeps only the time after 3 seconds. Compare its final table with the main one. What changed for the angry face?",
              "Select “Count transitions between areas”. From the angry face, where does gaze go next most often?",
              "Switch the last step to Wide and download the CSV. Which test compares dwell_pct for Angry and Happy within participants?",
              "Shrink every area to the face itself (the circle). Which measures change, and which conclusions survive?"],
             branches=[(3, [("crop", dict(start_ms=3000, end_ms=0)), *measure, ("aggregate", dict(**per_face, layout="long"))]),
                       (5, [("aoi_transitions", {})])])


if __name__ == "__main__":
    rng = np.random.default_rng(2026)
    areas = make_visual_search(rng)
    make_glasses(rng)
    face_areas = make_faces(rng)   # after the others, so that their files stay exactly as they were
    make_pipelines(areas, face_areas)
    for path in sorted(DATA.rglob("*")):
        if path.is_file():
            print(f"{path.stat().st_size / 1024:8.0f} kB  {path.relative_to(HERE)}")
