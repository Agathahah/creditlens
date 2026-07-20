{{ config(
    materialized='table',
    schema='mart'
) }}

WITH source AS (
    SELECT * FROM {{ ref('lc_loans_clean') }}
),

engineered AS (
    SELECT
        loan_id AS id,
        member_id,
        loan_amnt,
        NULLIF(REGEXP_REPLACE(term, '[^0-9]', '', 'g'), '')::INTEGER AS term_months,
        int_rate,
        installment,
        grade,
        sub_grade,
        emp_length_years,
        home_ownership,
        annual_inc,
        verification_status,
        issue_date AS issue_d,
        loan_status,
        purpose,
        addr_state,
        dti,
        delinq_2yrs,
        earliest_cr_line,
        inq_last_6mths,
        open_acc,
        pub_rec,
        revol_bal,
        revol_util,
        total_acc,
        is_default,

        -- 1. Rasio Kredit & Beban
        COALESCE(dti, 0.0) AS dti_eff,
        CASE 
            WHEN annual_inc > 0 THEN (installment * 12) / annual_inc 
            ELSE 0.0 
        END AS installment_to_income_ratio,

        -- 2. Kolektibilitas & Sejarah Kredit
        COALESCE(revol_util, 0.0) / 100.0 AS revol_util_clean,
        CASE 
            WHEN earliest_cr_line IS NOT NULL THEN 
                ((EXTRACT(YEAR FROM issue_date) - EXTRACT(YEAR FROM earliest_cr_line)) * 12) + 
                (EXTRACT(MONTH FROM issue_date) - EXTRACT(MONTH FROM earliest_cr_line))
            ELSE 0
        END AS credit_history_age_months,

        -- 3. Fitur Pelanggaran & Risiko
        CASE WHEN delinq_2yrs > 0 THEN 1 ELSE 0 END AS has_delinq,
        CASE WHEN pub_rec > 0 THEN 1 ELSE 0 END AS has_public_record

    FROM source
)

SELECT * FROM engineered
