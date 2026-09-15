# Draft report sections

> **Status: first draft, to be rewritten in the author's own voice.**
> Every number here traces to `report/RESULTS_SUMMARY.md` and the artefacts under
> `report/tables/`. Sections not present below are blocked on Phases 4–6.

---

# 1. Introduction

Mobile network operators face a scheduling problem with a short deadline. Radio
resources, backhaul capacity and base-station power must be committed before demand
arrives, and the cost of guessing wrongly is asymmetric: under-provisioning degrades
service for users, while over-provisioning wastes energy and capital. Accurate
short-horizon forecasting is what makes proactive allocation possible, and it underpins
practical techniques such as load balancing between cells and putting lightly loaded base
stations to sleep during quiet periods [5].

This study investigates the problem empirically using telecommunications activity data
collected across Milan by Telecom Italia between 1 November 2013 and 1 January 2014 [1],
[11]. The city is divided into a 100 × 100 grid of 235 m square cells, and internet
activity is recorded at 10-minute intervals, giving 8,928 observations for each of 10,000
areas over the two-month period. The dataset is public and widely used, which makes
results on it comparable across studies in a way that proprietary operator data is not.

The research question is:

> **How do different sequential models compare for one-step-ahead mobile network traffic
> forecasting, and how does their performance vary across geographical areas with
> different traffic characteristics?**

The question has two halves, and the second is easy to under-serve. Comparing models on a
single series answers only which algorithm fits that series; it says nothing about whether
the ranking is a property of the method or of the data it was given. This study therefore
treats the choice of areas as a methodological decision rather than an administrative one,
and Section 4 shows that the obvious choice — the three highest-traffic cells — would have
made the comparison uninformative, because those three cells turn out to be immediate
neighbours behaving almost identically.

Three models are implemented and compared: a dynamic harmonic regression with ARIMA
errors, a long short-term memory (LSTM) network, and a gradient-boosted tree ensemble
(LightGBM). They are selected in Section 3 to differ in what they *assume* rather than
only in how they are implemented — the first imposes seasonal structure explicitly, the
second learns representations from raw sequence, and the third learns from engineered
features. Persistence and seasonal-naive baselines appear in every results table as the
reference floor.

The contributions are: an account of processing 19.38 GiB of raw call-detail records into
a tractable form under stated computational constraints, with measured evidence for each
decision; an exploratory characterisation of the data that establishes what a forecasting
model must represent; a comparison of three structurally different models on areas chosen
to span distinct traffic regimes; and an analysis of where those models fail, including a
held-out period containing the Christmas and New Year holidays.

---

# 2. Dataset and Data Preparation

## 2.1 The data

The dataset comprises 62 tab-separated text files, one per day, totalling **19.38 GiB**
(20,804,803,507 bytes), with individual files ranging from 265 to 359 MiB. Each record
carries a square identifier, an interval start time in epoch milliseconds, a counterparty
country code, and five activity measures, of which `internet` is the target variable of
this study.

Three properties of the raw format determined the whole processing design, and each was
established by inspection rather than assumed.

**Records are split by country code.** A single `(square_id, time_ms)` pair appears once
for every country that generated traffic in that cell and interval — on average 3.6
times, and at most 36. Aggregating over country is therefore not a tidying step but the
operation that recovers the quantity of interest. It is also the reason a day holds
roughly 5.16 million records rather than the 1.44 million cells it describes. Across the
period, **319,896,289 raw records** reduce to 89,280,000 cells.

**Timestamps are UTC, but files are aligned to local midnight.** The first record of the
1 November file carries `1383260400000`, which is `2013-10-31T23:00:00Z` — midnight on
1 November in `Europe/Rome`, since Italy was on CET. Each file therefore covers a local
day, not a UTC day. Treating the timestamps as UTC days would have displaced every diurnal
pattern by an hour. No daylight-saving transition falls inside the observation window
(Italy changed clocks on 27 October 2013 and 30 March 2014), so every local day contains
exactly 144 intervals; this was asserted during assembly rather than assumed.

**The target is normalised activity, not an integer count.** Values such as
`11.028366381681026` appear throughout. The measure is a normalised activity index derived
from call-detail records, and the report describes it as such rather than as a count of
events.

## 2.2 Processing strategy

After aggregation the data is small: the full `8928 × 10000` matrix occupies **340.58 MiB**
as `float32`. The memory-management problem is therefore not one of storing the result but
of reaching it — converting 19.38 GiB of text without ever holding more than one day in
memory.

