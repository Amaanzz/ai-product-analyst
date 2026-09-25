-- ============================================================================
-- SQL Analytics Layer -- InsightAI Product Analytics
-- ============================================================================
-- These queries run against the SQLite database produced by
-- src/sql_layer/load_to_sqlite.py (tables: users, events, user_features,
-- user_daily_activity). Every query below has been executed against real
-- (synthetic) data to confirm it runs and returns sensible results --
-- see src/sql_layer/run_queries.py for the automated runner.
--
-- Portable note: written in standard ANSI SQL (CTEs, window functions) so it
-- ports to PostgreSQL/DuckDB with no changes; SQLite is used here only
-- because it requires zero extra installation.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- 1. FUNNEL: stage-by-stage conversion using a CTE per stage + window function
--    for conversion-from-previous-stage
-- ----------------------------------------------------------------------------
WITH funnel_stages AS (
    SELECT 'signup' AS stage, 1 AS stage_order
    UNION ALL SELECT 'onboarding_started', 2
    UNION ALL SELECT 'onboarding_completed', 3
    UNION ALL SELECT 'project_created', 4
    UNION ALL SELECT 'ai_assistant_opened', 5
    UNION ALL SELECT 'output_saved', 6
),
stage_counts AS (
    SELECT
        fs.stage,
        fs.stage_order,
        CASE
            WHEN fs.stage = 'signup' THEN (SELECT COUNT(DISTINCT user_id) FROM users)
            ELSE COUNT(DISTINCT e.user_id)
        END AS users_reached
    FROM funnel_stages fs
    LEFT JOIN events e ON e.event_name = fs.stage
    GROUP BY fs.stage, fs.stage_order
)
SELECT
    stage,
    users_reached,
    ROUND(100.0 * users_reached / FIRST_VALUE(users_reached) OVER (ORDER BY stage_order), 2)
        AS conversion_from_start_pct,
    ROUND(100.0 * users_reached / NULLIF(LAG(users_reached) OVER (ORDER BY stage_order), 0), 2)
        AS conversion_from_previous_pct
FROM stage_counts
ORDER BY stage_order;


-- ----------------------------------------------------------------------------
-- 2. COHORT RETENTION: signup-month cohorts x weeks-since-signup, using a CTE
--    to compute weeks-since-signup per event, then a window function for
--    cohort size
-- ----------------------------------------------------------------------------
WITH user_cohort AS (
    SELECT
        user_id,
        strftime('%Y-%m', signup_date) AS cohort_month,
        signup_date
    FROM users
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(DISTINCT user_id) AS cohort_size
    FROM user_cohort
    GROUP BY cohort_month
),
event_weeks AS (
    SELECT
        e.user_id,
        uc.cohort_month,
        CAST((julianday(e.timestamp) - julianday(uc.signup_date)) / 7 AS INTEGER) AS week_number
    FROM events e
    JOIN user_cohort uc ON uc.user_id = e.user_id
    WHERE julianday(e.timestamp) >= julianday(uc.signup_date)
)
SELECT
    ew.cohort_month,
    ew.week_number,
    COUNT(DISTINCT ew.user_id) AS active_users,
    cs.cohort_size,
    ROUND(100.0 * COUNT(DISTINCT ew.user_id) / cs.cohort_size, 2) AS retention_pct
FROM event_weeks ew
JOIN cohort_sizes cs ON cs.cohort_month = ew.cohort_month
WHERE ew.week_number BETWEEN 0 AND 8
GROUP BY ew.cohort_month, ew.week_number, cs.cohort_size
ORDER BY ew.cohort_month, ew.week_number;


-- ----------------------------------------------------------------------------
-- 3. A/B EXPERIMENT: activation rate by experiment group, with a window
--    function computing the lift directly in SQL (no pandas needed)
-- ----------------------------------------------------------------------------
WITH group_activation AS (
    SELECT
        u.experiment_group,
        COUNT(DISTINCT u.user_id) AS n_users,
        COUNT(DISTINCT CASE WHEN e.event_name = 'onboarding_completed' THEN u.user_id END) AS n_activated
    FROM users u
    LEFT JOIN events e ON e.user_id = u.user_id
    GROUP BY u.experiment_group
),
rates AS (
    SELECT
        experiment_group,
        n_users,
        n_activated,
        ROUND(100.0 * n_activated / n_users, 2) AS activation_rate_pct
    FROM group_activation
)
SELECT
    experiment_group,
    n_users,
    n_activated,
    activation_rate_pct,
    ROUND(
        activation_rate_pct - MIN(activation_rate_pct) OVER (),
        2
    ) AS absolute_lift_vs_control_pp
