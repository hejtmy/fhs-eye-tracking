"""Vytvoří přílohy k pracovním listům (data, obrázky k tisku, podklady pro klíč).

    .venv/bin/python vyuka/prilohy/vytvor_prilohy.py

Vše vychází ze SIMULOVANÝCH ukázkových dat Gaze Lab (examples/datasets), takže čísla
v pracovních listech odpovídají tomu, co studenti uvidí v aplikaci. Soubory *_excel.csv
mají středníky a desetinné čárky (otevřou se dvojklikem v českém Excelu), ostatní CSV
jsou standardní (jamovi, JASP).
"""
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from gazelab import Context, Library, Runner  # noqa: E402

EXAMPLES = ROOT / "examples"
spec = importlib.util.spec_from_file_location("generate", EXAMPLES / "generate.py")
generate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate)

PPD = generate.SCREEN_PPD            # pixelů na stupeň: obrazovka 53 cm ze 60 cm
LETTER = dict(Angry="Z", Sad="S", Happy="V", Neutral="N")   # zlostný, smutný, veselý, neutrální
CZ = dict(Angry="zlostný", Sad="smutný", Happy="veselý", Neutral="neutrální")
key = {}


def excel(frame, name):
    frame.to_csv(HERE / name, index=False, sep=";", decimal=",", encoding="utf-8-sig")


def font(size):
    return ImageFont.load_default(size=size)


def run(pipeline):
    runner = Runner(Context(Library(examples=EXAMPLES / "datasets")))
    return runner.run(json.loads((EXAMPLES / "pipelines" / f"{pipeline}.json").read_text())["graph"])


# ---------------------------------------------------------------- PL 3: surová data pro Excel
faces = pd.read_csv(EXAMPLES / "datasets" / "four-faces" / "four_faces.csv")
raw = faces[(faces.participant == "P07") & (faces.trial <= 3)].reset_index(drop=True)
excel(raw, "surova_data_excel.csv")
off = (raw.gaze_x < 0) | (raw.gaze_x > 1920) | (raw.gaze_y < 0) | (raw.gaze_y > 1080)
key["surova_data"] = dict(radku=len(raw), chybi=int(raw.gaze_x.isna().sum()), chybi_pct=round(100 * raw.gaze_x.isna().mean(), 1),
                          mimo=int(off.sum()), mimo_pct=round(100 * off.mean(), 1),
                          mimo_po_pokusech={int(k): int(v) for k, v in off.groupby(raw.trial).sum().items()},
                          chybi_po_pokusech={int(k): int(v) for k, v in raw.gaze_x.isna().groupby(raw.trial).sum().items()},
                          krok_ms=round(float(raw[raw.trial == 1].time_ms.diff().median()), 1))

# ---------------------------------------------------------------- PL 4: I-VT ručně
one = faces[(faces.participant == "P01") & (faces.trial == 1)].reset_index(drop=True)
step = np.hypot(one.gaze_x.diff(), one.gaze_y.diff())
speed = step / PPD * 60
fast = (speed > 30).to_numpy()
# okno 30 vzorků, které obsahuje dvě sakády a žádný chybějící vzorek
best = None
for start in range(5, len(one) - 30):
    w = slice(start, start + 30)
    runs = np.flatnonzero(np.diff(np.r_[0, fast[w].astype(int), 0]) == 1)
    if one.gaze_x[w].notna().all() and len(runs) == 2 and not fast[start] and not fast[start + 29] and 8 <= runs[0] and runs[1] - runs[0] >= 8 and runs[1] <= 22:
        best = start
        break