Only three of the eight columns are required. The processing pipeline projects to
`square_id`, `time_ms` and `internet` at parse time, discarding five-eighths of the data
before it is materialised, casts to the narrowest sufficient types (`uint16`, `int64`,
`float32`), and aggregates over country code within a single pass. Each day is reduced to
a dense `144 × 10000` block of 5.49 MiB and written to disk before the next is read.

Three strategies were implemented and measured rather than one being assumed best:

- **Naive pandas** — every column, inferred dtypes, whole file resident. Implemented to be
  measured, not used; it is the "before" condition.
- **Chunked pandas** — projection, narrow dtypes, and incremental aggregation over
  one-million-row chunks.
- **Polars lazy scan** — a declared schema with projection pushdown into the CSV reader and
  a streaming group-by.

## 2.3 Measured results

Table 1 reports each strategy measured on identical input. Peak resident set size is the
figure of interest rather than the size of the resulting frame: the peak occurs during
parsing and is released before the frame is returned, so it is sampled on a background
thread at 20 ms intervals rather than read once at completion.

**Table 1 — Ingest strategies, one day (2013-11-01), local hardware.**

| Strategy | Resident | Peak RSS | Wall time | Scales with days |
|---|---:|---:|---:|---|
| Naive pandas | 295.57 MiB | 633.06 MiB | 5.56 s | **yes** |
| Chunked pandas | 5.49 MiB | 172.55 MiB | 5.86 s | no |
| Polars lazy | 5.49 MiB | 552.22 MiB | 0.95 s | no |

The result contradicted the expectation that the faster engine would also be the leaner
one. Polars is roughly six times faster per day but peaks **3.2× higher** than chunked
pandas, because its CSV reader holds the entire ~322 MB file in memory before parsing.
Two candidate remedies were measured and both made matters worse: `low_memory=True`
reached 559 MiB, and batched reading 697–862 MiB depending on batch size. Neither strategy
dominates, so both are retained and selected by a command-line flag; the full run used
Polars, because the execution environment had ample memory and throughput was the binding
constraint.

The figure that matters most is not peak memory but scaling. Holding all 62 days in the
naive representation would require **17.90 GiB** resident — an extrapolation from one day,
stated as such, and deliberately not executed. Both optimised paths hold a single 5.49 MiB
block at any moment, so their working set is independent of the number of days processed.
The pipeline is O(1) in dataset size where the naive approach is O(n), and that difference,
rather than the ratio of peak values, is what makes the processing feasible.

### A measurement artefact worth reporting

An early version of this benchmark ran all three strategies within one process and
reported 544, 184 and 384 MiB for *identical* work. The cause is that CPython and the
allocators beneath it do not return freed arenas to the operating system, so whichever
strategy runs first absorbs the cost of growing the heap and later ones appear artificially
cheap. Every measurement reported here therefore runs in a fresh subprocess; repeated runs
under that protocol agree to within about 2%. Available system memory is recorded alongside
each measurement, because memory pressure causes the operating system to trim working sets
and compress pages, which *depresses* measured peak RSS and would understate demand.

## 2.4 Execution environment

The processing was performed on Kaggle rather than locally, for a measured reason. The
download rate available locally was 0.44 MiB/s (3.7 Mbit/s), implying approximately 12.6
hours for the full dataset. The same transfer on Kaggle sustained **55.9 MiB/s
(469 Mbit/s)** and completed in **5.92 minutes** — a factor of roughly 127. Since the raw
data is required exactly once, to produce a 340.58 MiB artefact, performing that conversion
where the bandwidth is available was substantially more efficient than performing it where
the analysis was developed.

The execution environment also imposed constraints that shaped the pipeline. Session
scratch storage is discarded when a session ends and sessions are capped at 12 hours, so a
design that downloaded all 62 files before ingesting any would, on a timeout, lose every
raw file and leave nothing behind. The pipeline therefore interleaves: each day is
downloaded, converted, written to persistent storage, and its raw text deleted before the
next begins. Peak disk usage stays near the size of one file rather than 19.38 GiB, and
every completed day is a durable artefact that a resumed run skips.

**Table 2 — Full ingest run (62 days).**

| Quantity | Value |
|---|---|
| Raw records parsed | 319,896,289 |
| Download | 5.92 min total, 5.73 s/day ± 0.64 |
| Ingest | 1.54 min total, 1.49 s/day ± 0.10 |
| Total wall time | 7.7 min |
| Peak RSS | 574 MiB max, 326 MiB mean |
| Output | 340.58 MiB |

