# AI Product Intelligence & Growth Analytics — InsightAI

**Status: Tier 1 (MVP) complete and verified. Tier 2 complete and confirmed
working (dashboard, FastAPI, and Docker deployment all user-verified). Tier 3
complete at the code level** (recommendation engine, RICE scoring, demo
video script) — logic verified against real data the same way as every
other module; the demo video itself is the one deliverable that's yours to
actually record. Section 3 documents what was built, why, and exactly what's
been proven to work vs. what still needs your confirmation.

---
### 🚀 Live Demo

**[Open the Live Streamlit Dashboard](https://ai-appuct-analyst-4huugav44koj9kvvntrygq.streamlit.app/)**

## 1. The problem this project answers

InsightAI is a fictional AI-powered productivity/knowledge SaaS product.
Product leadership has launched an AI assistant feature and wants to know:

> **Is the AI feature actually improving the product, and should we invest
> further in it?**

That's a business question, not just a modelling exercise — so the project
is built to answer it with evidence: funnel/retention analysis to find where
users struggle, a randomised experiment to establish causal impact, and a
cost/ROI model to judge whether the feature is economically worth it.

## 2. Data disclosure (read this first)

**All data in this project is synthetically generated.** No real user,
company, or product data is used or implied anywhere. This isn't a caveat
buried in fine print — it's a design principle: every number this project
produces is illustrative of *methodology*, not a claim about any real
company's performance. Exactly how the data is generated, and every
assumption baked into it, is documented in Section 5 below and in
`src/ingestion/generate_synthetic_data.py`.

---

## 3. What Tier 1 actually contains, module by module

This is the part most repos skip — here's what each file does, why it's
built the way it is, and what happened when it was run.

### 3.1 `src/ingestion/generate_synthetic_data.py` — the data generator
Creates two tables from scratch: `users.csv` (3000+ fake users with country,
device, acquisition channel, plan, experiment group) and `events.csv` (every
action each user took: signup, onboarding, project creation, AI queries,
subscriptions, etc.).

This isn't random noise. Specific, disclosed behavioural rules are coded in:
- Users assigned to the **treatment** group (AI-assisted onboarding) get a
  deliberate **+9 percentage point activation-probability lift** over control.
  This is the "ground truth" effect that the A/B test module (3.7) is supposed
  to *discover* statistically — it's there so we can verify the statistics
  actually work, not just that they run without crashing.
- AI adoption and retention are correlated, but **noisily** — some retained
  users never touch AI, some heavy AI users still churn. Real product data is
  never perfectly clean, and a generator that produces a "too clean" signal
  would make the whole project's statistical story fake.
- Small, known data-quality defects are injected on purpose: ~0.3% duplicate
  events, ~0.08% missing user IDs, ~0.02% corrupted timestamps — so the data
  quality module (3.3) has real problems to catch, instead of reporting
  "0 issues found" on data that was never actually dirty.

**Verified output** (n=3000 users, seed=42): 41,425 raw events generated.

### 3.2 `src/preprocessing/etl.py` — the cleaning pipeline
Raw → clean → analytical tables, in three explicit steps:
1. **`clean_events()`** — drops duplicate `event_id`s, drops rows with null
   `user_id`, drops events with impossible timestamps (outside 2020–2030).
2. **`build_user_daily_activity()`** — one row per user per day: event count,
   session count, AI-event count.
3. **`build_user_features()`** — one row per user: did they activate? are
   they an AI adopter? did they subscribe? how many AI queries/ratings?

**Verified output:** 41,425 → 41,261 rows (164 removed) — meaning the cleaning
step actually found and removed exactly the defects injected in 3.1. This
match is itself a validation check: if the numbers didn't line up, something
would be wrong with either the generator or the cleaner.

### 3.3 `src/quality/data_quality.py` — the data quality report
Produces a plain report: total events, % duplicates, % missing user IDs, %
invalid timestamps, % events occurring before signup (an impossible sequence).

**Verified output:**
```
Total events:         41,425
Duplicate events:     123 (0.297%)
Missing user IDs:     33 (0.08%)
Invalid timestamps:   8 (0.019%)
Events before signup: 0 (0.0%)
```
These percentages match what was deliberately injected in 3.1 — proof the
detection logic works, not just that it prints something.

### 3.4 `src/metrics/funnel.py` — funnel analysis
Tracks users through: `signup → onboarding_started → onboarding_completed →
project_created → ai_assistant_opened → output_saved`, computing conversion
from the previous stage and from the very start, both overall and split by
`experiment_group`. The `signup` stage denominator is pulled from the
canonical `users` table, not the `signup` *event* — see Section 6 for why.

**Verified output (overall, post-fix):**
| Stage | Users reached | Conv. from start |
|---|---|---|
| signup | 3,000 | 100% |
| onboarding_started | 2,536 | 84.5% |
| onboarding_completed | 1,689 | 56.3% |
| project_created | 1,350 | 45.0% |
| ai_assistant_opened | 730 | 24.3% |
| output_saved | 336 | 11.2% |

**Two real bugs were caught and fixed here during validation** (both are
worth being able to explain in an interview, exactly because they show real
debugging, not a pipeline that worked perfectly on the first try):
1. An earlier version of the generator reused the `project_created` event
   name to also mark generic "return visits" for retention simulation, which
   made `project_created`'s conversion exceed 100% of the previous stage —
   an impossible funnel. Fixed by giving return-visits their own `app_opened`
   event, excluded from the funnel definition.
2. The funnel's `signup` stage was originally counted from the `signup`
   *event* (2,997) rather than the canonical `users` table (3,000) — 3
   treatment users lost their signup event during ETL cleaning while still
   being valid, assigned users. This silently shrank the denominator and
   made the treatment-arm funnel inconsistent with the A/B test's population.
   Fixed by pulling the signup stage's count from `users` specifically, in
   both `compute_funnel()` and the equivalent SQL query — see Section 6 for
   the full principle this established.

### 3.5 `src/metrics/retention.py` — retention & cohort analysis
Computes D1/D7/D14/D30 retention, signup-month cohort retention curves, and a
behavioural comparison (AI adopters vs. non-adopters; activated vs. not).

**Every result here is explicitly labelled "observational association, not
causal"** — this is a deliberate methodological rule carried through the
whole project (see Section 6). Retention correlating with AI adoption does
NOT mean AI adoption *causes* retention; only the randomised experiment (3.7)
can support that stronger claim.

**Verified output:** D30 retention was 22.9% for AI adopters vs. 9.9% for
non-adopters — a real, noticeable difference, reported as an association.

### 3.6 `src/metrics/kpi.py` — North Star + KPI hierarchy
Defines **North Star Metric = Weekly Active Users completing a meaningful
AI-assisted task** (operationalised as: user has an `ai_response_received`
event that week), plus supporting KPIs across acquisition, activation,
engagement, monetisation, and AI-specific metrics — following the same
structure as Google's HEART framework (goals → user-centred metrics), not a
random pile of 30 numbers.

### 3.7 `src/experimentation/ab_test.py` — the A/B test (the centrepiece)
Compares control (standard onboarding) vs. treatment (AI-assisted onboarding)
on activation rate, using:
- Two-proportion z-test → p-value
- 95% confidence interval on the absolute lift
- Cohen's h effect size (so a "significant but tiny" effect isn't mistaken
  for something worth shipping)
