"""Baseline relational schema; no query-specific sorting/email indexes."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import DATETIME

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None
OPTIONS = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}


def upgrade():
    op.create_table(
        "lab_user",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("email", sa.String(128), nullable=False),
        sa.Column("created_at", DATETIME(fsp=6), nullable=False),
        **OPTIONS,
    )
    op.create_table(
        "lab_product",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("sku", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("price >= 0", name="ck_product_price"),
        **OPTIONS,
    )
    op.create_table(
        "lab_order",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("lab_user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", DATETIME(fsp=6), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.CheckConstraint("total >= 0", name="ck_order_total"),
        sa.CheckConstraint("status IN ('created','paid','cancelled')", name="ck_order_status"),
        **OPTIONS,
    )
    op.create_index("ix_order_user", "lab_order", ["user_id"])
    op.create_table(
        "lab_order_item",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "order_id",
            sa.BigInteger(),
            sa.ForeignKey("lab_order.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.BigInteger(),
            sa.ForeignKey("lab_product.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.UniqueConstraint("order_id", "product_id", name="uq_item_order_product"),
        sa.CheckConstraint("quantity > 0", name="ck_item_quantity"),
        sa.CheckConstraint("unit_price >= 0", name="ck_item_price"),
        **OPTIONS,
    )
    op.create_index("ix_item_product", "lab_order_item", ["product_id"])
    ownership = op.create_table(
        "experiment_ownership",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("purpose", sa.String(64), nullable=False),
        **OPTIONS,
    )
    op.bulk_insert(ownership, [{"id": 1, "purpose": "index-baseline-v1"}])
    op.create_table(
        "experiment_dataset",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("seed", sa.BigInteger(), nullable=False),
        sa.Column("order_count", sa.BigInteger(), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        **OPTIONS,
    )


def downgrade():
    for name in (
        "experiment_dataset",
        "experiment_ownership",
        "lab_order_item",
        "lab_order",
        "lab_product",
        "lab_user",
    ):
        op.drop_table(name)