## 2.5 Missing data

Two distinct phenomena are easily conflated, and the pipeline treats them separately.

An **absent cell** is a `(square, time)` pair with no record in the raw file. Because a
record exists only where activity was logged, an absent pair means no activity occurred,
not that data was lost; such cells are set to 0.0 and the count reported. Across the period
there are **34,682** of them, 0.0388% of the 89,280,000 cells.

A **missing interval** is a timestamp absent from the grid entirely, which would be genuine
data loss. The policy specified for this case was to interpolate gaps of up to three
intervals, leave longer gaps as `NaN` with the count reported, and raise an error rather
than impute if any gap fell inside the evaluation week. In the event, the assembled matrix
contains **zero missing intervals and zero `NaN` values**: the timestamp grid is complete,
every local day contains exactly 144 intervals, and the policy never executed.

The absent-cell counts are not uniform across the period, and this is worth reporting. They
hold at roughly 22 per day through 21 November, step upward around 23 November, and reach
1,463 per day over the Christmas period, peaking at **2,267 on 26 December** (Santo
Stefano). By split the means are 220 per day in training, 864 in the test week, and 1,463
in the held-out stress period — roughly a fourfold difference in data density between
training and evaluation. Raw record counts over the same window decline smoothly by 6.7%
rather than stepping, which indicates quiet peripheral cells falling into complete silence
as overall activity declines, rather than a failure of collection. The pattern tracks human
activity, peaking over the holidays, which is itself evidence for the interpretation of
absent cells as silence. It does not affect the forecasting experiments: the three areas
modelled contain no zero value at any point in any split, with minima of 47.3, 55.8 and
80.2.

## 2.6 Reproducibility

All configuration — paths, dates, split boundaries, preprocessing parameters — resides in
a single YAML file, loaded into immutable structures with strict validation that rejects
unknown keys and verifies that the four splits are contiguous, non-overlapping and within
the observation period. Logic resides in a tested library; notebooks import from it and
render figures. The processed artefacts other than the full matrix total approximately
320 KB and are version-controlled, so the exploratory analysis and the modelling stages
reproduce from a clean checkout without repeating the 19.38 GiB download.

---

# 3. Exploratory Analysis

## 3.1 How traffic is distributed across the city

Figure 1 shows the distribution of total internet activity across the 10,000 cells over
the full period, as a histogram on a logarithmic axis beside the complementary cumulative
distribution function on logarithmic axes. Both views use log scales because cell totals
span nearly five orders of magnitude, from 213.6 to 12,740,060; on a linear axis almost the
entire grid collapses into the first bin.

The distribution is strongly right-skewed (skewness 4.26, excess kurtosis 25.50) with a
mean of 555,289 against a median of 277,871, and a maximum 45.8 times the median. Spatial
concentration is substantial but not extreme: the Gini coefficient is **0.608**, the busiest
1% of cells carry **11.0%** of all traffic, the top 10% carry **48.4%**, and the least
active half of the grid accounts for **11.6%**. No cell is entirely inactive over the
period.

A two-parameter lognormal distribution fits the totals with μ = 12.496 and σ = 1.211. A
Kolmogorov–Smirnov test rejects the fit at p = 4.3 × 10⁻⁵, but that result requires
qualification rather than plain reporting. The test statistic is 0.0232 against a critical
value of 0.0136 at n = 10,000 and α = 0.05 — only 1.7 times the threshold — and the
logarithm of the totals has skewness +0.023 and excess kurtosis +0.013, both effectively
zero. With ten thousand observations the test has sufficient power to reject a maximum
cumulative discrepancy of 2.3 percentage points. The distribution is lognormal to any
practical standard, and quoting the rejection without the statistic would misrepresent it.

The consequence for the study is that traffic volume varies by more than an order of
magnitude between areas, so absolute error metrics such as MAE and RMSE are not comparable
across them. The cross-area comparison in Section 6 therefore uses the mean absolute scaled
error, which is scale-free by construction [10].

## 3.2 Where the busiest cells are, and why it matters

Figure 2 maps the base-ten logarithm of total activity over the 100 × 100 grid. Activity is
concentrated in a compact central region with a pronounced peak, decaying toward the
periphery.

The three highest-traffic cells are squares **5161, 5059 and 5259**, with totals of
12,740,060, 11,170,854 and 10,485,779. Converting their identifiers to grid coordinates
places them at rows 50–52 and columns 58–60 — **within 470 m of one another**. The ten
busiest cells occupy a bounding box of 13 × 10 cells, approximately 3.05 × 2.35 km, in
central Milan.