- A sample-size calculator for planning future experiments
- An `interpret()` function that deliberately avoids "p<0.05 therefore
  launch" — it weighs significance, effect size, and guardrails together

**Verified output:**
```
Control activation:    51.72%  (n=1,512)
Treatment activation:  60.95%  (n=1,488)
Absolute lift:         +9.23 percentage points
Relative lift:         +17.86%
95% CI:                [5.70, 12.77] pp
p-value:               <0.001
Cohen's h:              0.186
```
The experiment successfully **recovered the ~9pp effect that was deliberately
built into the generator** in 3.1 — this is the single most important
validation in the whole project: it proves the statistical pipeline correctly
detects a known true effect, rather than just producing plausible-looking
numbers.

### 3.8 `src/ai_analysis/ai_feature_metrics.py` — AI feature analytics
Adoption rate, average queries per adopter, a response/rating-rate proxy for
quality (explicitly labelled as a proxy — there's no real 1–5 satisfaction
score simulated yet, see Section 7), and a disclosed cost model
(`$0.012/query`, a stated assumption, not real billing data).

**Verified output:** 24.3% AI adoption, 11.7 avg queries/adopter, ~$103 total
AI cost across 3,000 users (~$0.034/user).

### 3.9 `src/business_impact/roi.py` — business impact / ROI
Compares total AI cost against illustrative subscription revenue (a disclosed
`$29/month` ARPU assumption), producing cost-as-%-of-revenue and an ROI
figure. Explicitly does **not** claim the revenue is *caused* by AI usage —
it's a side-by-side cost/revenue comparison, not an attribution model.

