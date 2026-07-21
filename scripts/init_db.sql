-- ============================================
-- SQL-FIRST SCHEMAS FOR CREDIT_LENS
-- DESIGNED WITH 3-SCHEMA LAYERS (RAW, STAGING, MART)
-- ============================================

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS mart;

-- Dedicated metadata database for the Apache Airflow orchestration services.
-- (Runs on the same PostgreSQL instance; created once on first init.)
SELECT 'CREATE DATABASE airflow OWNER creditlens'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow')\gexec

-- ============================================
-- RAW LAYER: Transactional Source Tables
-- ============================================

CREATE TABLE IF NOT EXISTS raw.lc_loans (
    loan_id BIGINT PRIMARY KEY,
    member_id BIGINT,
    loan_amnt NUMERIC(12,2),
    funded_amnt NUMERIC(12,2),
    term VARCHAR(20),
    int_rate NUMERIC(5,2),
    installment NUMERIC(10,2),
    grade CHAR(1),
    sub_grade VARCHAR(5),
    emp_title VARCHAR(255),
    emp_length VARCHAR(50),
    home_ownership VARCHAR(50),
    annual_inc NUMERIC(15,2),
    verification_status VARCHAR(50),
    issue_date DATE,
    loan_status VARCHAR(50),
    purpose VARCHAR(100),
    title VARCHAR(255),
    zip_code VARCHAR(20),
    addr_state CHAR(2),
    dti NUMERIC(8,2),
    delinq_2yrs INTEGER,
    earliest_cr_line DATE,
    inq_last_6mths INTEGER,
    open_acc INTEGER,
    pub_rec INTEGER,
    revol_bal NUMERIC(15,2),
    revol_util NUMERIC(5,2),
    total_acc INTEGER,
    total_pymnt NUMERIC(15,2),
    total_rec_prncp NUMERIC(15,2),
    total_rec_int NUMERIC(15,2),
    recoveries NUMERIC(15,2),
    collection_recovery_fee NUMERIC(15,2),
    last_pymnt_date DATE,
    last_pymnt_amnt NUMERIC(15,2),
    application_type VARCHAR(50),
    loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw.sec_financials (
    adsh VARCHAR(20),
    cik BIGINT,
    company_name VARCHAR(255),
    form_type VARCHAR(20),
    period DATE,
    fy INTEGER,
    fp VARCHAR(10),
    tag VARCHAR(256),
    value NUMERIC(24,4),
    uom VARCHAR(20),
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (adsh, tag, period)
);

CREATE TABLE IF NOT EXISTS raw.fred_indicators (
    series_id VARCHAR(50),
    observation_date DATE,
    value NUMERIC(15,4),
    series_name VARCHAR(255),
    loaded_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (series_id, observation_date)
);

-- ============================================
-- PERFORMANCE & FILTER INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_lc_loans_issue_date ON raw.lc_loans(issue_date);
CREATE INDEX IF NOT EXISTS idx_lc_loans_status ON raw.lc_loans(loan_status);
CREATE INDEX IF NOT EXISTS idx_lc_loans_grade_sub ON raw.lc_loans(grade, sub_grade);
CREATE INDEX IF NOT EXISTS idx_lc_loans_addr_state ON raw.lc_loans(addr_state);
CREATE INDEX IF NOT EXISTS idx_sec_financials_cik_period ON raw.sec_financials(cik, period);
CREATE INDEX IF NOT EXISTS idx_fred_indicators_date ON raw.fred_indicators(observation_date);

-- ============================================
-- CONSTRAINTS FOR DATA INTEGRITY
-- ============================================

ALTER TABLE raw.lc_loans ADD CONSTRAINT chk_loan_amnt CHECK (loan_amnt > 0);
ALTER TABLE raw.lc_loans ADD CONSTRAINT chk_int_rate CHECK (int_rate >= 0 AND int_rate <= 100);
ALTER TABLE raw.lc_loans ADD CONSTRAINT chk_annual_inc CHECK (annual_inc >= 0);
ALTER TABLE raw.lc_loans ADD CONSTRAINT chk_dti CHECK (dti >= 0);
ALTER TABLE raw.fred_indicators ADD CONSTRAINT chk_fred_value CHECK (value IS NOT NULL);

-- ============================================
-- SCHEMA DOCUMENTATION
-- ============================================

COMMENT ON TABLE raw.lc_loans IS 'Raw tabular financial data containing 2.9M records of Lending Club borrowers';
COMMENT ON TABLE raw.sec_financials IS 'Quarterly financial filings metrics and tags extracted from SEC EDGAR';
COMMENT ON TABLE raw.fred_indicators IS 'Macroeconomic time-series values fetched from Federal Reserve Bank of St. Louis API';
