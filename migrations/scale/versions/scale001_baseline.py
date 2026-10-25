"""Frozen009baseline tables, single-column user indexes and quarterly analytical twin."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "scale001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scale_order",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("payload", sa.String(length=160), nullable=False),
        sa.CheckConstraint(
            "status IN ('created','paid','cancelled')", name="ck_scale_order_status"
        ),
        sa.CheckConstraint("id>0 AND user_id>0 AND total>=0", name="ck_scale_order_values"),
        sa.PrimaryKeyConstraint("id", "created_at"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_user", "scale_order", ["user_id"], unique=False)
    op.create_table(
        "scale_order_partitioned",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("payload", sa.String(length=160), nullable=False),
        sa.CheckConstraint(
            "status IN ('created','paid','cancelled')", name="ck_scale_order_partitioned_status"
        ),
        sa.CheckConstraint(
            "id>0 AND user_id>0 AND total>=0", name="ck_scale_order_partitioned_values"
        ),
        sa.PrimaryKeyConstraint("id", "created_at"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_user", "scale_order_partitioned", ["user_id"], unique=False)
    op.create_table(
        "scale_ownership",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("purpose", sa.String(length=40), nullable=False),
        sa.CheckConstraint("id=1", name="ck_scale_owner_singleton"),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.create_table(
        "scale_write_composite",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("payload", sa.String(length=160), nullable=False),
        sa.CheckConstraint(
            "status IN ('created','paid','cancelled')", name="ck_scale_write_composite_status"
        ),
        sa.CheckConstraint(
            "id>0 AND user_id>0 AND total>=0", name="ck_scale_write_composite_values"
        ),
        sa.PrimaryKeyConstraint("id", "created_at"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_user", "scale_write_composite", ["user_id"], unique=False)
    op.create_table(
        "scale_write_covering",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("payload", sa.String(length=160), nullable=False),
        sa.CheckConstraint(
            "status IN ('created','paid','cancelled')", name="ck_scale_write_covering_status"
        ),
        sa.CheckConstraint(
            "id>0 AND user_id>0 AND total>=0", name="ck_scale_write_covering_values"
        ),
        sa.PrimaryKeyConstraint("id", "created_at"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_user", "scale_write_covering", ["user_id"], unique=False)
    op.create_table(
        "scale_write_single",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("payload", sa.String(length=160), nullable=False),
        sa.CheckConstraint(
            "status IN ('created','paid','cancelled')", name="ck_scale_write_single_status"
        ),
        sa.CheckConstraint("id>0 AND user_id>0 AND total>=0", name="ck_scale_write_single_values"),
        sa.PrimaryKeyConstraint("id", "created_at"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_user", "scale_write_single", ["user_id"], unique=False)
    op.create_table(
        "scale_dataset",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("seed", sa.BigInteger(), nullable=False),
        sa.Column("order_count", sa.BigInteger(), nullable=False),
        sa.Column("batch_size", sa.Integer(), nullable=False),
        sa.Column("generator_version", sa.Integer(), nullable=False),
        sa.Column("digest", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint("status IN ('loading','ready')", name="ck_scale_dataset_state"),
        sa.ForeignKeyConstraint(["id"], ["scale_ownership.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.execute(
        "ALTER TABLE scale_order_partitioned PARTITION BY RANGE COLUMNS(created_at) ("
        "PARTITION p1 VALUES LESS THAN ('2025-04-01'),"
        "PARTITION p2 VALUES LESS THAN ('2025-07-01'),"
        "PARTITION p3 VALUES LESS THAN ('2025-10-01'),"
        "PARTITION p4 VALUES LESS THAN ('2026-01-01'),"
        "PARTITION p_future VALUES LESS THAN (MAXVALUE))"
    )
    op.execute("INSERT INTO scale_ownership(id,purpose) VALUES(1,'scale-lab-v1')")


def downgrade() -> None:
    raise ValueError("009experiment history retained; no automated destructive downgrade")