### 3.10 `sql/analytics_queries.sql` + `src/sql_layer/` — the SQL layer
This is real, hand-written SQL (CTEs and window functions throughout — `LAG`,
`FIRST_VALUE`, `NTILE`, `ROW_NUMBER`), not pandas `.groupby()` calls translated
into SQL-shaped syntax. Six queries: funnel with window-function conversion
rates, cohort retention, A/B lift computed entirely in SQL, AI-adoption vs.
retention, quartile-based engagement segmentation, and time-to-activation.

`src/sql_layer/load_to_sqlite.py` loads the processed CSVs into a real SQLite
database (chosen because it needs zero extra services — swap the connection
string for PostgreSQL/DuckDB if you want a production-style setup later).
`src/sql_layer/run_queries.py` runs and prints all six.

**Verified output:** every number produced by SQL matches the equivalent
Python computation exactly — e.g. the SQL A/B query independently returned
51.72% vs. 60.95% activation, identical to the Python `ab_test.py` result,
and the SQL funnel's signup stage correctly reads 3,000 from the `users`
table (see Section 6 for why this specific number matters). This
cross-validation between two independent code paths is a genuine correctness
signal worth mentioning in interviews.

### 3.11 `dashboard/app.py` — the Streamlit dashboard
Six pages: Executive Overview, Funnel, Retention & Cohorts, Segmentation, AI
Feature, and Experiment & Business Impact, with device-based filtering. The
Segmentation page (added in Tier 2) lets you interactively pick the number of
K-Means clusters and see the rule-based-vs-clustering comparison live.
**Not yet run in this build environment** — the sandbox used to build this
project has no internet access, so `streamlit` couldn't be installed here.
You'll need to confirm it runs on your own machine (Section 4, step 5) — if
anything breaks, bring the error back and we'll fix it.

### 3.12 `tests/` — automated tests
`test_pipeline.py` checks the ETL cleaning logic and the A/B statistical
functions. `test_sql_layer.py` checks the SQLite loader and confirms the
funnel is monotonically non-increasing and activation counts never exceed
user counts. `test_segmentation.py` checks the rule-based tiers and K-Means
clustering, including a regression guard for the "identical suggestion for
every cluster" bug caught during development (Section 3.15).
`test_segment_experiment.py` checks the experiment-segmentation logic,
including that a reversed effect in one subgroup is actually detected, not
averaged away. `test_api_logic.py` checks every FastAPI endpoint's underlying
logic and confirms every payload is JSON-serialisable — it deliberately
doesn't spin up FastAPI itself (see Section 3.17). `test_recommendations.py`
checks the recommendation engine's rule logic (including that a heterogeneity
caveat correctly downgrades confidence) and the RICE scoring formula. Every
assertion across all six files was manually verified against real output in the
build sandbox (no `pytest` available there either — but the logic was run by
hand and passed); run `pytest tests/ -v` yourself to get the real, automated
pass/fail report.

