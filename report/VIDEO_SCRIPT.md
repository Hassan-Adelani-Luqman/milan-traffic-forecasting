# Video demonstration — script and guidance

**Target: 9 minutes** (the brief allows 7–10; 9 leaves room to slow down without
overrunning).

---

## What the rubric actually rewards

The 8 marks are scored on four things: *implementation, results, design decisions, and
limitations*, explained **specifically** and **directly connected to the submitted work**.

The band boundaries are worth reading carefully, because they describe a failure mode
rather than a missing topic:

| Band | Wording | What that means in practice |
|---|---|---|
| Exemplary (6–8) | "specific and well-articulated explanations directly connected to the submitted work" | You name the file, the number, the decision, and the evidence for it |
| Developing (2–4) | "overly descriptive, or lacks sufficient technical depth and connection to the implementation details" | You narrate what is on screen |
| Beginning (0–2) | "generic" | What you said could describe anybody's project |

**The single biggest risk is description instead of explanation.** "Here is my EDA
notebook, it shows the daily pattern" is descriptive. "The decomposition put 82.9% of
variance in the daily cycle and 10% in the weekly, and that pair of numbers is why I could
not use SARIMA" is an explanation connected to the work.

**Rule for the whole video:** every time you show something, say *why it is there* and
*what it changed*. If a sentence would be true of any traffic-forecasting project, cut it.

---

## Before you record

**Have these open in tabs, in this order**, so you never hunt for a window on camera:

1. `report/REPORT.pdf` — scrolled to the top
2. `results/figures/02_spatial_totals.png`
3. `results/figures/05_mstl_decomposition.png`
4. `results/tables/final_metrics_all_test.csv` (or the Results table in the PDF)
5. `results/experiments.csv`
6. `src/models/gbm.py` — scrolled to the module docstring at the top
7. `results/figures/forecast_test_4159_lstm.png`
8. A terminal in the project root

**Setup checklist**

- Screen resolution 1920×1080; editor font size up two or three steps — on a marker's
  screen your normal size is unreadable.
- Close Slack, email, notifications. Close unrelated browser tabs.
- Record at 1080p. Audio matters more than video: use a headset mic, not the laptop's,
  and record somewhere without echo.
- Webcam optional. If your face is on screen, put it in a corner and keep it small.
- Do a 20-second test recording and **listen back** before committing to a full take.

**Rehearse once, out loud, with a timer.** Not to memorise it — to find the sentences
you stumble over, and to check the pacing. Then record without reading verbatim.

---

## The script

Timings are cumulative. The **Say** lines are the substance, not words to recite — put
them in your own phrasing. The **Show** lines are what should be on screen.

---

### 1. Problem and research question — 0:00 → 0:45

**Show:** `report/REPORT.pdf`, title page, then scroll to the abstract.

**Say:**

- Operators commit radio and backhaul capacity *before* demand arrives, and the cost of
  being wrong is asymmetric — under-provisioning degrades service, over-provisioning wastes
  energy and capital. That is why short-horizon forecasting is an operational problem.
- The data is Telecom Italia's Milan grid: 100 × 100 cells, 10-minute intervals, two
  months, 8,928 observations per cell.
- State the research question as two halves: *which model is better*, and *does the answer
  depend on the area*. Say explicitly that the second half is the one that shaped the
  design, because it is what most single-series comparisons skip.

**Avoid:** reading the abstract aloud. Summarise it.

---

### 2. Data handling and memory — 0:45 → 2:00

**Show:** terminal, then the memory table in the PDF (Table 1).

**Say:**

- 19.38 GiB of text across 62 files becomes a 340.58 MiB matrix. The problem is not storing
  the result, it is *reaching* it without holding more than a day in memory.
- Three strategies were **measured**, not assumed: naive pandas, chunked pandas, Polars
  lazy. Give the numbers — 633 MiB peak, 173 MiB, 552 MiB.