This finding determined the study design. The brief specifies forecasting across three
geographical areas, and the apparently natural choice is the three with the highest total
traffic. But those three are immediate neighbours within a single hotspot, and a comparison
across them would measure model performance on three samples of the same traffic regime.
It could not answer how performance varies across areas with different characteristics,
which is half of the research question.

The three areas modelled are therefore **square 5161** (rank 1), **square 4159** (rank 424)
and **square 4556** (rank 109). The latter two are specified in the brief, and they span
regimes that the top three do not. Squares 5059 and 5259 are retained in the exploratory
figures for completeness but are not forecast.

## 3.3 The five series and their characteristics

Figure 3 shows each of the five areas over the first two weeks of the observation period,
and Figure 4 overlays the same series normalised to their individual maxima, which compares
shape rather than volume. All five show a pronounced daily cycle and a clear weekly
modulation, with activity collapsing overnight and rising through the morning.

Table 3 summarises each area over the full period.

**Table 3 — Per-area characteristics.**

| Square | Rank | Mean | SD | CV | Peak/trough | Night floor ÷ mean | Weekend ÷ weekday |
|---|---:|---:|---:|---:|---:|---:|---:|
| 5161 | 1 | 1,427 | 1,382 | 0.968 | 99.4 | 0.130 | 1.384 |
| 5059 | 2 | 1,251 | 961 | 0.768 | 30.9 | 0.235 | 0.861 |
| 5259 | 3 | 1,174 | 1,103 | 0.939 | 47.0 | 0.333 | **0.425** |
| 4159 | 424 | 275 | 181 | 0.660 | 14.9 | 0.489 | 0.587 |
| 4556 | 109 | 512 | 248 | **0.485** | 17.0 | **0.534** | 1.140 |

The table justifies the area selection more strongly than the rankings do. The three
forecast areas differ in the properties that make forecasting hard, not merely in volume.
Square 5161 swings by a factor of 99 between its peak and its first-percentile trough and
falls to 13% of its mean overnight; square 4556 swings by a factor of 17 and retains a
night floor at 53% of its mean. Their coefficients of variation differ by a factor of two.

The weekly patterns separate them further, and the grid geometry published with the
dataset [12] allows the pattern to be checked rather than merely inferred. Converting each
cell identifier to its centroid and measuring the distance to known reference points gives
Table 4.

**Table 4 — Where each study area is.**

| Square | Centroid (lat, lon) | Nearest reference point | Distance | Weekend ÷ weekday |
|---|---|---|---:|---:|
| 5161 | 45.4655, 9.1934 | Galleria Vittorio Emanuele II | 276 m | 1.384 |
| 5059 | 45.4634, 9.1874 | Duomo | 226 m | 0.861 |
| 5259 | 45.4676, 9.1874 | Teatro alla Scala | 167 m | 0.425 |
| 4159 | 45.4443, 9.1873 | Università Bocconi | 365 m | 0.587 |
| 4556 | 45.4528, 9.1783 | Navigli | 273 m | 1.140 |

Two of the five match their temporal signature closely. Square 4556 lies 273 m from the
Navigli, Milan's principal nightlife district, and has both the highest night floor of the
five (53% of its mean) and a weekend ratio above one — the profile of an area that stays
active late and is busier at weekends. Square 4159 lies 365 m from Università Bocconi, and
its weekend ratio of 0.587 together with a high night floor is what a university quarter
with substantial resident population would produce.

The three busiest cells are the more interesting result, and it qualifies the reading
offered above. All three sit within 500 m of the Duomo, and yet their weekend ratios span
**0.425 to 1.384** — a factor of 3.3 between cells that are themselves only a few hundred
metres apart. Square 5259, closest to Teatro alla Scala and the municipal and banking
offices around Piazza della Scala, empties at weekends; square 5161, beside the Galleria
Vittorio Emanuele II, fills up. Proximity to a landmark is therefore evidence about a
cell's location but not a sufficient explanation of its traffic: two neighbouring cells in
the same historic centre behave in opposite ways.

That finding reinforces the case made in Section 3.2 from a second direction. It is not
only that the three highest-traffic cells are spatially adjacent; it is that traffic
character varies at a finer spatial scale than volume rank reveals, so ranking by total
activity carries no information about temporal behaviour. These are different forecasting
problems, and a model that handles one well need not handle the others.