window = one.iloc[best:best + 30].copy()
window["n"] = range(1, 31)
window["cas_ms"] = (window.time_ms - window.time_ms.iloc[0]).round(0).astype(int)
window["krok_px"] = step[best:best + 30].round(1)
window["rychlost"] = speed[best:best + 30].round(0)
window.loc[window.index[0], ["krok_px", "rychlost"]] = np.nan
blank = set(range(9, 21))   # tyto řádky počítají studenti sami
lines = {"student": [], "klic": []}
for kind in lines:
    lines[kind] += ["| n | čas (ms) | x (px) | y (px) | krok (px) | rychlost (°/s) | F / S |", "|--:|--:|--:|--:|--:|--:|:-:|"]
    for row in window.itertuples():
        first = row.n == 1
        hide = kind == "student" and row.n in blank
        krok = "–" if first else ("" if hide else f"{row.krok_px:.1f}")
        rych = "–" if first else ("" if hide else f"{row.rychlost:.0f}")
        label = "" if kind == "student" else ("–" if first else ("**S**" if row.rychlost > 30 else "F"))
        lines[kind].append(f"| {row.n} | {row.cas_ms} | {row.gaze_x:.0f} | {row.gaze_y:.0f} | {krok} | {rych} | {label} |")
(HERE / "_ivt_tabulka_student.md").write_text("\n".join(lines["student"]) + "\n")
(HERE / "_ivt_tabulka_klic.md").write_text("\n".join(lines["klic"]) + "\n")
labels = ["F"] + ["S" if v > 30 else "F" for v in window.rychlost.iloc[1:]]
groups, at = [], 0
while at < 30:
    end = at
    while end + 1 < 30 and labels[end + 1] == labels[at]:
        end += 1
    part = window.iloc[at:end + 1]
    groups.append(dict(typ=labels[at], od=at + 1, do=end + 1, trvani_ms=round((end - at + 1) * 1000 / 60), x=round(part.gaze_x.mean()), y=round(part.gaze_y.mean())))
    at = end + 1
key["ivt"] = dict(ppd=round(PPD, 1), ucastnik="P01", pokus=1, prvni_vzorek=int(best), useky=groups)

# ---------------------------------------------------------------- PL 5: scanpath, AOI a metriky ručně
six = run("06-four-faces")
fixations = six["s5"].bundle["fixations"]
areas = pd.DataFrame(json.loads((EXAMPLES / "pipelines" / "06-four-faces.json").read_text())["graph"]["nodes"][5]["params"]["aois"])
STIMULUS = "set_1"
boxes = areas[areas.stimulus == STIMULUS]


def area_of(x, y):
    for a in boxes.itertuples():
        if a.x <= x <= a.x + a.w and a.y <= y <= a.y + a.h:
            return a.name
    return ""


def levenshtein(a, b):
    row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        new = [i]
        for j, cb in enumerate(b, 1):
            new.append(min(row[j] + 1, new[-1] + 1, row[j - 1] + (ca != cb)))
        row = new
    return row[-1]


scan, strings = {}, {}
for who in ("P01", "P02", "P04"):
    f = fixations[(fixations.participant == who) & (fixations.stimulus == STIMULUS)].copy()
    f["start"] = f["start"].round(0).astype(int)   # už je počítán od začátku pokusu
    f["aoi"] = [area_of(x, y) for x, y in zip(f.x, f.y)]
    f["n"] = range(1, len(f) + 1)
    scan[who] = f
    visits = [a for i, a in enumerate(f.aoi) if a and (i == 0 or a != f.aoi.iloc[i - 1])]
    strings[who] = "".join(LETTER[a] for a in visits)
    table = ["| n | začátek (ms) | trvání (ms) | x (px) | y (px) | AOI |", "|--:|--:|--:|--:|--:|:-:|"]
    table_key = list(table)
    for r in f.itertuples():
        table.append(f"| {r.n} | {r.start} | {r.duration:.0f} | {r.x:.0f} | {r.y:.0f} |  |")
        table_key.append(f"| {r.n} | {r.start} | {r.duration:.0f} | {r.x:.0f} | {r.y:.0f} | {LETTER.get(r.aoi, '–')} |")
    (HERE / f"_fixace_{who}_student.md").write_text("\n".join(table) + "\n")
    (HERE / f"_fixace_{who}_klic.md").write_text("\n".join(table_key) + "\n")
    inside = f[f.aoi != ""]
    metrics = {}
    for name in ("Angry", "Sad", "Happy", "Neutral"):
        mine = inside[inside.aoi == name]
        entries = sum(1 for i, a in enumerate(f.aoi) if a == name and (i == 0 or f.aoi.iloc[i - 1] != name))
        metrics[LETTER[name]] = dict(pocet_fixaci=len(mine), dwell_ms=int(mine.duration.sum()), ttff_ms=int(mine.start.min()) if len(mine) else None,
                                     prvni_fixace_ms=int(mine.duration.iloc[0]) if len(mine) else None, navstevy=entries, navraty=max(0, entries - 1))
    trans = pd.crosstab(pd.Series(list(strings[who][:-1]), name="z"), pd.Series(list(strings[who][1:]), name="do")).reindex(index=list("ZSVN"), columns=list("ZSVN"), fill_value=0)
    key[f"scanpath_{who}"] = dict(retezec=strings[who], pocet_fixaci=len(f), metriky=metrics, prechody=trans.to_dict(orient="index"))
