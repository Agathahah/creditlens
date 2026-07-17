{{
  config(
    materialized='view',
    schema='staging',
    alias='fred_macro_clean'
  )
}}

/*
  Staging: FRED macro indicators — clean and align to monthly granularity.
  Source: raw.fred_indicators (FEDFUNDS, UNRATE, CPIAUCSL, GDPC1)
  Target: staging.fred_macro_clean

  Transformations:
  - Filter NULL values
  - Truncate to month start for consistent join key with lc_loans
  - Deduplicate to one value per (series_id, month) — last observation wins
  - Pivot four series into wide columns for easier feature joins
*/

WITH source AS (
    SELECT
        series_id,
        DATE_TRUNC('month', observation_date)::DATE AS observation_month,
        value,
        ROW_NUMBER() OVER (
            PARTITION BY series_id, DATE_TRUNC('month', observation_date)
            ORDER BY observation_date DESC
        ) AS _rn
    FROM {{ source('raw', 'fred_indicators') }}
    WHERE value IS NOT NULL
),

deduped AS (
    SELECT series_id, observation_month, value
    FROM source
    WHERE _rn = 1
),

pivoted AS (
    SELECT
        observation_month,
        MAX(CASE WHEN series_id = 'FEDFUNDS'  THEN value END) AS fed_funds_rate,
        MAX(CASE WHEN series_id = 'UNRATE'    THEN value END) AS unemployment_rate,
        MAX(CASE WHEN series_id = 'CPIAUCSL'  THEN value END) AS cpi,
        MAX(CASE WHEN series_id = 'GDPC1'     THEN value END) AS real_gdp
    FROM deduped
    GROUP BY observation_month
)

SELECT
    observation_month,
    fed_funds_rate,
    unemployment_rate,
    cpi,
    -- YoY CPI change as inflation proxy
    cpi - LAG(cpi, 12) OVER (ORDER BY observation_month) AS cpi_yoy_change,
    real_gdp,
    -- QoQ real GDP growth rate
    ROUND(
        (real_gdp - LAG(real_gdp, 1) OVER (ORDER BY observation_month))
        / NULLIF(LAG(real_gdp, 1) OVER (ORDER BY observation_month), 0) * 100,
        4
    ) AS gdp_qoq_growth
FROM pivoted
ORDER BY observation_month