## 3.4 First additional analysis: multi-seasonal decomposition

The exploratory figures suggest two seasonal cycles operating simultaneously. Classical
seasonal decomposition accommodates only one, so the series for square 5161 was decomposed
using MSTL [7], which extends seasonal-trend decomposition by Loess to multiple seasonal
periods, with periods of 144 intervals (one day) and 1,008 (one week). Figure 5 shows the
components.

**Table 5 — MSTL variance decomposition, square 5161.**

| Component | Share of variance | Strength |
|---|---:|---:|
| Trend | 2.8% | 0.451 |
| Daily seasonality (144) | **82.9%** | **0.959** |
| Weekly seasonality (1008) | 10.0% | 0.746 |
| Residual | 3.6% | — |

Strength is measured as 1 − Var(remainder) / Var(component + remainder), so a value near
one indicates a component that dominates what remains after the others are removed.
Variance shares do not sum to unity because the components are correlated.

Three conclusions follow. The daily cycle is overwhelmingly dominant, carrying 82.9% of
variance at a strength of 0.959. The weekly cycle is secondary but not negligible at 10.0%
and strength 0.746 — enough that a model ignoring it discards real structure. And the
residual standard deviation is only **19% of the observed**, meaning roughly four-fifths of
the variation is systematic structure that a model can in principle capture.

The modelling consequence is direct. Two seasonal periods are present simultaneously, so
the seasonal model must represent both. A seasonal ARIMA cannot: it accommodates one
seasonal period, and at 10-minute resolution the daily period of s = 144 is in any case
computationally intractable. This is the argument for the dynamic harmonic regression
selected in Section 3, which represents each period by Fourier terms entered as exogenous
regressors [6].

## 3.5 Second additional analysis: autocorrelation and stationarity

Figure 6 shows the autocorrelation and partial autocorrelation functions for square 5161 to
lag 1,100, with the daily and weekly lags marked.

The lag-1 autocorrelation is **0.987**. Local maxima occur at lags 144, 288, 432, 720, 864
and 1,008 — every multiple of the daily period, with the weekly lag among them —
with autocorrelations of 0.878 at one day and 0.838 at one week. The structure decays
slowly and periodically rather than dying out, which is the signature of strong seasonality
rather than a short-memory process.

Stationarity was assessed with the Augmented Dickey–Fuller and KPSS tests together, since
their null hypotheses are opposites and agreement between them is more informative than
either alone. Table 6 reports both on the raw series and on two transformations.

**Table 6 — Stationarity tests, square 5161.**

| Series | ADF statistic | ADF p | KPSS statistic | KPSS p | Verdict |
|---|---:|---:|---:|---:|---|
| Raw | −19.03 | 0.0000 | 0.237 | ≥ 0.10 | Stationary (both agree) |
| First difference | −15.16 | 0.0000 | 0.003 | ≥ 0.10 | Stationary (both agree) |
| Seasonal difference (lag 144) | −11.83 | 0.0000 | 0.069 | ≥ 0.10 | Stationary (both agree) |

KPSS p-values are clamped to the upper end of the tabulated range, so 0.10 indicates
"≥ 0.10" rather than an exact value.

This result requires careful statement. Both tests indicate stationarity on the raw series,
which would ordinarily suggest no differencing is required — and indeed the harmonic
regression is specified with d = 0 on this basis. But "stationary" here means only that the
series contains no stochastic trend. The mean varies enormously with time of day, as
Figure 3 and the decomposition both show; neither test examines that, because deterministic
seasonality is not a unit root. Describing the series as stationary without this
qualification would mislead. Figure 7 shows rolling mean and standard deviation over a
one-day window, which makes the level stability visible while the within-day variation
remains.

The very high lag-1 autocorrelation carries a second implication for the experimental
design. A model can achieve a low one-step-ahead error simply by reproducing its most
recent input, and would appear successful while having learned nothing. Persistence is
therefore reported as a baseline in every results table, and Section 6 includes an explicit
check for whether any model has collapsed to it.

## 3.6 Supporting evidence: spectral analysis

Figure 8 shows the periodogram against period in hours. Power is concentrated at
**24.00 hours**, as expected, with a substantial secondary peak at **12.00 hours** and a
further peak near 165 hours corresponding to the weekly cycle.

