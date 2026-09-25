# Project Specification v1.0 — AI Product Intelligence & Growth Analytics

*This spec is written retrospectively from the Tier 1 implementation, not
speculatively before it. Every schema field, event name, and metric definition
below matches what is actually implemented in `src/` and has been run against
real (synthetic) output. Where later phases will add or change something,
that is noted explicitly rather than assumed.*

## 1. Product
**InsightAI** — a fictional AI-powered productivity/knowledge SaaS platform.
Users register, complete onboarding, create projects, upload documents, use
an AI assistant, and optionally subscribe to a paid plan.

## 2. Business objective
Determine whether the AI assistant feature meaningfully improves activation,
retention, and monetisation — and whether its operational cost is justified
by the incremental value it creates.

## 3. Stakeholders (fictional, for narrative framing)
- Product leadership — deciding whether to expand AI investment
- Growth/analytics team — measuring funnel and retention health
- Finance — evaluating AI cost vs. revenue impact

## 4. User journey (as implemented)
```
signup → onboarding_started → onboarding_completed → project_created
  → document_uploaded → ai_assistant_opened → ai_query_submitted
  → ai_response_received → (ai_response_rated) → output_saved
  → (collaboration_invited) → (subscription_started) → (subscription_cancelled)
```
Parenthesised events are conditional/optional branches, not guaranteed for
every user. Exact branch probabilities are defined in
`src/ingestion/generate_synthetic_data.py::simulate_user_journey`.

## 5. Event taxonomy (as implemented)
| Event | Description |
|---|---|
| `signup` | User registers |
| `onboarding_started` / `onboarding_completed` | Onboarding funnel |
| `project_created` | First-time project creation (funnel stage only — NOT reused for return-visit activity; see §11 known design fix) |
| `document_uploaded` | Document added to a project |
| `ai_assistant_opened` | User opens the AI assistant |
| `ai_query_submitted` / `ai_response_received` | One AI interaction turn |
| `ai_response_rated` | User rated a response (binary occurrence only — no rating value simulated yet, see §12) |
| `output_saved` | User saved an AI output |
| `collaboration_invited` | User invited a collaborator |
| `subscription_started` / `subscription_cancelled` | Monetisation events |
| `app_opened` | Generic return-visit marker used only for retention simulation, deliberately excluded from funnel stages |

## 6. Database schema (as implemented)
```
users(user_id, signup_date, country, device, acquisition_channel,
      age_group, experiment_group, plan)

events(event_id, user_id, timestamp, event_name, session_id,
       platform, feature, experiment_group)
```
Processed/derived tables (`src/preprocessing/etl.py`):
```
clean_events            -- deduplicated, non-null user_id, valid timestamp range
user_daily_activity     -- user_id, date, n_events, n_sessions, ai_events
user_features           -- per-user: activated, ai_adopter, subscribed,
                           ai_query_count, ai_rating_count
```
`properties` (a free-form JSON column proposed in the original layout) was
**not implemented in Tier 1** — every event needed by the current analysis is
representable via `event_name` + `feature` alone. Adding `properties` is
deferred to Tier 2 if a future analysis genuinely needs it (e.g. AI query
text length, document type). Not adding unused columns is a deliberate choice,
not an oversight.

## 7. KPI definitions (as implemented, `src/metrics/kpi.py`)
- **North Star**: distinct users with an `ai_response_received` event, per week
- **Activation**: user has an `onboarding_completed` event
- **AI adoption**: user has an `ai_assistant_opened` event
- **Retention (day N)**: user has ≥1 event on exactly day N after signup
- **Conversion**: user has a `subscription_started` event

## 8. Experiment definition (as implemented, `src/experimentation/ab_test.py`)
- **Assignment**: 50/50 randomised at signup, stored as `users.experiment_group`
- **Control**: standard onboarding
- **Treatment**: AI-assisted onboarding (simulated as a +9pp activation-probability lift, see generator source)
- **Primary metric**: activation rate (`onboarding_completed`)
- **Statistical method**: two-proportion z-test, 95% CI on absolute lift, Cohen's h effect size
- **Guardrails**: not yet simulated in Tier 1 (see §12) — would be latency/error rate/cost-per-user in a full build

## 9. Synthetic data generation assumptions (`src/ingestion/generate_synthetic_data.py`)
Explicitly disclosed, not hidden:
- Treatment group gets a deliberate +9pp activation-probability lift (the
  ground-truth effect the A/B module is expected to recover statistically)
- AI adoption and retention are correlated but noisy — not a clean deterministic
  function, so retention analysis has genuine (if bounded) uncertainty to report
- Data quality issues (duplicate events ~0.3%, missing user_id ~0.08%, invalid
  timestamps ~0.02%) are injected deliberately so `src/quality/data_quality.py`
  has real defects to catch