### 3.13 `docs/project_specification.md` and `docs/roadmap.md`
The spec doc is written **from the implementation**, not before it — schema,
event taxonomy, KPI definitions, experiment design, and every disclosed
assumption, plus a checklist of what counts as "Tier 1 done." The roadmap doc
tracks Tier 2 (segmentation done; FastAPI, Docker, deployment pending) and
Tier 3 (recommendation engine, RICE scoring, demo video) — deliberately
sequenced so Tier 1 stood as a complete, demoable project on its own before
any of Tier 2 was added.

### 3.14 `docs/case_study.md`
A skeleton for your actual 5-8 page write-up, including a **skill-alignment
table** mapping your existing portfolio (ML/AI systems, NLP/RAG, calibration
research) against what this project specifically adds (SQL, experimentation,
product analytics, business/ROI framing) — meant to be dropped directly into
your SOP or referenced in interviews.

### 3.15 `src/segmentation/segment_users.py` — user segmentation (Tier 2)
Two segmentation approaches, deliberately built side by side so you can judge
whether the more complex one earns its place, rather than using K-Means
just to say "I used K-Means":

1. **Rule-based tiers** — explainable thresholds (median session count,
   subscription status, AI adoption) producing tiers like "Power users,"
   "Explorers (low engagement)," "Never activated." Thresholds are computed
   from the dataset's own median rather than hardcoded constants, so they
   stay meaningful if you regenerate data at a different scale.
2. **K-Means clustering** (k=4 default, adjustable) on behavioural features
   (sessions, events, active days, projects, documents, AI queries),
   standardised before clustering. Each cluster is profiled (average
   behaviour, AI adoption %, subscription %, activation %) and given a
   suggested product action, using thresholds relative to that run's own
   cluster medians rather than fixed percentages — a hardcoded ">50%
   subscribed" rule would never fire on a dataset where the max subscription
   rate across clusters is 25%, silently producing identical, uninformative
   suggestions for every cluster (a real issue caught and fixed during
   development).

`compare_segmentations()` then gives an honest verdict on whether the
clustering surfaced anything the simple rules didn't.

**Verified output** (n=3000, seed=42): rule-based tiers split into 1,361
"Engaged non-AI," 1,317 "Explorers," 296 "Power users," 20 "Never activated,"
6 "AI adopters (light)." K-Means (k=4) found a 24.3pp spread in subscription
rate across clusters — reported as "modest," i.e. mostly confirming the
simpler tiers rather than revealing a hidden segment. That honest verdict is
itself worth keeping in the write-up: it shows judgement about when a more
sophisticated method is/isn't adding value, rather than defaulting to ML
everywhere.

### 3.16 `src/experimentation/segment_experiment.py` — experiment segmentation (Tier 2)
Checks whether the A/B effect (3.7) holds across subgroups — device,
acquisition channel, country — rather than reporting one overall number and
assuming it applies uniformly. Segments with fewer than 30 users per arm are
explicitly flagged as "too small for a reliable test" instead of reporting an
unstable p-value from a tiny sample. A `summarize_heterogeneity()` function
gives an honest verdict rather than letting you cherry-pick the most
interesting-looking cut.

**Note on scope:** the original plan asked for "new vs. existing users" and
"free vs. paid" cuts too. Both were deliberately dropped: every synthetic
user is new at signup (there's no returning-user population to compare
against), and `plan` is an *outcome* of the funnel, not a pre-existing trait
— splitting the experiment by it would condition on a post-treatment
variable and bias the comparison. Documented here so it reads as a decision,
not an oversight.