The 12-hour peak is not an artefact. It indicates that the daily cycle is not a single
sinusoid — it has structure within the day, consistent with distinct morning and evening
activity. This has a direct consequence for model specification: a harmonic regression
using a single Fourier pair for the daily period would capture the envelope of the daily
cycle while missing its shape. At least two daily harmonics are required, and the harmonic
order is selected empirically in Section 5 rather than assumed.

## 3.7 Supporting evidence: anomalies and the holiday calendar

Intervals where a seasonal-naive predictor fails unusually badly were identified, on the
reasoning that periods difficult for the simplest seasonal model are likely to be difficult
for all of them, and that identifying them in advance converts the later failure analysis
from post-hoc explanation into a testable prediction.

The detection method required adjustment. Forecast errors on this series are strongly
heteroscedastic: the standard deviation of the seasonal-naive residual varies by a factor
of **25 between the quietest and busiest hours** of the day. A single robust scale
estimated over the whole series is therefore determined by the quiet hours and flags every
busy one — at a threshold of four robust standard deviations it marked 12.7% of all
intervals, which identifies nothing. Estimating the scale separately for each position in
the daily cycle asks the appropriate question, namely whether an observation is unusual
*for that time of day*. With 62 days of history, each of the 144 positions has 62
observations, sufficient for a stable median and median absolute deviation. A `log1p`
transform was evaluated as an alternative remedy and rejected: it reduces the spread ratio
to 2.0 but still flags 2.85%, and since the study reports absolute-error metrics the
absolute scale is the appropriate one on which to judge deviations.

Under the per-position scale, **152 intervals are flagged**, 1.73% of the 8,784
intervals that can be evaluated (the first day provides no seasonal-naive comparison). Holidays account for
12.9% of the days in the period but carry **23.0%** of the flagged intervals — an
enrichment of **1.78×**, significant at p = 4.3 × 10⁻⁴ under a binomial test. Both
Milan-specific dates appear: Sant'Ambrogio on 7 December, the city's patron saint's day and
a municipal holiday coinciding with the opening of the La Scala season, and the Immacolata
on 8 December. A national holiday calendar would have missed the former.

This justifies including a holiday indicator among the calendar features, since a model
given only day-of-week has no means of anticipating a Wednesday that behaves like a Sunday.
It also motivates the choice of held-out stress period: 23 December to 1 January contains
four of the eight holidays in the observation window, and is reserved for failure analysis
and never used for tuning.

One case resists explanation. The single worst day is **Monday 2 December**, with 17 flagged
intervals — more than Christmas Day (9) or New Year's Day (13) — and it is not a holiday.
No cause has been identified. It is carried into the failure analysis in Section 6 rather
than omitted.

## 3.8 Implications for the forecasting approach

The exploratory analysis establishes six constraints that the modelling approach must
satisfy, each traceable to a measurement.

1. **Two seasonal periods operate simultaneously** (82.9% and 10.0% of variance), so the
   seasonal model must represent both. Seasonal ARIMA cannot, and at s = 144 is in any case
   intractable.
2. **The daily cycle is not sinusoidal** — the 12-hour spectral peak requires at least two
   Fourier harmonics for the daily period.
3. **No differencing is required for a stochastic trend** (ADF and KPSS agree across all
   three transformations), fixing d = 0.
4. **Lag-1 autocorrelation of 0.987 makes persistence a demanding baseline**, and creates a
   risk that a flexible model collapses to reproducing its input. Both a baseline and an
   explicit check are required.
5. **The autocorrelation peaks at 144, 288, 432, 720, 864 and 1,008** identify the lag set
   for a feature-based model empirically rather than by convention.
6. **Variance scales with level.** The correlation between daily mean and daily standard
   deviation is +0.947 on the raw scale and +0.265 after a `log1p` transform, which
   justifies the variance-stabilising transform applied before model fitting.

Areas differ by roughly fivefold in mean volume and sixfold in peak-to-trough ratio, so
cross-area comparison requires a scale-free metric; MASE is used for that purpose [10],
with MAE, RMSE and MAPE reported per area.

---

## Notes for revision

- **Figure numbering** assumes Figures 1–8 map to `report/figures/01`–`08` in order; renumber if
  the final report includes figures from other sections ahead of these.
- **Citation numbers** follow `report/references.md`.
- **Section 3.3** was verified against the Milano Grid geometry rather than left as
  inference; `src/geo.py` performs the lookup and `tests/test_geo.py` pins it. The
  landmark distances establish where each cell is, not what drives its traffic, and the
  text says so.
- **The AI-use disclosure required by the brief is not yet written.**