key["levenshtein"] = {f"{a}-{b}": levenshtein(strings[a], strings[b]) for a, b in (("P01", "P02"), ("P01", "P04"), ("P02", "P04"))}
key["levenshtein_prvnich_6_navstev"] = {f"{a}-{b}": [strings[a][:6], strings[b][:6], levenshtein(strings[a][:6], strings[b][:6])] for a, b in (("P01", "P02"), ("P01", "P04"), ("P02", "P04"))}
key["rozlozeni"] = {LETTER[a.name]: dict(x=int(a.x), y=int(a.y), w=int(a.w), h=int(a.h)) for a in boxes.itertuples()}

picture = Image.open(EXAMPLES / "datasets" / "four-faces" / "stimuli" / f"{STIMULUS}.png")
for name, who in (("scanpath_podklad.png", None), ("scanpath_klic_P01.png", "P01"), ("scanpath_klic_P02.png", "P02")):
    fig, ax = plt.subplots(figsize=(11.2, 6.6), dpi=150)
    ax.imshow(picture, extent=(0, 1920, 1080, 0), alpha=0.55 if who is None else 0.8)
    ax.set_xticks(range(0, 1921, 160)); ax.set_yticks(range(0, 1081, 90))
    ax.set_xticks(range(0, 1921, 40), minor=True); ax.set_yticks(range(0, 1081, 30), minor=True)
    ax.grid(which="major", color="#555", linewidth=0.5, alpha=0.6); ax.grid(which="minor", color="#777", linewidth=0.2, alpha=0.5)
    ax.set_xlim(0, 1920); ax.set_ylim(1080, 0); ax.set_xlabel("x (px)"); ax.set_ylabel("y (px)"); ax.tick_params(labelsize=7)
    if who:
        f = scan[who]
        ax.plot(f.x, f.y, color="#c2185b", linewidth=1.2)
        ax.scatter(f.x, f.y, s=f.duration * 1.2, color="#ff5ebc", alpha=0.55, edgecolor="#7a0f45")
        for r in f.itertuples():
            ax.annotate(str(r.n), (r.x, r.y), ha="center", va="center", fontsize=7, weight="bold")
        for a in boxes.itertuples():
            ax.add_patch(plt.Rectangle((a.x, a.y), a.w, a.h, fill=False, edgecolor="#1a56a8", linewidth=1.4, linestyle="--"))
            ax.text(a.x + 8, a.y + 30, LETTER[a.name], color="#1a56a8", fontsize=12, weight="bold")
        ax.set_title(f"Klíč: scanpath {who}, podnět {STIMULUS} (velikost kruhu = délka fixace)", fontsize=9)
    fig.tight_layout(); fig.savefig(HERE / name); plt.close(fig)

