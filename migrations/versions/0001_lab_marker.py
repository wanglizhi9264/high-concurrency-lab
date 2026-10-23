"""Minimal migration-chain verification schema."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "lab_marker",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )


def downgrade():
    op.drop_table("lab_marker")
