# Roadmap & Prioritisation

Built in tiers so there is always a complete, demoable project, even if later tiers
run out of time.

## Tier 1 — MVP (build and finish this first)
- [x] Synthetic event data generator (users + events)
- [x] ETL: raw -> clean -> user_daily_activity -> user_features
- [x] Data quality report (duplicates, missing IDs, invalid timestamps, etc.)
- [x] SQL analytics layer (CTEs, window functions) cross-validated against Python
- [x] North Star metric + KPI hierarchy
- [x] Funnel analysis (onboarding -> first AI interaction -> meaningful task)
- [x] Cohort & retention analysis (signup-month cohorts, D1/D7/D30)
- [x] A/B experiment: AI-assisted onboarding vs control, full statistical writeup
- [x] AI feature analytics: adoption, quality (ratings), cost per request/user
- [x] Business impact: incremental revenue vs incremental AI cost, ROI
- [x] Streamlit dashboard (6 pages) — confirmed working (user-verified via Docker deployment)
- [ ] Case study write-up (5-8 pages) — skeleton + skill-alignment table in place, still needs your real narrative

## Tier 2 — only after Tier 1 is fully working end-to-end
- [x] User segmentation (rule-based tiers + K-Means, with an honest comparison of whether clustering adds value over the simple rules)
- [x] Experiment segmentation (device, acquisition channel, country -- surfaced a genuine reversed-effect case in Canada worth investigating, not silently averaged away)
- [x] FastAPI backend serving the same analytics as endpoints (9 endpoints; confirmed working — user-verified via Docker deployment)
- [x] Dockerfile + docker-compose (3 services: pipeline, api, dashboard; confirmed working — user-verified)
- [ ] Basic GitHub Actions (lint + full pipeline + pytest on push; YAML-validated, not confirmed run on a real GitHub runner yet)
- [x] Deployment — completed via Docker (`docs/deployment.md` covers cloud options too, if you want a public link beyond local Docker)

## Tier 3 — nice-to-have, skip unless time allows
- [x] Rule-based recommendation engine (`src/recommendations/engine.py`) -- 3 rule categories, evidence-backed, confidence-labelled, verified against real data
- [x] RICE prioritisation scoring (`src/recommendations/rice_scoring.py`) -- 5 initiatives, Reach/Confidence grounded in real data where possible, Impact/Effort/other-Confidence disclosed as analyst estimates
- [x] Demo video script written (`docs/demo_video_script.md`) -- the actual video is yours to record

## Why this order
The A/B experiment + business impact section is the centrepiece for a business/data
analyst admissions portfolio — it proves you understand causal inference, not just
descriptive stats. Everything in Tier 1 exists to build up to and support that
section. Tier 2/3 items are polish and engineering signal, not analytical signal —
valuable, but not at the cost of leaving Tier 1 unfinished.