# ---------------------------------------------------------------- tabulky pro jamovi (záloha, kdyby aplikace neběžela)
wide = six["s8"].bundle["summary"]
table = wide.pivot(index="participant", columns="aoi", values=["dwell_pct", "first_fixation_ms", "fixation_count"])
table.columns = [f"{m}_{a}" for m, a in table.columns]
table.round(2).reset_index().to_csv(HERE / "ctyri_obliceje_jamovi.csv", index=False)
late = six["b15"].bundle["summary"].pivot(index="participant", columns="aoi", values="dwell_pct")
late.columns = [f"dwell_pct_po3s_{a}" for a in late.columns]
late.round(2).reset_index().to_csv(HERE / "ctyri_obliceje_po3s_jamovi.csv", index=False)
two = run("02-search-difficulty")["s7"].bundle["summary"]
search = two[two.aoi == "Target"].pivot(index="participant", columns="condition", values=["first_fixation_ms", "dwell_ms", "fixation_count"])
search.columns = [f"{m}_{c}" for m, c in search.columns]
search.round(2).reset_index().to_csv(HERE / "hledani_jamovi.csv", index=False)
try:
    from scipy import stats
    d = wide.pivot(index="participant", columns="aoi", values="dwell_pct"); f = wide.pivot(index="participant", columns="aoi", values="first_fixation_ms")
    tests = {"dwell_pct veselý vs zlostný (celý pokus)": stats.ttest_rel(d.Happy, d.Angry), "dwell_pct veselý vs zlostný (po 3 s)": stats.ttest_rel(late.dwell_pct_po3s_Happy, late.dwell_pct_po3s_Angry),
             "first_fixation_ms zlostný vs veselý": stats.ttest_rel(f.Angry, f.Happy),
             "hledání: first_fixation_ms hard vs easy": stats.ttest_rel(search.first_fixation_ms_hard, search.first_fixation_ms_easy)}
    key["t_testy"] = {k: dict(t=round(float(v.statistic), 2), df=int(v.df), p=float(f"{v.pvalue:.2g}")) for k, v in tests.items()}
except ImportError:
    pass
key["ctyri_obliceje_prumery"] = wide.groupby("aoi")[["first_fixation_ms", "dwell_pct", "fixation_count"]].mean().round(1).rename(index=CZ).to_dict(orient="index")
key["ctyri_obliceje_po3s_dwell_pct"] = six["b15"].bundle["summary"].groupby("aoi")["dwell_pct"].mean().round(1).rename(index=CZ).to_dict()
key["hledani_prumery"] = two[two.aoi == "Target"].groupby("condition")[["first_fixation_ms", "dwell_ms"]].mean().round(0).to_dict(orient="index")

# ---------------------------------------------------------------- PL 6: zornice a počítání zpaměti (simulovaná záloha)
rng = np.random.default_rng(48)
rows, effort = [], dict(lehká=0.06, střední=0.20, těžká=0.38)
for person, (base, reactive) in {"A": (3.4, 1.0), "B": (4.1, 0.75)}.items():
    trial = 0
    for repeat in range(2):
        for level in rng.permutation(list(effort)):
            trial += 1
            time = np.arange(-2000, 8000, 20.0)   # 50 Hz jako Tobii Glasses 2
            rise = np.clip(time / 1500, 0, 1) * np.where(time > 6000, np.exp(-(time - 6000) / 1500), 1)
            pupil = base + 0.04 * np.sin(2 * np.pi * (time / 7000 + rng.uniform())) + effort[level] * reactive * rise + rng.normal(0, 0.02, len(time))
            _, _, pupil, _, _ = generate.lose_signal(rng, time + 2000, np.zeros(len(time)), np.zeros(len(time)), pupil, 0.2, 0.0, 0.004)
            rows.append(pd.DataFrame(dict(ucastnik=person, pokus=trial, obtiznost=level, cas_ms=time.astype(int), zornice_mm=np.round(pupil, 3))))
