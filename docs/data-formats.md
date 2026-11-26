# Bringing your own recordings

Upload one file per participant (or recording) in the Load step. The format
is recognised from the file's content; you can override it under *File
format*. After reading, check three things before trusting anything further
down the pipeline:

1. **File as read** (data panel): does the table look like your file?
2. **What this step did** (right column): the sampling rate, the units that
   were assumed, and how many rows were set aside.
3. **Columns**: is the right column used for time, gaze and pupil?

## Tobii Pro Glasses 2 (and 3)

There are two ways in.

### A. Tobii Pro Lab data export (recommended)

In Tobii Pro Lab: *Data Export*, format tab-separated (`.tsv`), one file per
recording. Include at least:

| Needed for | Columns |
| --- | --- |
| everything | Recording timestamp · Gaze point X · Gaze point Y · Sensor |
| participants | Participant name (or Recording name) |
| trials from markers | Event (and Event value) |
| pupil | Pupil diameter left · Pupil diameter right |
| areas of interest | Mapped gaze data X/Y for your snapshot · the *AOI hit* columns |
| comparing with Tobii's fixations | Eye movement type · Eye movement type index |

What the reader does:

- keeps the rows whose *Sensor* is “Eye Tracker” and sets gyroscope and
  accelerometer rows aside;
- turns rows with an *Event* into a separate **Markers** table;
- copes with decimal commas (Czech and German Windows) and with both old and
  new column names (with or without units such as `[MCS px]`);
- averages the two pupil diameters into *Pupil diameter mean* (or takes one
  eye, your choice);
- proposes the *AOI hit*, *Mapped gaze data* and *Eye movement type* columns
  as extra columns to keep.

**Which gaze columns?** *Gaze point X/Y* is gaze in the scene video, which
moves with the head: fine for detecting fixations (a speed threshold of about
100 °/s), useless for fixed areas of interest. *Mapped gaze data X/Y*
is gaze on a still snapshot after Tobii's mapping: use it when you want to
see gaze on the picture and draw areas. Degrees are only approximate there,
because the snapshot is not what the camera saw; the example pipeline uses
50 °/s. Upload
the snapshot as a stimulus image to see it behind the gaze. The simplest
route to AOI measures for glasses is the step *Areas from file columns*,
which reads Tobii's own AOI hits.

Trials: a glasses recording is one stream. Send events during recording (or
add them in Pro Lab) named like `task_start` / `task_end` and use *Cut trials
from markers*.

### B. Raw recording from the SD card

Upload `livedata.json.gz` from
`projects/<project>/recordings/<recording>/segments/1/`. No Tobii software is
needed. The reader assembles one row per gaze sample from the packets (`gp`,
`gp3`, `pd`), converts gaze to scene-video pixels (1920 × 1080) and time to
milliseconds from the start, marks invalid packets (`s` ≠ 0) as missing, and
turns API events and sync-port signals into markers.

All recordings are called `livedata.json.gz`, so after uploading several, type
a participant name next to each file. There is no mapping onto snapshots in
this route: positions are relative to the camera, so drawn areas of interest
make no sense, but fixation counts, durations, saccades, blinks and pupil do.

### A caveat

Both Tobii readers were written from the documented formats and tested on the
simulated files in `examples/datasets/`. They have not yet been run on a real
Glasses 2 recording in this repository. Column names differ a little between
Pro Lab versions; the reader matches them by how they begin, and the mapping
dialog lets you correct anything it misses. If a real export fails to load,
the error names the file and the reason, and the file can always be read as
*Table of samples* with manual mapping.

## EyeLink

Convert the EDF with SR Research's EDF2ASC (samples and events) and upload the
`.asc`. The file is parsed by `pymovements.gaze.from_asc`. `TRIALID … TRIAL_RESULT` messages become trials; samples between
trials are left out; all messages become markers. For binocular recordings
choose the eye under *File format*. Pupil size is in EyeLink's arbitrary units.

## Any other tracker: a table of samples

CSV, TSV or other delimited text with one row per sample. The separator, the
decimal mark and comment lines at the top are detected; codes for missing
values (such as `-1`) can be entered under *File format*. Then map the columns:

| Meaning | Needed | Notes |
| --- | --- | --- |
| Time | yes | milliseconds, seconds or microseconds; detected from the spacing of samples, can be set by hand |
| Gaze X, Gaze Y | yes | pixels, or fractions of the screen (0–1), which are multiplied by the width and height you enter |
| Pupil size | no | zero or negative values count as missing |
| Participant | no | otherwise each file is one participant, named by its label |
| Trial | no | otherwise the file is one trial; cut trials from markers, or map a trial column |
| Condition, Stimulus | no | can also be added later with *Add trial information* |

Column names of common exports are recognised (Tobii, SMI, Gazepoint and
similar); anything else you choose from a list that shows an
example value of each column. Time must run forward within each participant
and trial: if the clock restarts for every trial, map the trial column.
The origin must be the top left corner; exports that count y upward from the
bottom (Pupil Labs `norm_pos`) need flipping before upload.

## Stimulus images

Upload PNG, JPEG or WebP images in the Load step. An image is shown behind
the gaze of every trial whose *stimulus* value equals the image's file name
(with or without extension, ignoring case). If a dataset has exactly one
image, it is used for all trials. Images are stretched over the full width
and height given in the Load step, so they should be screenshots of the whole
screen (or the snapshot that gaze was mapped onto).

## Viewing geometry

Detection thresholds are in degrees of visual angle, so the app needs to
know the geometry. For a screen, enter its width in centimetres and the
viewing distance; for glasses, the horizontal field of view of the scene
camera (82° for Glasses 2, 95° for Glasses 3). The Load step reports the
resulting pixels per degree and passes the geometry to pymovements as its
`Experiment`. A scene camera is described to pymovements as a screen one
metre away that spans the field of view, which gives the same angles.

## Limits

One dataset may hold up to 300 MB of files and 3 million samples by default;
both are server settings (see [deployment.md](deployment.md)). Uploads are
deleted a week after their last use.
