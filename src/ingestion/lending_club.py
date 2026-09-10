"""Chunked Lending Club ingestion with an explicit resume mode."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extensions import connection as pg_connection
from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)

SOURCE_TO_RAW = {
    "id": "loan_id",
    "member_id": "member_id",
    "loan_amnt": "loan_amnt",
    "funded_amnt": "funded_amnt",
    "term": "term",
    "int_rate": "int_rate",
    "installment": "installment",
    "grade": "grade",
    "sub_grade": "sub_grade",
    "emp_title": "emp_title",
    "emp_length": "emp_length",
    "home_ownership": "home_ownership",
    "annual_inc": "annual_inc",
    "verification_status": "verification_status",
    "issue_d": "issue_date",
    "loan_status": "loan_status",
    "purpose": "purpose",
    "title": "title",
    "zip_code": "zip_code",
    "addr_state": "addr_state",
    "dti": "dti",
    "delinq_2yrs": "delinq_2yrs",
    "earliest_cr_line": "earliest_cr_line",
    "inq_last_6mths": "inq_last_6mths",
    "open_acc": "open_acc",
    "pub_rec": "pub_rec",
    "revol_bal": "revol_bal",
    "revol_util": "revol_util",
    "total_acc": "total_acc",
    "total_pymnt": "total_pymnt",
    "total_rec_prncp": "total_rec_prncp",
    "total_rec_int": "total_rec_int",
    "recoveries": "recoveries",
    "collection_recovery_fee": "collection_recovery_fee",
    "last_pymnt_d": "last_pymnt_date",
    "last_pymnt_amnt": "last_pymnt_amnt",
    "application_type": "application_type",
}
INTEGER_COLUMNS = {
    "id",
    "member_id",
    "delinq_2yrs",
    "inq_last_6mths",
    "open_acc",
    "pub_rec",
    "total_acc",
}
NUMERIC_COLUMNS = INTEGER_COLUMNS | {
    "loan_amnt",
    "funded_amnt",
    "int_rate",
    "installment",
    "annual_inc",
    "dti",
    "revol_bal",
    "revol_util",
    "total_pymnt",
    "total_rec_prncp",
    "total_rec_int",
    "recoveries",
    "collection_recovery_fee",
    "last_pymnt_amnt",
}
# Preserve legacy raw mapping; changing missingness semantics is a separate contract change.
ZERO_DEFAULTS = {
    "annual_inc",
    "delinq_2yrs",
    "inq_last_6mths",
    "open_acc",
    "pub_rec",
    "revol_bal",
    "revol_util",
    "total_acc",
    "total_pymnt",
    "total_rec_prncp",
    "total_rec_int",
    "recoveries",
    "collection_recovery_fee",
    "last_pymnt_amnt",
}
DATE_COLUMNS = {"issue_d", "earliest_cr_line", "last_pymnt_d"}


@dataclass
class IngestionSummary:
    """Aggregate progress without borrower values or credentials."""

    read_rows: int = 0
    excluded_required_fields: int = 0
    skipped_existing: int = 0
    written_rows: int = 0
    unchanged_or_conflicted: int = 0
    committed_batches: int = 0


def normalize_chunk(frame: pd.DataFrame) -> tuple[list[tuple[Any, ...]], int]:
    """Map CSV fields to raw SQL values without truncating status text.

    Args:
        frame: A CSV chunk containing SOURCE_TO_RAW columns.

    Returns:
        SQL rows and count excluded for missing required ID, amount or issue date.

    Raises:
        ValueError: Required columns are absent or a present value cannot be parsed.
    """
    missing = set(SOURCE_TO_RAW) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing CSV columns: {sorted(missing)}")
    clean = frame.dropna(subset=["id", "loan_amnt", "issue_d"]).copy()
    excluded = len(frame) - len(clean)
    for column in NUMERIC_COLUMNS:
        original = clean[column]
        converted = pd.to_numeric(original, errors="coerce")
        values = converted.to_numpy(dtype=float, na_value=np.nan)
        if (original.notna() & converted.isna()).any() or np.isinf(values).any():
            raise ValueError(f"Invalid numeric values in {column}")
        if column == "dti":
            converted = converted.where(converted >= 0)
        if column in ZERO_DEFAULTS:
            converted = converted.fillna(0)
        if column in INTEGER_COLUMNS:
            if ((converted.dropna() % 1) != 0).any():
                raise ValueError(f"Non-integral values in {column}")
            converted = converted.astype("Int64")
        clean[column] = converted
    for column in DATE_COLUMNS:
        original = clean[column]
        parsed = pd.to_datetime(original, format="%b-%Y", errors="coerce")
        if (original.notna() & parsed.isna()).any():
            raise ValueError(f"Invalid month-year values in {column}")
        clean[column] = parsed.dt.date
    clean = clean[list(SOURCE_TO_RAW)].astype(object)
    clean = clean.where(pd.notna(clean), None)
    return list(clean.itertuples(index=False, name=None)), excluded


def load_csv(
    csv_path: str | Path,
    connection: pg_connection,
    *,
    insert_missing: bool = False,
    chunksize: int = 50_000,
) -> IngestionSummary:
    """Load a local CSV, committing each successful chunk and rolling back failures.

    Args:
        csv_path: CSV or gzip CSV path.
        connection: Explicit PostgreSQL connection; autocommit must be disabled.
        insert_missing: Skip existing IDs and never overwrite their values.
        chunksize: Maximum CSV rows held for normalization at once.

    Returns:
        Aggregate row and batch counts. Upsert mode counts updated and inserted rows.

    Raises:
        FileNotFoundError: Source is missing.
        ValueError: Options or source values are invalid.
        RuntimeError: A database write failed; prior committed batches remain.
    """
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    if chunksize <= 0 or connection.autocommit:
        raise ValueError("Use a positive chunksize and a connection with autocommit disabled")
    summary = IngestionSummary()
    existing: set[int] = set()
    columns = ", ".join(SOURCE_TO_RAW.values())
    if insert_missing:
        conflict = "ON CONFLICT (loan_id) DO NOTHING"
    else:
        conflict = """ON CONFLICT (loan_id) DO UPDATE SET
            loan_status = EXCLUDED.loan_status, total_pymnt = EXCLUDED.total_pymnt,
            last_pymnt_date = EXCLUDED.last_pymnt_date, loaded_at = NOW()
            WHERE (lc_loans.loan_status, lc_loans.total_pymnt, lc_loans.last_pymnt_date)
                IS DISTINCT FROM
                (EXCLUDED.loan_status, EXCLUDED.total_pymnt, EXCLUDED.last_pymnt_date)"""
    query = f"INSERT INTO raw.lc_loans ({columns}) VALUES %s {conflict} RETURNING loan_id"
    try:
        if insert_missing:
            with connection.cursor(name="lc_existing_ids") as reader:
                reader.itersize = 10_000
                reader.execute("SELECT loan_id FROM raw.lc_loans")
                existing.update(row[0] for row in reader)
            connection.commit()
        for chunk in pd.read_csv(
            path, usecols=list(SOURCE_TO_RAW), chunksize=chunksize, dtype="string"
        ):
            summary.read_rows += len(chunk)
            if insert_missing:
                numeric_ids = pd.to_numeric(chunk["id"], errors="coerce")
                mask = numeric_ids.map(
                    lambda value: pd.notna(value) and value % 1 == 0 and int(value) in existing
                )
                summary.skipped_existing += int(mask.sum())
                chunk = chunk.loc[~mask]
            rows, excluded = normalize_chunk(chunk)
            summary.excluded_required_fields += excluded
            if rows:
                with connection.cursor() as cursor:
                    written = execute_values(cursor, query, rows, page_size=1000, fetch=True)
                connection.commit()
                summary.written_rows += len(written)
                summary.unchanged_or_conflicted += len(rows) - len(written)
                summary.committed_batches += 1
                if insert_missing:
                    existing.update(row[0] for row in written)
            logger.info("Lending Club progress: %s", asdict(summary))
    except psycopg2.Error as exc:
        connection.rollback()
        raise RuntimeError(
            f"Lending Club batch failed ({type(exc).__name__}, SQLSTATE={exc.pgcode}); "
            f"committed_batches={summary.committed_batches}, written_rows={summary.written_rows}"
        ) from None
    except (ValueError, OSError):
        connection.rollback()
        raise
    return summary
