"""SQLAlchemy ORM models for CreditLens raw schema tables.

Maps raw.lc_loans, raw.sec_financials, and raw.fred_indicators
so Alembic autogenerate can manage schema migrations.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database import Base


class LcLoan(Base):
    """Raw Lending Club loan record.

    Maps to raw.lc_loans — 2.9M rows ingested from Kaggle CSV.
    Primary key is loan_id assigned by Lending Club.
    """

    __tablename__ = "lc_loans"
    __table_args__ = (
        CheckConstraint("loan_amnt > 0", name="chk_loan_amnt"),
        CheckConstraint("annual_inc >= 0", name="chk_annual_inc"),
        CheckConstraint("dti >= 0", name="chk_dti"),
        CheckConstraint(
            "int_rate >= 0 AND int_rate <= 100", name="chk_int_rate"
        ),
        Index("idx_lc_loans_issue_date", "issue_date"),
        Index("idx_lc_loans_status", "loan_status"),
        Index("idx_lc_loans_grade_sub", "grade", "sub_grade"),
        Index("idx_lc_loans_addr_state", "addr_state"),
        {"schema": "raw"},
    )

    loan_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    member_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    loan_amnt: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    funded_amnt: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    term: Mapped[Optional[str]] = mapped_column(String(20))
    int_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    installment: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    grade: Mapped[Optional[str]] = mapped_column(String(1))
    sub_grade: Mapped[Optional[str]] = mapped_column(String(5))
    emp_title: Mapped[Optional[str]] = mapped_column(String(255))
    emp_length: Mapped[Optional[str]] = mapped_column(String(50))
    home_ownership: Mapped[Optional[str]] = mapped_column(String(50))
    annual_inc: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    verification_status: Mapped[Optional[str]] = mapped_column(String(50))
    issue_date: Mapped[Optional[date]] = mapped_column(Date)
    loan_status: Mapped[Optional[str]] = mapped_column(String(50))
    purpose: Mapped[Optional[str]] = mapped_column(String(100))
    title: Mapped[Optional[str]] = mapped_column(String(255))
    zip_code: Mapped[Optional[str]] = mapped_column(String(20))
    addr_state: Mapped[Optional[str]] = mapped_column(String(2))
    dti: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    delinq_2yrs: Mapped[Optional[int]] = mapped_column(Integer)
    earliest_cr_line: Mapped[Optional[date]] = mapped_column(Date)
    inq_last_6mths: Mapped[Optional[int]] = mapped_column(Integer)
    open_acc: Mapped[Optional[int]] = mapped_column(Integer)
    pub_rec: Mapped[Optional[int]] = mapped_column(Integer)
    revol_bal: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    revol_util: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    total_acc: Mapped[Optional[int]] = mapped_column(Integer)
    total_pymnt: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    total_rec_prncp: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    total_rec_int: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    recoveries: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    collection_recovery_fee: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2)
    )
    last_pymnt_date: Mapped[Optional[date]] = mapped_column(Date)
    last_pymnt_amnt: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    application_type: Mapped[Optional[str]] = mapped_column(String(50))
    loaded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )


class SecFinancial(Base):
    """Raw SEC EDGAR financial statement record.

    Maps to raw.sec_financials — XBRL tag-value pairs per filing.
    Composite PK: (adsh, tag, period) matches SEC's EDGAR bulk data format.
    """

    __tablename__ = "sec_financials"
    __table_args__ = (
        Index("idx_sec_financials_cik_period", "cik", "period"),
        {"schema": "raw"},
    )

    adsh: Mapped[str] = mapped_column(String(20), primary_key=True)
    tag: Mapped[str] = mapped_column(String(256), primary_key=True)
    period: Mapped[date] = mapped_column(Date, primary_key=True)
    cik: Mapped[Optional[int]] = mapped_column(BigInteger)
    company_name: Mapped[Optional[str]] = mapped_column(String(255))
    form_type: Mapped[Optional[str]] = mapped_column(String(20))
    fy: Mapped[Optional[int]] = mapped_column(Integer)
    fp: Mapped[Optional[str]] = mapped_column(String(10))
    value: Mapped[Optional[Decimal]] = mapped_column(Numeric(24, 4))
    uom: Mapped[Optional[str]] = mapped_column(String(20))
    loaded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )


class FredIndicator(Base):
    """Raw FRED macro-economic indicator observation.

    Maps to raw.fred_indicators — time series fetched via FRED API.
    Composite PK: (series_id, observation_date).
    """

    __tablename__ = "fred_indicators"
    __table_args__ = (
        CheckConstraint("value IS NOT NULL", name="chk_fred_value"),
        Index("idx_fred_indicators_date", "observation_date"),
        {"schema": "raw"},
    )

    series_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    observation_date: Mapped[date] = mapped_column(Date, primary_key=True)
    value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    series_name: Mapped[Optional[str]] = mapped_column(String(255))
    loaded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )
