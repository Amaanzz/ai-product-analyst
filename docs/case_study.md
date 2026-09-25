# AI Product Intelligence & Growth Analytics — Case Study

## Executive Summary

InsightAI is a fictional AI-powered productivity and knowledge SaaS product designed to help users organize projects, work with documents, and complete AI-assisted tasks. The central product question was:

> **Is the AI feature improving the product experience, and what evidence should guide further investment?**

I built an end-to-end product analytics and experimentation system to answer that question using a synthetic dataset of 20,000 users and 281,256 raw events. The pipeline covers data generation, data-quality validation, ETL, SQL analytics, funnel analysis, cohort retention, behavioural segmentation, randomized experimentation, AI feature economics, business-impact analysis, recommendation generation, RICE prioritisation, a FastAPI backend, and a Streamlit dashboard.

The analysis identified `output_saved` as the largest funnel bottleneck, with only **49.69%** of users reaching that stage from the previous stage. A randomized AI-assisted onboarding experiment produced an observed **+6.22 percentage-point activation lift**, with a 95% confidence interval of **[4.85, 7.59] percentage points** and p < 0.001. Country-level analysis showed positive observed treatment effects across all seven countries checked, ranging from **+3.59 pp to +9.34 pp**.

The AI feature had **25.26% adoption** in the final dataset. The project also estimated AI cost and illustrative ROI, but those economic figures depend on explicit synthetic assumptions and should not be interpreted as measured real-world revenue attributable to AI.

The resulting recommendation is therefore evidence-based but bounded: the experiment provides strong evidence within this synthetic dataset that AI-assisted onboarding is associated with higher activation under the randomized experiment design, while the broader business case requires real production data, measured AI quality, and validated revenue attribution before making a real-world investment decision.

---

## Product Context

### The fictional product

InsightAI is a fictional AI-powered productivity and knowledge SaaS platform.

A typical user journey is:

```text
Signup
   ↓
Onboarding
   ↓
Onboarding completion
   ↓
Project creation
   ↓
AI assistant interaction
   ↓
AI-generated output
   ↓
Output saved
   ↓
Collaboration / subscription
```

The product generates behavioural events such as signups, onboarding actions, project creation, document uploads, AI interactions, output saves, collaboration activity, and subscription events.

Because the product is fictional, all user and event data are synthetic. The purpose is to demonstrate the analytical workflow and decision-making framework rather than to claim findings about a real company.

---

## Skill Alignment

| Capability | Demonstrated in the project |
|---|---|
| Data Analytics | Data cleaning, transformation, KPI analysis, funnel analysis, retention, segmentation |
| SQL | Product metrics, funnel queries, cohort analysis, AI adoption and business-impact queries |
| Python | Data generation, ETL, analytics, statistical analysis, recommendation logic |
| Statistics | Confidence intervals, hypothesis testing, p-values, effect size and experiment analysis |
| Experimentation | Randomized A/B testing, segment-level analysis and treatment-effect comparison |
| Machine Learning | K-Means behavioural segmentation |
| AI / Product Analytics | AI adoption, usage, quality proxies, cost analysis and AI-assisted onboarding evaluation |
| Business Analytics | Revenue assumptions, cost analysis, ROI framing and prioritisation |
| Product Thinking | North Star metric, funnel diagnosis, experimentation and recommendation framework |
| API Development | FastAPI endpoints for analytics and recommendations |
| Data Visualisation | Interactive Streamlit dashboard with Plotly |
| Engineering Practices | Automated tests, Docker, CI workflow and deployment documentation |

---

## Data Architecture

```text
Synthetic Event Generation
        ↓
Raw Events
        ↓
Data Quality Validation
        ↓
ETL / Cleaning
        ↓
Feature Engineering
        ↓
SQLite Analytical Layer
        ↓
SQL Product Metrics
        ↓
Funnel / Retention / Segmentation
        ↓
Experimentation
        ↓
AI Feature Economics
        ↓
Recommendation Engine
        ↓
FastAPI
        ↓
Streamlit Dashboard
```

The final scaling run generated:

- **20,000 users**
- **281,256 raw events**
- **280,134 clean events after ETL**
- **1,122 rows removed during ETL**

The synthetic generator deliberately introduced data-quality problems such as duplicate events, missing user IDs and invalid timestamps so that the pipeline could demonstrate validation rather than assuming perfect source data.

The ETL stage checks for duplicate events, missing user IDs, invalid timestamps, impossible event sequences, users generating events before signup, inconsistent event data, and experiment-assignment issues.

A key integrity rule is that the `users` table is treated as the canonical population for signup and experiment-assignment analysis rather than relying exclusively on observed signup events.

---

## Product KPI Framework

### North Star Metric

> **Weekly Active Users completing a meaningful AI-assisted task**

