{{
  config(
    materialized='view',
    schema='staging',
    alias='lc_loans_clean'
  )
}}

/*
  Staging: Lending Club loans — clean, deduplicate, add ML target.
  Source: raw.lc_loans (2.9M rows, 2007-2018 Q4)
  Target: staging.lc_loans_clean

  Transformations:
  - Deduplicate by loan_id (keep latest loaded_at)
  - Filter: require loan_id, loan_amnt > 0, issue_date
  - Parse emp_length text → integer years
  - Add is_default binary target (1=default/charged-off, 0=fully-paid, NULL=ongoing)
  - Exclude rows without definitive outcome for ML training
*/

WITH source AS (
    SELECT * FROM {{ source('raw', 'lc_loans') }}
),

deduped AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY loan_id ORDER BY loaded_at DESC NULLS LAST
        ) AS _rn
    FROM source
    WHERE loan_id    IS NOT NULL
      AND loan_amnt  >  0
      AND issue_date IS NOT NULL
),

cleaned AS (
    SELECT
        loan_id,
        member_id,
        loan_amnt,
        funded_amnt,
        TRIM(term)                              AS term,
        int_rate,
        installment,
        grade,
        sub_grade,
        NULLIF(TRIM(emp_title), '')             AS emp_title,
        emp_length,
        CASE
            WHEN emp_length = '10+ years'       THEN 11
            WHEN emp_length = '< 1 year'        THEN 0
            WHEN emp_length ~ '^\d+ year'
                THEN REGEXP_REPLACE(emp_length, '[^0-9]', '', 'g')::INTEGER
            ELSE NULL
        END                                     AS emp_length_years,
        home_ownership,
        annual_inc,
        verification_status,
        issue_date,
        EXTRACT(YEAR  FROM issue_date)::INTEGER AS issue_year,
        EXTRACT(MONTH FROM issue_date)::INTEGER AS issue_month,
        loan_status,
        CASE
            WHEN loan_status IN ('Charged Off', 'Default', 'Late (31-120 days)')
                THEN 1
            WHEN loan_status = 'Fully Paid'
                THEN 0
            ELSE NULL
        END                                     AS is_default,
        purpose,
        addr_state,
        COALESCE(dti, 0)                        AS dti,
        COALESCE(delinq_2yrs, 0)                AS delinq_2yrs,
        earliest_cr_line,
        CASE
            WHEN earliest_cr_line IS NOT NULL
            THEN EXTRACT(YEAR FROM AGE(issue_date, earliest_cr_line))::INTEGER
            ELSE NULL
        END                                     AS credit_age_years,
        COALESCE(inq_last_6mths, 0)             AS inq_last_6mths,
        COALESCE(open_acc, 0)                   AS open_acc,
        COALESCE(pub_rec, 0)                    AS pub_rec,
        COALESCE(revol_bal, 0)                  AS revol_bal,
        COALESCE(revol_util, 0)                 AS revol_util,
        COALESCE(total_acc, 0)                  AS total_acc,
        COALESCE(total_pymnt, 0)                AS total_pymnt,
        COALESCE(total_rec_prncp, 0)            AS total_rec_prncp,
        COALESCE(total_rec_int, 0)              AS total_rec_int,
        COALESCE(recoveries, 0)                 AS recoveries,
        application_type,
        loaded_at
    FROM deduped
    WHERE _rn = 1
)

SELECT * FROM cleaned
