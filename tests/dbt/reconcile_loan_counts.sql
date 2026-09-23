-- Current mart transforms must preserve the number of staged loans.
-- This complements key/uniqueness tests; equal counts alone do not prove equal IDs.
WITH counts AS (
    SELECT
        (SELECT COUNT(*) FROM {{ ref('lc_loans_clean') }}) AS staging_count,
        (SELECT COUNT(*) FROM {{ ref('loan_features') }}) AS loan_count,
        (SELECT COUNT(*) FROM {{ ref('final_features') }}) AS final_count
)

SELECT 'staging_to_loan' AS transition, staging_count AS expected_count,
    loan_count AS actual_count
FROM counts
WHERE staging_count <> loan_count

UNION ALL

SELECT 'loan_to_final' AS transition, loan_count AS expected_count,
    final_count AS actual_count
FROM counts
WHERE loan_count <> final_count