Supporting KPI categories include acquisition, activation, engagement, retention, AI adoption, AI usage, AI quality proxies, monetisation, AI economics and experimentation.

The KPI framework deliberately separates activity metrics from outcome metrics so that the product is not optimized merely for increased AI usage.

---

## Funnel Analysis

| Stage | Users | Overall conversion | Previous-stage conversion |
|---|---:|---:|---:|
| Signup | 20,000 | 100.00% | — |
| Onboarding started | 17,013 | 85.06% | 85.06% |
| Onboarding completed | 11,369 | 56.84% | 66.83% |
| Project created | 9,145 | 45.73% | 80.44% |
| AI assistant opened | 5,053 | 25.27% | 55.25% |
| Output saved | 2,511 | 12.55% | **49.69%** |

The largest stage-to-stage drop occurs between **AI assistant opened** and **output saved**. This makes `output_saved` the primary funnel bottleneck identified by the analysis.

The funnel identifies where users are dropping off, but it does not establish why. Potential explanations such as response quality, unclear next actions, latency, workflow friction or insufficient perceived value require further instrumentation and experimentation.

---

## Cohort & Retention Analysis

| Group | D30 retention |
|---|---:|
| AI adopters | **21.55%** |
| Non-AI adopters | **10.34%** |

This is a descriptive observational comparison, not a causal estimate.

Users who adopt AI may differ from non-adopters in motivation, engagement, product intent or other characteristics. The randomized onboarding experiment is therefore used separately when evaluating causal evidence for activation.

---

## Behavioural Segmentation

The project implements two complementary approaches:

### Rule-based behavioural segmentation

Users are grouped according to AI usage intensity:

- Low
- Medium
- High
- Power

### K-Means clustering

K-Means is also implemented to identify behavioural groups from usage features. The dashboard allows comparison between rule-based segmentation and clustering.

The purpose is to support questions such as which users are highly engaged, which users use AI frequently, whether segments have different activation patterns, and whether experiment results behave consistently across user groups.

---

## AI Feature Evaluation

Final AI adoption was:

> **25.26% of users**

The analysis tracks total AI queries, AI responses, queries per adopter, response rate and rating rate.

Current AI quality measurement uses response and rating behaviour as **quality proxies**. It does not claim to measure semantic answer quality.

A production implementation should add task success rate, helpfulness, groundedness, hallucination rate, latency, error rate and cost per successful task.

---

## A/B Experiment

### Experiment question

> **Does AI-assisted onboarding increase activation compared with the standard onboarding experience?**

Users were randomly assigned to control or treatment.

| Group | Users | Activated | Activation rate |
|---|---:|---:|---:|
| Control | 9,906 | 5,320 | **53.70%** |
| Treatment | 10,094 | 6,049 | **59.93%** |

Observed treatment effect:

> **+6.22 percentage points**

95% confidence interval:

> **[+4.85 pp, +7.59 pp]**

Statistical significance:

> **p < 0.001**

Effect size:

> **Cohen's h ≈ 0.126**

The result provides strong statistical evidence of a difference in activation between treatment and control within this synthetic randomized experiment.

However, the synthetic generator deliberately embeds a positive treatment effect. Therefore, this validates the experimentation and statistical-analysis pipeline rather than demonstrating that a real-world AI onboarding feature would produce the same effect.

### Segment-level experiment analysis

Device-level observed lifts ranged from **+4.89 pp to +8.42 pp**.

Acquisition-channel observed lifts ranged from **+5.29 pp to +7.18 pp**.

Country-level observed lifts ranged from **+3.59 pp in India to +9.34 pp in Canada**. All seven countries checked showed a positive observed treatment difference in this synthetic dataset.

These subgroup analyses are secondary and exploratory.

---

## Business Impact

Final AI adoption:

> **25.26%**

The project estimates AI-related cost and compares that cost with synthetic subscription revenue assumptions.

The resulting illustrative ROI was approximately:

> **8,390.4%**

This number is intentionally labelled **illustrative**. It is not measured real-world ROI and should not be interpreted as evidence that AI generated that level of financial return.

The economic model depends on synthetic assumptions around subscription revenue, AI cost, user behaviour, monetisation and attribution.

A production implementation would require actual model/API costs, subscription revenue, incremental conversion attributable to the feature, retention or LTV impact, infrastructure costs and support costs.

---

## Product Recommendation Engine

### 1. Investigate the output-saving bottleneck

Only **49.69%** of users who opened the AI assistant progressed to saving an output.

Potential hypotheses include poor output usefulness, unclear next actions, weak save affordance, latency/errors or workflow mismatch. These are hypotheses, not established causes.

### 2. Evaluate AI-assisted onboarding through controlled rollout

The randomized experiment produced:

- **+6.22 pp activation lift**
- **95% CI: +4.85 to +7.59 pp**
- **p < 0.001**