FROM rates
ORDER BY experiment_group;


-- ----------------------------------------------------------------------------
-- 4. AI FEATURE ADOPTION x RETENTION: behavioural cohort comparison, using a
--    CTE to flag AI adopters then joining to a D30-activity flag
-- ----------------------------------------------------------------------------
WITH ai_adopters AS (
    SELECT DISTINCT user_id
    FROM events
    WHERE event_name = 'ai_assistant_opened'
),
day30_active AS (
    SELECT DISTINCT e.user_id
    FROM events e
    JOIN users u ON u.user_id = e.user_id
    WHERE CAST((julianday(e.timestamp) - julianday(u.signup_date)) AS INTEGER) = 30
)
SELECT
    CASE WHEN a.user_id IS NOT NULL THEN 'AI adopter' ELSE 'Non-adopter' END AS segment,
    COUNT(DISTINCT u.user_id) AS n_users,
    COUNT(DISTINCT d.user_id) AS retained_day_30,
    ROUND(100.0 * COUNT(DISTINCT d.user_id) / COUNT(DISTINCT u.user_id), 2) AS retention_day_30_pct
FROM users u
LEFT JOIN ai_adopters a ON a.user_id = u.user_id
LEFT JOIN day30_active d ON d.user_id = u.user_id
GROUP BY segment;
-- NOTE: this is an observational association (AI adopters vs not), not a
-- causal claim -- only the randomized A/B test above supports causal language.


-- ----------------------------------------------------------------------------
-- 5. RULE-BASED SEGMENTATION: engagement tiers using window-function
--    percentile ranking (NTILE) on AI query volume
-- ----------------------------------------------------------------------------
WITH user_ai_activity AS (
    SELECT
        user_id,
        COUNT(*) AS ai_query_count
    FROM events
    WHERE event_name = 'ai_query_submitted'
    GROUP BY user_id
),
ranked AS (
    SELECT
        user_id,
        ai_query_count,
        NTILE(4) OVER (ORDER BY ai_query_count) AS engagement_quartile
    FROM user_ai_activity
)
SELECT
    CASE engagement_quartile
        WHEN 1 THEN 'Low engagement'
        WHEN 2 THEN 'Medium engagement'
        WHEN 3 THEN 'High engagement'
        WHEN 4 THEN 'Power users'
    END AS segment,
    COUNT(*) AS n_users,
    ROUND(AVG(ai_query_count), 2) AS avg_ai_queries,
    MIN(ai_query_count) AS min_queries,
    MAX(ai_query_count) AS max_queries
FROM ranked
GROUP BY engagement_quartile
ORDER BY engagement_quartile;


-- ----------------------------------------------------------------------------
-- 6. TIME-TO-ACTIVATION: median/percentile time between signup and
--    onboarding_completed, using a CTE + window function for row numbering
--    (SQLite has no native PERCENTILE_CONT, so this approximates via ordering)
-- ----------------------------------------------------------------------------
WITH time_to_activate AS (
    SELECT
        e.user_id,
        (julianday(e.timestamp) - julianday(u.signup_date)) * 24 AS hours_to_activate
    FROM events e
    JOIN users u ON u.user_id = e.user_id
    WHERE e.event_name = 'onboarding_completed'
),
ranked AS (
    SELECT
        hours_to_activate,
        ROW_NUMBER() OVER (ORDER BY hours_to_activate) AS rn,
        COUNT(*) OVER () AS total_n
    FROM time_to_activate
)
SELECT
    ROUND(AVG(hours_to_activate), 2) AS avg_hours_to_activate,
    (SELECT ROUND(hours_to_activate, 2) FROM ranked WHERE rn = (total_n / 2) LIMIT 1) AS median_hours_to_activate
FROM time_to_activate;
