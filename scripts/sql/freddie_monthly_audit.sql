-- Run only on the private SQLite research panel; never on the LendingClub PostgreSQL mart.
-- Example: sqlite3 -header -column "$FREDDIE_PANEL/panel.sqlite" < scripts/sql/freddie_monthly_audit.sql
SELECT COUNT(*) AS eligible_loan_months, COUNT(DISTINCT loan_id) AS loans,
       MIN(as_of) AS first_month, MAX(as_of) AS last_month FROM loan_month;
SELECT label_reason, COUNT(*) AS loan_months FROM loan_month GROUP BY label_reason;
SELECT as_of, eligible_current, labeled, adverse, censored,
       ROUND(100.0 * adverse / NULLIF(labeled, 0), 4) AS adverse_pct_labeled
FROM monthly_summary ORDER BY as_of;
-- Descriptive train-vintage availability only, not model/test evaluation.
SELECT COUNT(*) AS observations, SUM(label=1) AS adverse,
       SUM(label=0) AS non_adverse, SUM(label IS NULL) AS censored
FROM loan_month WHERE as_of BETWEEN '201901' AND '201909';
-- Must return zero: negatives require the entire horizon; label establishment is future-only.
SELECT COUNT(*) AS invalid_label_timing FROM loan_month
WHERE label IS NOT NULL AND (label_observed_period IS NULL OR label_observed_period <= as_of);
