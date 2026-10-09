-- Required loan layers must contain data; column-level tests alone allow empty tables.
SELECT 'staging.lc_loans_clean' AS relation_name, COUNT(*) AS row_count
FROM {{ ref('lc_loans_clean') }}
HAVING COUNT(*) = 0

UNION ALL

SELECT 'mart.loan_features' AS relation_name, COUNT(*) AS row_count
FROM {{ ref('loan_features') }}
HAVING COUNT(*) = 0

UNION ALL

SELECT 'mart.final_features' AS relation_name, COUNT(*) AS row_count
FROM {{ ref('final_features') }}
HAVING COUNT(*) = 0