- Then make the point that earns the marks: **the headline is scaling, not peak.** Naive
  would need 17.90 GiB resident for all 62 days; both optimised paths hold one 5.49 MiB
  block regardless of how many days you process. O(1) against O(*n*).
- Polars is ~6× faster but peaks 3.2× higher, so neither dominates — which is why both are
  kept and selected by a flag, rather than one being declared the winner.

**The detail worth 30 seconds** — this is a genuine methodological point and markers notice
it:

> My first benchmark ran all three strategies in one process and reported 544, 184 and
> 384 MiB for *identical* work. CPython does not return freed arenas to the OS, so
> whichever strategy ran first absorbed the cost of growing the heap and the later ones
> looked artificially cheap. Every measurement now runs in a fresh subprocess, and repeated
> runs agree to within about 2%.

That single anecdote demonstrates you understand what you measured, not just that you
measured it.

---

### 3. Exploratory analysis and the decision it forced — 2:00 → 3:30

**Show:** `02_spatial_totals.png`, then `05_mstl_decomposition.png`.

**Say — the area selection (this is a design decision, say so):**

- The brief asks for three areas. The obvious choice is the three busiest cells.
- Converting their IDs to grid coordinates puts squares 5161, 5059 and 5259 **within 470 m
  of one another** — all in one hotspot by the Duomo.
- So comparing across them would have measured the same traffic regime three times, and
  could not have answered the second half of the research question. That is why the areas
  modelled are ranks 1, 424 and 109 instead.
- Reinforce with the finding that makes it more than a technicality: those three adjacent
  cells have weekend/weekday ratios spanning **0.425 to 1.384** — a factor of 3.3 between
  neighbours. Traffic *character* varies at a finer spatial scale than volume rank reveals.

**Say — the decomposition:**

- MSTL with periods 144 and 1008: daily carries **82.9%** of variance at strength 0.959,
  weekly **10.0%** at 0.746.
- Two simultaneous seasonal periods is exactly what SARIMA cannot represent — it takes one —
  and at *s* = 144 it is computationally intractable anyway. **That pair of facts is the
  argument for dynamic harmonic regression**, and it came from a measurement rather than
  from a textbook preference.
- Mention the 12-hour spectral peak beside the 24-hour one: the daily cycle is not a single
  sinusoid, so at least two daily Fourier harmonics are required. The search started at
  K₁ = 2 for that reason.

---

### 4. The models and the protocol — 3:30 → 4:45

**Show:** the model table in the PDF (Section 5.4), then `src/models/` in the editor.

**Say:**

- Three models chosen to differ in **what they assume**, not just in implementation:
  harmonic regression is *told* the seasonal structure; LightGBM is *told* which lags to
  look at; the LSTM assumes nothing and sees a raw window.
- Lag selection was empirical: the ACF has local maxima at 144, 288, 432, 720, 864 and
  1,008, so those are the lags LightGBM gets — identified from the data, not by convention.
- **Persistence is not a straw man.** Lag-1 autocorrelation is 0.987, so repeating the last
  observation scores MASE 0.195–0.267 with R² above 0.94. It is the bar that decides whether
  any complexity earned its place.
- Protocol, briefly but precisely: chronological splits (never random, on a time series);
  transforms fitted on train only, and the scaler *raises* if asked to refit; and inference
  is always walk-forward with true observed history, never a recursive rollout.

**One sentence that shows engineering care:**

> The batched walk-forward used by LightGBM and the LSTM is asserted equal to the
> step-by-step loop in the test suite, because the fast path is only valid if every window
> contains nothing but true prior observations.

---

### 5. Experimentation — 4:45 → 5:30

**Show:** `results/experiments.csv` — scroll, then widen the `rationale_for_next_change`
column on one row.

**Say:**

- 101 logged candidates. Every row carries hyperparameters, validation metrics, wall time,
  parameter count, the git commit, and a **mandatory** rationale — the log refuses a row
  with an empty one.