**Verified output** (n=3000, seed=42): the effect was directionally
consistent across device and acquisition channel (lift ranged 4.9–11.9pp
depending on channel). **Canada showed a near-zero/slightly negative lift
(-0.19pp, p=0.97, n≈150/arm)** — correctly flagged by
`summarize_heterogeneity()` as "at least one segment shows a lift in the
opposite direction, warrants investigation," rather than being silently
averaged into the overall +9.23pp figure. With this sample size that's very
plausibly noise, not a real reversal — but the point of this module is that
you'd want to know that before recommending a blanket global rollout, and
re-check it once you scale the data up.

### 3.17 `api/main.py` — FastAPI backend (Tier 2)
Nine GET endpoints (`/health`, `/metrics`, `/funnel`, `/retention`,
`/cohorts`, `/cohorts/behavioural`, `/segments`, `/experiments`,
`/ai-feature`, `/business-impact`) that wrap the exact same functions used by
the CLI scripts and the dashboard — the API doesn't duplicate any analysis
logic, so a metric definition only ever changes in one place. `/funnel` and
`/experiments` both accept an optional `segment_by` query parameter, backed
by the same segmentation/experiment-segmentation modules above.

**What was actually verified, and what wasn't:** `fastapi`/`uvicorn` could
not be installed in this sandbox (no internet), so the HTTP layer itself —
routing, request parsing, the actual server — has never been started. What
*was* verified: every endpoint's underlying logic was called directly
against real data (bypassing the FastAPI decorators) and its output was
confirmed to be valid, structured, and JSON-serialisable — including a
specific check that `numpy.float64`/`numpy.int64` values (a common source of
silent JSON-serialisation failures) serialise correctly here. `python -m
py_compile api/main.py` also confirms there are no syntax errors. Run
`uvicorn api.main:app --reload` yourself and report any error — the most
likely failure mode at this point is a FastAPI-version-specific issue, not a
logic bug.

### 3.18 `docker/Dockerfile` + `docker-compose.yml` (Tier 2)
One shared image (`docker/Dockerfile`) used by three services in
`docker-compose.yml`: `pipeline` (runs the generator + ETL once, then exits),
`api` (FastAPI on :8000), and `dashboard` (Streamlit on :8501) — `api` and
`dashboard` wait for `pipeline` to finish via
`condition: service_completed_successfully` before starting. **Not built or
run** — no `docker` binary was available in this sandbox. The YAML was
validated for correct syntax (`yaml.safe_load` parses it without error) but
`docker compose up --build` has never actually been executed. Run it
yourself; if a service fails to start, the compose logs (`docker compose logs
<service>`) will point at exactly which step broke.

