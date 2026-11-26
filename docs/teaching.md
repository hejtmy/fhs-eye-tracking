# Teaching with Gaze Lab

The app is built around one idea: students should see what every processing
decision does to the data, at the moment they make it.

## What supports that on screen

- **Input and Output.** Selecting a step shows the data that entered it and
  the data that left it. For the Load step the input is the file as the
  tracker wrote it.
- **Show input in grey.** In the signal view, the data before the step are
  drawn underneath the data after it. A blink margin, a filled gap or a
  smoothing window becomes visible as the difference between the two lines.
- **Event bars.** Under the signal, coloured bars show on one time axis what
  was removed, what was filled, and where blinks, saccades and fixations lie.
  Zooming reloads that stretch in full detail.
- **What this step did.** Each step reports in a sentence what it changed
  ("37 blinks, 443 samples removed, 1.8% of the data") and which tables are
  new or changed.
- **A question per step**, written to be answered by trying things.
- **The code.** Cleaning and detection are calculated by the pymovements
  package. Those steps offer *Do this step in your own Python script*: the
  pymovements calls with the current settings, as a script that runs on the
  CSV downloaded from the step's Input tab. Students who go on to script
  their analysis start from code they have already watched working. Every
  step also shows its own source.
- **Branches.** *Branch* on a step starts a second line of analysis from the
  same data, for example I-VT beside I-DT, without copying anything.
- **Instant re-runs.** Changing a setting recomputes that step and those
  after it, and the counts on the pipeline update.

## The five examples

Each opens with a short list of things to try (the blue strip at the top;
step through it with the arrows). All data are simulated; the true fixations
are in each dataset's `truth/` folder.

| Example | Idea | Roughly |
| --- | --- | --- |
| From samples to fixations | What a sample is; what a blink does to the signal; I-VT against I-DT; saccades and their main sequence; a participant with poor data (P06); the step as a script | 35 min |
| Is a hard search slower? | Areas of interest per stimulus; time to first fixation; long and wide tables; a paired t-test in JASP or jamovi | 40 min |
| Does effort show in the pupil? | Blink margins, interpolation limits and baselines for pupil data; why trial length confounds the comparison | 30 min |
| Glasses: which product gets attention? | A Tobii Pro Lab export of Glasses 2: sensor rows, markers, mapped gaze, AOI hit columns, viewing patterns | 45 min |
| Glasses: straight from the SD card | The raw packet format; scene-video coordinates; why the speed threshold is higher with a moving head | 20 min |

Effects built into the simulated data, so that there is something to find:

- **Visual search.** In hard trials the target is fixated later (about 2.1 s
  against 0.7 s) and the pupil dilates more. Participant P06 has three times
  the noise and frequent signal loss.
- **Shelf.** In the task “find the cheapest” the cheapest product (Porridge)
  collects the most dwell time, and prices are read in order before the low
  ones are compared; in the choice task each shopper goes back and forth
  between two favourites, which shows up as A → B → A patterns.

## A 90-minute session that works

1. **Ten minutes, everyone together.** Open *From samples to fixations*.
   Select the Load step and look at *File as read*: one row, one sample. Ask
   how many rows one second of looking produces.
2. **Twenty minutes in pairs.** Work through the suggestions of the first
   example. Collect the fixation counts different pairs got with different
   thresholds on the board. Nobody's number is "the" number of fixations;
   compare with `truth/fixations.csv` at the end.
3. **Thirty minutes in pairs.** *Is a hard search slower?* up to the exported
   table. Each pair runs the paired t-test in JASP or jamovi.
4. **Twenty minutes.** Pairs enlarge the target areas, or change the fixation
   threshold, and re-run the test. Does the conclusion hold? This is the
   point of the session: results depend on decisions that are rarely reported.
5. **Ten minutes.** What would a methods section have to say for someone
   else to arrive at the same table?

## From the examples to students' own data

*Examples → Analyse your own recording* starts an empty pipeline with a Load
step. A sensible first pipeline for a screen experiment:

Load recording → Remove off-screen gaze → Detect and remove blinks → Fill
short gaps → Detect fixations by speed → Draw areas of interest → Measure
attention per area → Build a table for statistics

(add *Detect saccades* after the fixations if saccade counts or amplitudes
matter; it adds a table and changes nothing else)

and for Tobii Glasses 2 from a Pro Lab export:

Load recording → Cut trials from markers → Fill short gaps → Detect fixations
by speed → Areas from file columns → Measure attention per area / Find
viewing patterns → Build a table for statistics

The step library greys out steps that cannot work yet and says what is
missing ("Needs fixations. Add Detect fixations by speed first.").

For handing in work, *Export results* gives one zip with the tables, the
pipeline and a script that reproduces them; *Save* gives just the pipeline
file, which a teacher can open to see every setting.

## From the app to a script

A possible last exercise for students who will write their own analysis:
download the Samples table of the step before fixation detection, copy the
script from *Do this step in your own Python script*, run it
(`pip install pymovements`), and compare the printed events with the
Fixations table in the app. Then change one argument in the script and
predict the result before running it.

## What the app does not teach

It computes no statistics and makes no claims about cognition. Pupil size is
in the tracker's units. The simulated data follow a deliberately simple model:
real recordings have calibration drift, smooth pursuit, head movement and
artefacts that this model does not contain.
