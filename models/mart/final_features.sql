{{ config(
    materialized='table',
    schema='mart'
) }}

WITH loans AS (
    SELECT * FROM {{ ref('loan_features') }}
),

macro AS (
    SELECT * FROM {{ ref('macro_features') }}
),

joined AS (
    SELECT
        l.*,
        m.unemployment_rate,
        m.unrate_lag3,
        m.unrate_lag6,
        m.cpi,
        m.cpi_lag3,
        m.cpi_lag6,
        m.fed_funds_rate,
        m.fedfunds_lag3,
        m.fedfunds_lag6
    FROM loans l
    LEFT JOIN macro m 
        ON DATE_TRUNC('month', l.issue_d)::DATE = m.date
)

SELECT * FROM joined