- Read one rationale aloud. It demonstrates the search was reasoned rather than swept.
- Search was staged, one axis at a time, so each decision is attributable. Explain the two
  deliberate deviations: harmonic order by AICc because walk-forwarding 15 candidates costs
  far more than an in-sample criterion; LightGBM by Optuna because `num_leaves`,
  `min_child_samples` and the sampling fractions trade off against each other, so a staged
  sweep would fix each at a value chosen while the others were wrong.

---

### 6. Results — 5:30 → 6:45

**Show:** the MASE table (Table 10 in the PDF), then `cross_area_mase_test.png`.

**Say — lead with the surprise, not the method:**

- **The 22-parameter model wins.** Harmonic ARIMA has the best mean MASE, 0.213, and wins
  two of three areas. On the third, a three-seed LSTM ensemble takes it at 0.233.
- Say the uncomfortable number out loud: **averaged across areas only two of the three
  models beat persistence.** Both LSTM variants do not. A study that reported only model
  errors without that floor would look respectable and be worse than doing nothing.
- Explain the two LSTM rows, because a marker will wonder: `lstm` is the mean of three
  seeds' *errors*; `lstm_ensemble` is the error of their *averaged forecast*. Averaging
  cannot increase absolute error, so the ensemble is better — at three times the training,
  inference and parameter cost.
- Seed variance justifies the three-seed protocol: on square 4159 the LSTM is
  21.16 ± 4.59 MAE, a 22% relative standard deviation. A single seed would have been a
  number with no interpretation.

**Then the cost inversion — this is a strong, specific result:**