Before a real production rollout, the experiment should be repeated using real users and real business metrics, with guardrails for AI cost, latency, errors, onboarding completion, retention, satisfaction and downstream revenue.

### 3. Continue investigating AI investment economics

The AI feature has 25.26% adoption and an illustrative positive economic model. However, the current dataset does not provide measured semantic quality or causal revenue attribution.

The next analytical chain should connect:

```text
AI Usage
   ↓
Task Success
   ↓
Retention
   ↓
Conversion
   ↓
Revenue
   ↓
Incremental Profit
```

---

## RICE Prioritisation

| Initiative | Reach | Impact | Confidence | Effort | RICE Score |
|---|---:|---:|---:|---:|---:|
| Improve onboarding reach | 17,013 | 2.0 | 90% | 2 | **15,311.7** |
| Improve pricing page / conversion flow | 20,000 | 1.0 | 40% | 2 | **4,000.0** |
| Expand AI assistant capabilities | 5,053 | 2.0 | 60% | 4 | **1,515.9** |
| Reduce AI response latency | 5,053 | 1.0 | 50% | 3 | **842.2** |
| Improve collaboration features | 1,600 | 0.5 | 50% | 3 | **133.3** |

Only some RICE inputs are directly measured. Impact, confidence and effort are partly analyst estimates. The project explicitly discloses this rather than presenting the scores as objective measurements.

---

## Dashboard & API

The Streamlit dashboard contains:

1. Executive Overview
2. Funnel Analysis
3. Retention & Cohorts
4. Segmentation
5. AI Feature Analysis
6. Experiment & Business Impact
7. Recommendations

FastAPI exposes:

```text
/health
/metrics
/funnel
/retention
/cohorts
/cohorts/behavioural
/segments
/experiments
/ai-feature
/business-impact
/recommendations
/rice-roadmap
```

This separates analytical computation from presentation and makes the project easier to extend.

---

## Engineering Validation

The final automated test suite passed:

> **32 tests**

The application was also containerized using Docker with separate services for the pipeline, API and dashboard.

The project includes:

- Docker Compose
- FastAPI
- Streamlit
- pytest
- GitHub Actions CI configuration
- deployment documentation

These components demonstrate that the workflow is reproducible rather than dependent on manually executed notebook cells.

---

## Limitations

### 1. Synthetic data

The dataset is generated rather than collected from real users. Numerical results demonstrate methodology rather than actual product behaviour.

### 2. Embedded experiment effect

The synthetic generator deliberately creates a positive treatment effect. The A/B result therefore demonstrates that the experimentation system can recover a known signal.

### 3. AI quality

Response and rating behaviour are only proxies. Semantic correctness, hallucination, groundedness and task success are not yet measured.

### 4. Revenue attribution

The ROI calculation depends on synthetic revenue and cost assumptions. No causal revenue impact is claimed.

### 5. Observational retention

The difference between AI adopters and non-adopters is descriptive and should not be interpreted as a causal estimate.

### 6. Segment-level analysis

Segment-level experiment results are exploratory and should be validated with larger real-world samples and an appropriate multiple-comparison strategy.

### 7. RICE estimates

Several RICE inputs are analyst estimates because the event schema does not contain enough evidence to directly measure every initiative.

---

## Future Work

A production version could be extended with:

### Product instrumentation

Add richer events for AI task completion, output editing, output rejection, regeneration, latency, errors, user feedback and subscription conversion.

### AI evaluation

Introduce semantic quality evaluation, groundedness checks, hallucination detection, task-success measurement, human evaluation and model comparison.

### Experimentation

Add sequential testing, CUPED, power analysis, multiple-testing correction, longer-term retention outcomes and revenue-per-user outcomes.

### Business intelligence

Extend the economic model with customer acquisition cost, lifetime value, gross margin, churn, incremental revenue and contribution margin.

### Data infrastructure

A production-scale implementation could move from SQLite to a cloud warehouse and introduce scheduled orchestration, stronger observability and production-grade data-quality monitoring.

---

## Final Takeaway

The central outcome of this project is not a dashboard or a single statistical result.

It is the **decision-making workflow**:

```text
Observe
   ↓
Diagnose
   ↓
Experiment
   ↓
Evaluate
   ↓
Quantify
   ↓
Prioritise
   ↓
Decide
```

The project demonstrates how product analytics, statistics, experimentation, AI evaluation and business analysis can be combined into one decision-intelligence system.

The analysis identifies a clear funnel bottleneck, demonstrates a measurable activation difference in a controlled synthetic experiment, evaluates AI adoption and economics, and translates the evidence into a product roadmap.

The next step toward production readiness would be replacing synthetic assumptions with real behavioural, quality, cost, retention and revenue data.

The long-term objective is therefore not merely to build another dashboard, but to create a repeatable **product decision-intelligence system** that connects behavioural data, experimentation, AI economics and product prioritisation.
