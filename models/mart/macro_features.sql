{{ config(
    materialized='table',
    schema='mart'
) }}

WITH source AS (
    SELECT * FROM {{ ref('fred_macro_clean') }}
),

lagged AS (
    SELECT
        observation_month AS date,
        unemployment_rate,
        cpi,
        fed_funds_rate,
        
        -- Lag Unemployment Rate
        LAG(unemployment_rate, 3) OVER (ORDER BY observation_month) AS unrate_lag3,
        LAG(unemployment_rate, 6) OVER (ORDER BY observation_month) AS unrate_lag6,
        
        -- Lag CPI
        LAG(cpi, 3) OVER (ORDER BY observation_month) AS cpi_lag3,
        LAG(cpi, 6) OVER (ORDER BY observation_month) AS cpi_lag6,
        
        -- Lag Fed Funds Rate
        LAG(fed_funds_rate, 3) OVER (ORDER BY observation_month) AS fedfunds_lag3,
        LAG(fed_funds_rate, 6) OVER (ORDER BY observation_month) AS fedfunds_lag6
    FROM source
)

SELECT * FROM lagged