- Harmonic ARIMA is the cheapest to train (18 s) and **~1,825× the most expensive to
  serve** (74.6 ms per forecast against the LSTM's 0.041 ms), because appending an
  observation without refitting still runs a Kalman update every step.
- At city scale that disqualifies it: one forecast for each of 10,000 cells takes
  **12.4 minutes**, which is longer than the ten-minute interval being forecast. The
  accuracy ranking and the deployability ranking are opposites.

---

### 7. One technical decision, in depth — 6:45 → 7:45

Pick **one** and go deep. The default below is the strongest because it is the hardest to
fake and shows you understand causality in one-step forecasting.

**Show:** `cross_correlation_test_5161.png` and `results/tables/copying_test.csv`.

**Say:**

- With lag-1 autocorrelation at 0.987, a model can score well by learning to repeat its
  most recent input — it would look successful while having learned nothing. So I tested for
  it explicitly.
- The obvious test is to cross-correlate forecasts against observations and check where the
  peak falls. **When I did that, every model peaked at lag +1 — including the best one.**
- Then the insight: that is not evidence of copying, it is evidence of *causality*. A
  one-step forecast is built only from data up to *t*−1, so it cannot contain the innovation
  at *t*, and must correlate slightly more with the previous value than the current one. A
  forecast peaking at lag 0 on a series this persistent would be the suspicious case,
  because it would imply access to the present value.
- The data settles it: **seasonal naive is the only model peaking at lag 0, and it is the
  worst forecaster in the study.**
- So the verdict rests on the copy ratio instead — distance from the persistence baseline,
  scaled by how far the series actually moves. Copy ratios run 0.54–1.14 against
  persistence's 0.00. No model collapsed.

**Close with:** "My first implementation keyed the verdict on the peak, which flagged all
three real models and cleared the worst one. The test suite has the corrected reasoning
written into it so it cannot drift back."

**Alternatives if you prefer:** the subprocess isolation in Section 2, or the area
selection in Section 3. Do not attempt all three — depth beats coverage here.

---

### 8. Failure analysis and limitations — 7:45 → 8:40

**Show:** the stress-split table, then `forecast_test_4159_lstm.png`.

**Say — the failure that was predicted in advance:**

- The stress split is 23 December to 1 January, four of the eight holidays, never tuned on.
- **Persistence wins outright on two of three areas.** LightGBM degrades by 69–140% and the
  LSTM by 78–103%, while harmonic ARIMA stays within 9%.
- Here is the part worth emphasising: **I wrote that prediction into the LightGBM module
  docstring before the split was ever run** — a tree ensemble cannot extrapolate beyond the
  range of its training targets, and a holiday period is exactly where that bites. *(Show
  the docstring at the top of `src/models/gbm.py`.)* It is the worst non-naive model on all
  three areas.

**Say — a specific failure, not a general one:**

- The LSTM's poor result on square 4159 is a **weekday-morning** failure. Its three worst
  six-hour windows all start around 09:50 on consecutive weekdays, at 2.0–2.6× persistence,
  and its weekday/weekend MAE split is 24.13 against 12.03 — the most lopsided of any model.
  It misses the morning ramp; it is competitive at weekends.

**Say — the limitation, stated plainly:**

- Hyperparameters were tuned on the highest-traffic area only. So the LSTM's failure on
  4159 is **partly a transfer result**, and my evidence does not separate an architectural
  limitation from a transfer failure. Per-area tuning was outside the compute budget, and
  that is the single most informative extension.
- If you have time, add the second one: the staged search is **not device-invariant** — on
  CPU it selected sequence length 288, on the GPU 144, because a candidate that stopped at
  epoch 17 on one device stopped at epoch 2 on the other. The selection should not be
  presented as inevitable.

**Do not soften these.** Volunteering a limitation before a marker finds it is what
"critical reflection" means, and the rubric scores it.

---

### 9. Reproducibility and close — 8:40 → 9:00

**Show:** terminal. Have `python run.py test` already finished so the result is on screen —
do not make the marker watch 90 seconds of dots.

**Say:**

- 501 tests. They target the properties the conclusions depend on — leakage, the equivalence
  of the batched and looped inference paths, MASE scaled by training error rather than the
  window scored.
- A clean clone into an empty virtualenv reproduces **every reported metric exactly**, not
  to three significant figures, because the extracted series and the forecast series are
  committed. The LSTM columns cannot be regenerated without a GPU, which is precisely why
  they are in the repository.
- One-sentence close: the smallest model won on the test week, no model beat persistence
  once the distribution shifted, and the cheapest model to train was the most expensive to
  deploy.

---

## Questions you should be ready for

A viva or a marker's comment is likely to probe these. Have an answer ready; you do not
need to script it.

| Question | The short answer |
|---|---|
| Why not SARIMA? | Two simultaneous seasonal periods (82.9% / 10.0%); SARIMA takes one, and *s* = 144 is intractable. |
| Why is persistence so strong? | Lag-1 autocorrelation 0.987 at a 10-minute horizon. At a longer horizon it would collapse — that is future work. |
| Why did the LSTM underperform? | Partly capacity for 5,472 training points, partly transfer — it was tuned on one area only. I can't separate those with this evidence. |
| Is MASE below 1 "good"? | It means better than the in-sample naive forecast. The meaningful comparison here is against persistence, which is much stronger than naive. |
| Why three seeds? | The spread (±4.59 MAE on 4159) is comparable to the gaps between models; one seed reports one draw. |
| Why is ARIMA(3,0,1) selected when (1,0,1) is within 0.08 MAE? | The protocol selected on validation MAE and I followed it rather than overriding after the fact. I report in the limitations that two extra parameters are not justified on that margin. |
| Did you use AI? | Answer honestly and match what Appendix C of your report says. |

---

## Final checks before you submit the link

- [ ] Length is between 7 and 10 minutes
- [ ] Audio is clear throughout — listen to the whole thing once
- [ ] Every figure you show is legible at the recorded resolution
- [ ] You named at least one **technical decision** and explained the evidence behind it
- [ ] You named at least one **limitation or failure case** without being prompted
- [ ] Nothing on screen that should not be (notifications, unrelated tabs, credentials)
- [ ] Sharing permissions allow the marker to open it — test the link in a private window
- [ ] The URL is pasted into `report/REPORT.md` (the footer) and `report/references.md`

After adding the URL, run `python run.py pdf` to rebuild the PDF so the link is in the
submitted document, and `pytest tests/test_report.py -q` — the video-link test will stop
skipping once the placeholder is replaced.
