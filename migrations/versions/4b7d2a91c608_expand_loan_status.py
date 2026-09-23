"""Preserve full source loan status strings.

Revision ID: 4b7d2a91c608
Revises: e9827ae898f0
"""

import sqlalchemy as sa

from alembic import op

revision = "4b7d2a91c608"
down_revision = "e9827ae898f0"
branch_labels = None
depends_on = None


def _change_status_type(
    existing: sa.types.TypeEngine[str], target: sa.types.TypeEngine[str]
) -> None:
    """Recreate the known dbt view atomically; refuse unexpected view metadata.

    PostgreSQL prevents changing a column type while a view depends on it.
    DROP RESTRICT also protects downstream views; Alembic's transaction restores
    the original view if any subsequent operation fails. Custom grants, owners,
    comments or options require an explicit migration instead of being discarded.
    """
    connection = op.get_bind()
    view = (
        connection.execute(
            sa.text("""SELECT c.relkind, pg_get_userbyid(c.relowner) = current_user AS owned,
            c.relacl IS NULL AND c.reloptions IS NULL
                AND NOT EXISTS (SELECT 1 FROM pg_description WHERE objoid=c.oid)
                AND NOT EXISTS (SELECT 1 FROM pg_seclabel WHERE objoid=c.oid) AS plain,
            pg_get_viewdef(c.oid, true) AS definition
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='staging' AND c.relname='lc_loans_clean'""")
        )
        .mappings()
        .one_or_none()
    )
    if view:
        if view["relkind"] != "v" or not view["owned"] or not view["plain"]:
            raise RuntimeError("Staging view has custom metadata; explicit preservation required")
        connection.execute(sa.text("DROP VIEW staging.lc_loans_clean RESTRICT"))
    op.alter_column(
        "lc_loans",
        "loan_status",
        schema="raw",
        existing_type=existing,
        type_=target,
        existing_nullable=True,
    )
    if view:
        connection.exec_driver_sql("CREATE VIEW staging.lc_loans_clean AS " + view["definition"])


def upgrade() -> None:
    """Allow source statuses longer than the legacy 50-character bound."""
    _change_status_type(sa.String(50), sa.Text())


def downgrade() -> None:
    """Restore the old bound only when doing so cannot truncate source data."""
    connection = op.get_bind()
    count = connection.execute(
        sa.text("SELECT COUNT(*) FROM raw.lc_loans WHERE length(loan_status) > 50")
    ).scalar_one()
    if count:
        raise RuntimeError("Cannot narrow loan_status: source values exceed 50 characters")
    _change_status_type(sa.Text(), sa.String(50))
