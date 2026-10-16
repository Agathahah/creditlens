-- Reproduce dashboard populations from the local warehouse, without borrower exports.
-- Historical UI snapshot: 2026-09-23. Running today gives today's state, not that snapshot.
-- Requires the existing local CreditLens raw/staging/mart relations; no schema changes.
-- Run locally: psql -X -h localhost -p 5432 -U creditlens -d creditlens \
--   -v ON_ERROR_STOP=1 -f scripts/sql/dashboard_aggregates.sql
\pset pager off
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '10min';

-- Stable grain: one loan per row. Compare counts across the four layers.
SELECT 'raw.lc_loans' AS layer, count(*) AS rows FROM raw.lc_loans
UNION ALL SELECT 'staging.lc_loans_clean', count(*) FROM staging.lc_loans_clean
UNION ALL SELECT 'mart.loan_features', count(*) FROM mart.loan_features
UNION ALL SELECT 'mart.final_features', count(*) FROM mart.final_features;

-- Warehouse population: all terms and issue years, including NULL outcomes.
-- NULL means not definitively labeled by this contract; it is not a non-adverse label.
WITH profiled AS (
    SELECT EXTRACT(YEAR FROM issue_date)::int AS vintage,
           trim(term) AS term,
           CASE WHEN loan_status = 'Fully Paid' THEN 0
                WHEN loan_status IN ('Charged Off', 'Default') THEN 1 END AS target
    FROM raw.lc_loans
)
SELECT vintage, term, count(*) AS rows, count(target) AS labeled,
       count(*) FILTER (WHERE target = 0) AS non_adverse,
       count(*) FILTER (WHERE target = 1) AS adverse,
       count(*) FILTER (WHERE target IS NULL) AS unresolved,
       round(100.0 * count(*) FILTER (WHERE target IS NULL) / NULLIF(count(*), 0), 3)
           AS unresolved_pct,
       round(100.0 * avg(target), 3) AS adverse_pct_among_labeled
FROM profiled
GROUP BY vintage, term
ORDER BY vintage, term;

-- Experiment population: accepted, resolved 36-month loans, income > 0, 2011-2015.
-- Does not fit a model, select a threshold, or evaluate the consumed 2015 test.
SELECT purpose, count(*) AS rows
FROM raw.lc_loans
WHERE trim(term) = '36 months'
  AND issue_date >= DATE '2011-01-01' AND issue_date < DATE '2016-01-01'
  AND loan_status IN ('Fully Paid', 'Charged Off', 'Default') AND annual_inc > 0
GROUP BY purpose
ORDER BY rows DESC;

-- Eligible M1 profile: median and outer percentiles for application-time candidates.
-- These summarize the full eligible 2011-2015 cohort. Neither model nor frozen test is re-scored.
WITH eligible AS (
    SELECT annual_inc, dti, revol_util,
           (issue_date - earliest_cr_line) / 30.4375 AS credit_history_age_months
    FROM raw.lc_loans
    WHERE trim(term) = '36 months'
      AND issue_date >= DATE '2011-01-01' AND issue_date < DATE '2016-01-01'
      AND loan_status IN ('Fully Paid', 'Charged Off', 'Default') AND annual_inc > 0
), numeric_values AS (
    SELECT 'annual_inc' AS feature, annual_inc::double precision AS value FROM eligible
    UNION ALL SELECT 'dti', dti::double precision FROM eligible
    UNION ALL SELECT 'revol_util', revol_util::double precision FROM eligible
    UNION ALL SELECT 'credit_history_age_months', credit_history_age_months::double precision
    FROM eligible
)
SELECT feature, count(*) AS rows, count(value) AS observed,
       min(value) AS min,
       percentile_cont(0.01) WITHIN GROUP (ORDER BY value) AS p01,
       percentile_cont(0.50) WITHIN GROUP (ORDER BY value) AS median,
       percentile_cont(0.99) WITHIN GROUP (ORDER BY value) AS p99,
       max(value) AS max
FROM numeric_values GROUP BY feature ORDER BY feature;

-- Eligible cohort distribution by vintage; all rates divide by labeled eligible rows per year.
WITH eligible AS (
    SELECT EXTRACT(YEAR FROM issue_date)::int AS vintage, annual_inc, dti, revol_util,
           CASE WHEN loan_status = 'Fully Paid' THEN 0 ELSE 1 END AS target
    FROM raw.lc_loans
    WHERE trim(term) = '36 months'
      AND issue_date >= DATE '2011-01-01' AND issue_date < DATE '2016-01-01'
      AND loan_status IN ('Fully Paid', 'Charged Off', 'Default') AND annual_inc > 0
)
SELECT vintage, count(*) AS rows, round(100.0 * avg(target), 3) AS adverse_pct,
       percentile_cont(0.50) WITHIN GROUP (ORDER BY annual_inc) AS annual_inc_median,
       percentile_cont(0.50) WITHIN GROUP (ORDER BY dti) AS dti_median,
       percentile_cont(0.50) WITHIN GROUP (ORDER BY revol_util) AS revol_util_median
FROM eligible GROUP BY vintage ORDER BY vintage;

-- Home ownership is a categorical feature in the same eligible M1 cohort.
SELECT home_ownership, count(*) AS rows
FROM raw.lc_loans
WHERE trim(term) = '36 months'
  AND issue_date >= DATE '2011-01-01' AND issue_date < DATE '2016-01-01'
  AND loan_status IN ('Fully Paid', 'Charged Off', 'Default') AND annual_inc > 0
GROUP BY home_ownership ORDER BY rows DESC;

ROLLBACK;