pupil = pd.concat(rows, ignore_index=True)
excel(pupil, "zornice_pocitani_excel.csv")
base = pupil[pupil.cas_ms < 0].groupby(["ucastnik", "pokus"]).zornice_mm.mean().rename("baseline")
task = pupil[(pupil.cas_ms >= 1500) & (pupil.cas_ms < 6000)].groupby(["ucastnik", "pokus", "obtiznost"]).zornice_mm.mean().rename("uloha").reset_index().join(base, on=["ucastnik", "pokus"])
task["zmena"] = task.uloha - task.baseline
key["zornice"] = dict(po_pokusech=task.round(3).to_dict(orient="records"),
                      prumer_zmeny=task.groupby(["ucastnik", "obtiznost"]).zmena.mean().round(3).unstack().to_dict(orient="index"),
                      prumer_surove=task.groupby(["ucastnik", "obtiznost"]).uloha.mean().round(3).unstack().to_dict(orient="index"),
                      chybi_pct=round(100 * pupil.zornice_mm.isna().mean(), 1))
fig, ax = plt.subplots(figsize=(8, 4), dpi=130)
corrected = pupil.join(base, on=["ucastnik", "pokus"])
corrected["zmena"] = corrected.zornice_mm - corrected.baseline
for level, colour in zip(effort, ("#4c9f70", "#e0a030", "#c2185b")):
    mean = corrected[corrected.obtiznost == level].groupby("cas_ms").zmena.mean().rolling(10, center=True, min_periods=1).mean()
    ax.plot(mean.index / 1000, mean, label=level, color=colour)
ax.axvline(0, color="#333", linewidth=0.8); ax.axhline(0, color="#999", linewidth=0.5)
ax.set_xlabel("čas od zadání příkladu (s)"); ax.set_ylabel("změna zornice proti baseline (mm)"); ax.legend(title="obtížnost"); ax.set_title("Klíč: zornice a počítání (simulovaná data)", fontsize=10)
fig.tight_layout(); fig.savefig(HERE / "zornice_klic.png"); plt.close(fig)

# ---------------------------------------------------------------- obrázky k tisku
A4 = (3508, 2480)   # A4 na šířku, 300 dpi
target = Image.new("RGB", A4, "white")
draw = ImageDraw.Draw(target)
points = [(x, y) for y in (300, 1240, 2180) for x in (350, 1754, 3158)]
for n, (x, y) in enumerate(points, 1):
    draw.ellipse([x - 60, y - 60, x + 60, y + 60], outline="black", width=8)
    draw.ellipse([x - 10, y - 10, x + 10, y + 10], fill="black")
    draw.text((x + 85, y - 85), str(n), fill="black", font=font(90))
draw.text((1754, 2420), "Validační terč · vzdálenost bodů 1–3: změřte pravítkem a zapište do pracovního listu 2", fill="#444", font=font(40), anchor="mm")
target.save(HERE / "validacni_terc_A4.png", dpi=(300, 300))

chart = Image.new("RGB", A4, "white")
draw = ImageDraw.Draw(chart)
cx, cy = A4[0] // 2, A4[1] // 2
draw.line([(cx - 40, cy), (cx + 40, cy)], fill="black", width=8); draw.line([(cx, cy - 40), (cx, cy + 40)], fill="black", width=8)
letters = iter("KRSNHVDOZCEFPLTAUBGMXYJ" * 3)
for ring, (radius, size) in enumerate(((230, 34), (480, 70), (800, 118), (1150, 170)), 1):
    count = 6 + 2 * ring
    for i in range(count):
        angle = 2 * np.pi * (i + 0.5 * (ring % 2)) / count
        x, y = cx + radius * 1.35 * np.cos(angle), cy + radius * 0.95 * np.sin(angle)
        if 60 < x < A4[0] - 60 and 60 < y < A4[1] - 60:
            draw.text((x, y), next(letters), fill="black", font=font(size), anchor="mm")
chart.save(HERE / "periferni_videni_A4.png", dpi=(300, 300))

for name in ("set_1", "set_2"):
    shutil.copy(EXAMPLES / "datasets" / "four-faces" / "stimuli" / f"{name}.png", HERE / f"ctyri_obliceje_{name}.png")
shutil.copy(EXAMPLES / "datasets" / "glasses-shelf" / "stimuli" / "Shelf.png", HERE / "regal.png")

(HERE / "_klic_cisla.json").write_text(json.dumps(key, indent=1, ensure_ascii=False))
print(json.dumps(key, indent=1, ensure_ascii=False))