- Revenue (`MONTHLY_ARPU_USD = 29.0`) and AI cost (`COST_PER_QUERY_USD = 0.012`)
  are illustrative constants, not derived from any real pricing data

## 10. Analytical questions this spec answers
1. Where do users drop off in the onboarding→AI-usage funnel? (`src/metrics/funnel.py`)
2. Do AI adopters retain better than non-adopters — as an association, not a causal claim? (`src/metrics/retention.py`)
3. Does AI-assisted onboarding *cause* higher activation? (`src/experimentation/ab_test.py` — the only module licensed to use causal language, because assignment is randomised)
4. Is AI usage high/valuable enough, and is its cost justified? (`src/ai_analysis/`, `src/business_impact/roi.py`)

## 11. Known design fixes (documented for transparency)
Two real issues were found and fixed during validation — kept here as a
record, not scrubbed from history, since being able to explain a real bug
and how it was caught is worth more in an interview than an untested-looking
clean history:

1. **Event name collision.** An earlier version of the generator reused the
   `project_created` event name for simulated return-visits (retention
   activity), which silently inflated the funnel's `project_created`
   conversion figure above 100% of the prior stage. Fixed by introducing a
   dedicated `app_opened` event for return-visit simulation that is excluded
   from `FUNNEL_STAGES`.
2. **Signup denominator mismatch.** The funnel's `signup` stage was
   originally counted from the `signup` *event* in `clean_events` (2,997),
   rather than from the canonical `users` table (3,000). Three treatment
   users lost their signup event during ETL cleaning (deduplication catching
   a corrupted row) while remaining valid, assigned users — so the
   event-based count silently undercounted the true population, and made the
   treatment-arm funnel (1,485) inconsistent with the A/B test's population
   (1,488, which was already correctly pulled from `users`). Fixed in both
   `compute_funnel()` (`src/metrics/funnel.py`) and SQL query 1
   (`sql/analytics_queries.sql`): the `signup` stage now always uses the
   `users` table as the starting population; every later stage still comes
   from `clean_events`. This is a data-integrity artifact of the cleaning
   pipeline, not a finding about real user behaviour or an A/B assignment
   problem, and must never be reported as either.
   **Rule established:** `users` = canonical population, signup population,
   experiment assignment. `events`/`clean_events` = downstream behavioural
   stages. `users` + `events` joined = user-level experiment/retention
   analyses.

## 12. Deferred to Tier 2 / Tier 3 (not gaps — deliberate sequencing)
- `ai_response_rated` currently records occurrence only; a 1-5 or thumbs up/down
  **value** is not yet simulated. Needed before any "AI quality score" claim
  beyond "engagement with feedback."
- Guardrail metrics (latency, error rate, cost/user) for the A/B test
- User segmentation via clustering (rule-based quartiles exist in
  `sql/analytics_queries.sql` query 5; K-Means is Tier 2)
- FastAPI backend, Docker, CI/CD, deployment
- Event `properties` JSON column, if a future analysis needs it

## 13. Tech stack (as implemented)
Python, pandas, numpy, scipy (stats), SQLite (via `sqlite3`, stdlib — no
external DB server required for Tier 1), Streamlit + Plotly (dashboard),
pytest. PostgreSQL/DuckDB swap-in is a Tier 2 deployment decision, not a
Tier 1 requirement.

## 14. Admission-oriented learning objectives
This project is explicitly designed to demonstrate the skills below, mapped
against what the author's existing portfolio (AI/ML systems, RAG, calibration
research, decision intelligence) already covers — see `docs/case_study.md`
§"Skill Alignment" for the full table:
- SQL: CTEs, window functions, cohort/funnel/experiment queries (§ this doc, `sql/analytics_queries.sql`)
- Statistical experimentation: proper A/B methodology, not just "p<0.05 → ship"
- Product analytics: funnels, cohorts, retention, KPI hierarchies
- Business framing: ROI, cost justification, not just model accuracy
- Data engineering hygiene: deliberately-flawed data caught and cleaned, not assumed clean

## 15. What constitutes a successful Tier 1 project
- [x] Pipeline runs end-to-end without manual intervention
- [x] Data quality issues are injected and then caught by the pipeline
- [x] Funnel, retention, and KPI numbers are internally consistent between
      the Python (`src/metrics/`) and SQL (`sql/analytics_queries.sql`) layers
- [x] The A/B test recovers a statistically significant result consistent
      with the deliberately-simulated ground truth effect
- [x] Every causal vs. associational claim is labelled correctly
- [ ] Case study written with real numbers (next step)
- [ ] Dashboard confirmed running in the author's own environment (author to verify — could not be tested in the build sandbox, which has no network access for `pip install streamlit`)