### 3.19 `.github/workflows/ci.yml` — GitHub Actions CI (Tier 2)
Runs on every push/PR to `main`: installs dependencies, lints with flake8
(errors only — style nitpicks don't fail the build), runs the full data
pipeline (generator → ETL → SQL layer) so a broken pipeline step fails CI
directly rather than only failing a unit test in isolation, runs the pytest
suite, and compile-checks both `api/main.py` and `dashboard/app.py`. **Not
yet run on a real GitHub Actions runner** — the YAML was validated for
syntax, and every step mirrors exactly what was manually verified in this
sandbox (Section 4), but you'll see the first real run on your first push.

### 3.20 `docs/deployment.md` (Tier 2)
A deployment guide covering three paths: Streamlit Community Cloud (fastest,
dashboard-only, free — recommended for what actually goes in your SOP/CV),
Render/Railway (API + dashboard, more control), and running Docker Compose
purely locally as a live-demo fallback that needs no cloud account at all.
**Confirmed working** — Docker deployment has been completed and verified.

### 3.21 `src/recommendations/engine.py` — rule-based recommendation engine (Tier 3)
Three independent rule categories, each reading real numbers computed
elsewhere in the project rather than inventing new analysis: (1) flags the
funnel's biggest drop-off stage as needing investigation; (2) turns the A/B
test result into a rollout/hold recommendation, with confidence downgraded
to "Medium" if the experiment-segmentation heterogeneity check (3.16) found
a reversed effect in any subgroup; (3) checks whether AI adoption and ROI
jointly justify continued investment. Every recommendation carries its
trigger condition and the exact evidence that fired it — auditable, not a
black box — and a confidence label based on how strong that evidence is, not
a made-up number.

**Design principle carried over from the original brief:** this surfaces
evidence and a structured recommendation; it does not autonomously decide
anything. A human product manager is still the one who acts on it.

**Verified output** (n=3000, seed=42): correctly flagged `output_saved`
(46.03% conversion from the previous stage) as the biggest drop-off; flagged
the A/B lift (+9.23pp, p<0.001) as "High confidence, roll out" with correct
CI-based confidence logic; flagged 24.33% AI adoption + a very high ROI
(8,743% — see the honesty note below) as "continue investing."

**Honest flag on that ROI number:** 8,743% is an artifact of the illustrative
`$0.012/query` cost assumption being extremely cheap relative to the
illustrative `$29/month` ARPU — not a claim that a real AI feature would be
this profitable. The dashboard's Recommendations page states this
explicitly rather than letting an inflated number look more authoritative
than it is.

### 3.22 `src/recommendations/rice_scoring.py` — RICE prioritisation (Tier 3)
Scores 5 hypothetical initiatives (improve onboarding, expand AI assistant,
reduce latency, improve collaboration, improve pricing) using
Reach × Impact × Confidence ÷ Effort. **Disclosed limitation, stated in the
module's own docstring rather than hidden:** RICE scores for untested
initiatives are inherently partly subjective — Confidence in particular is a
judgement call dressed as a number. This implementation grounds Reach and
Confidence in real project data wherever an initiative actually maps to
something measured (the onboarding initiative's Confidence comes directly
from the A/B test's p-value; latency's Confidence is explicitly labelled
"not measured in this dataset at all" since latency isn't simulated). Every
row's `confidence_basis` column states in plain language whether that row's
number is grounded or an estimate.

**Verified output:** "Improve onboarding" ranked #1 (RICE score 2282.4),
consistent with the recommendation engine's #1 flag above — the two Tier 3
modules independently agree on the top priority, which is a genuine (if
expected, since they both read the same funnel data) cross-check.

### 3.23 `docs/demo_video_script.md` (Tier 3)
A shot-by-shot outline (not a verbatim script) for a 5-7 minute demo video —
what to show, what to say, and explicit guidance on maintaining the same
honesty (disclosing synthetic data, disclosing the inflated ROI assumption)
on camera that the rest of this project maintains in writing. Recording the
actual video is the one Tier 3 deliverable that has to be yours.

---

## 4. How to run this, step by step

```bash
# 0. Unzip the project and enter it
cd ai-product-intelligence

# 1. (Recommended) create a virtual environment
python3 -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate the synthetic dataset
python src/ingestion/generate_synthetic_data.py --n-users 5000
#    (bump --n-users higher, e.g. 20000, once you confirm everything works —
#     bigger numbers make the dashboard and statistics feel more substantial)

# 4. Run the ETL (cleaning) step
python src/preprocessing/etl.py

# 5. Run the data quality report
python src/quality/data_quality.py

# 6. Build the SQL database and run the SQL analytics layer
python src/sql_layer/load_to_sqlite.py
python src/sql_layer/run_queries.py

# 7. Run the individual analysis modules (each prints its own results)
python src/metrics/funnel.py
python src/metrics/retention.py
python src/metrics/kpi.py
python src/segmentation/segment_users.py
python src/experimentation/segment_experiment.py
python src/ai_analysis/ai_feature_metrics.py
python src/business_impact/roi.py
python src/experimentation/ab_test.py
python src/recommendations/engine.py
python src/recommendations/rice_scoring.py

# 8. Run the automated tests
pip install pytest
pytest tests/ -v

# 9. Launch the interactive dashboard
streamlit run dashboard/app.py

# 10. (Tier 2) Launch the FastAPI backend, in a separate terminal
uvicorn api.main:app --reload
#     then open http://127.0.0.1:8000/docs for interactive API docs

# 11. (Tier 2, optional) Run everything via Docker Compose instead of steps 2-10
docker compose up --build
#     API:       http://localhost:8000/docs
#     Dashboard: http://localhost:8501
```

If any step errors out, copy the exact error message back here and we'll
debug it together — several of the fixes already in this codebase (the
`project_created` bug, the parquet→CSV swap for environments without
`pyarrow`) came from exactly this kind of iteration. Steps 9-11 are the ones
most likely to need a fix on first run: they were never actually executed in
the build sandbox (no internet access there), unlike everything before them.

---

## 5. Methodological rule (carried through every module)

**Correlation is never presented as causation.** Every retention/cohort
finding is explicitly labelled *observational association*. Only the A/B
experiment (3.7) — because assignment is randomised — supports causal
language, and even there, conclusions weigh effect size and (eventually)
guardrail metrics, not just a p-value threshold. If you extend this project,
keep this rule; it's one of the strongest signals of analytical maturity in
the whole thing.

---

## 6. Data-integrity principle (methodological rule, added after a real validation fix)

**The `users` table is the canonical population for signup and experiment
assignment. Event tables measure downstream behavioural stages only.**

This was added after catching a real discrepancy: a small number of users
(3, in the seed=42 / n=3000 run) can lose their `signup` *event* during ETL
cleaning while still being valid, assigned users in the canonical `users`
table — e.g. a corrupted row removed by deduplication. Using the event count
as the funnel's signup denominator silently undercounted the true starting
population (2,997 instead of 3,000), which also made the treatment-arm
funnel numbers (1,485 vs. the correct 1,488) inconsistent with the A/B test's
population (which was already correctly pulling from `users`, not events).

**Fix applied:** `compute_funnel()` (`src/metrics/funnel.py`) and SQL query 1
(`sql/analytics_queries.sql`) now both use the `users` table for the `signup`
stage specifically, while every later stage still comes from `clean_events`
as before. This is a data-integrity artifact of the cleaning pipeline, not a
finding about real user behaviour or an A/B assignment problem — it should
never be reported as one.

**Rule going forward:**
- `users` → canonical population, signup population, experiment assignment
- `events` / `clean_events` → behavioural events, downstream funnel stages
- `users` + `events` joined → user-level experiment and retention analyses

**Verified corrected funnel** (n=3000, seed=42):
| Stage | Overall | Control | Treatment |
|---|---|---|---|
| signup | 3,000 | 1,512 | 1,488 |
| onboarding_started | 2,536 | 1,268 | 1,268 |
| onboarding_completed | 1,689 | 782 | 907 |
| project_created | 1,350 | 619 | 731 |
| ai_assistant_opened | 730 | 334 | 396 |
| output_saved | 336 | 155 | 181 |

The A/B test result is **unchanged** by this fix (it was already correct):
control 51.72% vs. treatment 60.95% activation, +9.23pp lift.

---

## 7. What's deliberately out of scope (and what's still pending)

- **Actual cloud deployment** — Docker/API/dashboard code is written (Section
  3.17-3.20), but nothing has been deployed to Render/Railway/Streamlit Cloud
  from this sandbox (no accounts, no network). See `docs/deployment.md` for
  the guide; deploying is the one remaining Tier 2 action item, and it's
  yours to do since it needs real accounts and a real network connection.
- **A real AI response quality score** (1-5 rating / thumbs up-down value) —
  currently only *occurrence* of a rating event is tracked, not its value.
  Documented as a known gap in `docs/project_specification.md` §12.
- **Recommendation engine, RICE scoring, demo video** — Tier 3, lowest
  signal-per-effort, build last if time allows.

See `docs/roadmap.md` for the full tiering and current checklist status.

---

## 8. Repository structure

```
ai-product-intelligence/
├── data/                      # raw/ and processed/ (gitignored — regenerate locally)
├── notebooks/                 # exploratory analysis (empty — add your own EDA here)
├── sql/
│   └── analytics_queries.sql  # 6 tested CTE/window-function queries
├── src/
│   ├── ingestion/              # synthetic data generator
│   ├── preprocessing/          # ETL: raw -> clean -> analytical tables
│   ├── quality/                # data quality checks & report
│   ├── metrics/                # funnel, retention, KPI hierarchy
│   ├── experimentation/        # A/B test + experiment segmentation (Tier 2)
│   ├── ai_analysis/            # AI feature adoption/quality/cost
│   ├── business_impact/        # revenue vs cost, ROI
│   ├── segmentation/           # rule-based tiers + K-Means clustering (Tier 2)
│   ├── recommendations/        # rule-based engine + RICE scoring (Tier 3)
│   └── sql_layer/              # SQLite loader + query runner
├── api/
│   └── main.py                 # FastAPI backend, 9 endpoints (Tier 2)
├── docker/
│   └── Dockerfile              # shared image for pipeline/api/dashboard services
├── .github/workflows/ci.yml    # lint + pipeline + pytest on push (Tier 2)
├── dashboard/                 # Streamlit app (6 pages, incl. Segmentation)
├── tests/                     # pytest suite (pipeline, SQL, segmentation, API logic)
├── docs/
│   ├── project_specification.md  # schema, taxonomy, KPI/experiment definitions
│   ├── case_study.md             # your write-up skeleton + skill-alignment table
│   ├── deployment.md             # Streamlit Cloud / Render / Railway / Docker guide
│   ├── demo_video_script.md      # shot-by-shot outline for your demo video (Tier 3)
│   └── roadmap.md                # Tier 1/2/3 checklist
├── docker-compose.yml          # pipeline + api + dashboard, one command
├── requirements.txt
├── LICENSE
├── .gitignore
└── .dockerignore
```

---

## 9. Limitations

- Data is synthetic; behavioural patterns are simulated based on plausible
  SaaS assumptions, not observed real-world behaviour.
- The A/B experiment uses a known, deliberately-built-in ground-truth effect
  size, to demonstrate correct experimental methodology — not to claim a real
  product result.
- Revenue (`$29/month` ARPU) and AI cost (`$0.012/query`) are stated,
  illustrative assumptions, not derived from real pricing or billing data.
- AI response "quality" is currently a proxy (response/rating rate), not a
  simulated satisfaction score.
- The experiment-segmentation heterogeneity check (Section 3.16) is run on
  fairly small per-country samples (n≈150/arm) — the Canada anomaly is a
  candidate for investigation, not a confirmed finding; re-check it once you
  scale the data up.
- The FastAPI backend, Docker Compose setup, and CI workflow are code-complete
  and had their underlying logic verified, but their *runtime* behaviour
  (actually starting a server, actually building an image, actually running
  on a GitHub runner) has not been confirmed — see Section 3.17-3.19 for
  exactly what was and wasn't tested, and Section 4 steps 9-11 for what to
  run yourself.
- No deployment has actually happened yet (`docs/deployment.md` is a guide,
  not a confirmed live link) — this is the one remaining Tier 2 action item.

---

## 10. How to proceed from here

1. **Run the new Tier 3 modules** (`src/recommendations/engine.py`,
   `src/recommendations/rice_scoring.py`) and the new Recommendations
   dashboard page — steps 7 and 9 in Section 4 now include them.
2. **Write `docs/case_study.md`** with your real numbers, using the module
   walkthrough in Section 3 above as your source material.
3. **Record the demo video** using `docs/demo_video_script.md` as your outline.
4. **Optional, if you want a public link beyond your local Docker
   deployment**: follow `docs/deployment.md` for Streamlit Community Cloud,
   Render, or Railway.
5. **The project is now feature-complete across all three tiers.** From here
   it's refinement: scale the data up, tighten the case study narrative, and
   make sure you can defend every number out loud — an admissions reviewer
   or interviewer is far more likely to ask "why did you choose a
   two-proportion z-test" than to ask for a 21st module.
