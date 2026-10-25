"""Independent inventory scenarios and idempotent single-product purchase orders."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import DATETIME

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "inventory_scenario",
        sa.Column("id", sa.String(32, collation="ascii_bin"), primary_key=True),
        sa.Column(
            "product_id",
            sa.BigInteger(),
            sa.ForeignKey("lab_product.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("initial", sa.Integer(), nullable=False),
        sa.Column("available", sa.Integer(), nullable=False),
        sa.Column("reserved", sa.Integer(), nullable=False),
        sa.Column("sold", sa.Integer(), nullable=False),
        sa.Column("created_at", DATETIME(fsp=6), nullable=False),
        sa.CheckConstraint(
            "initial >= 0 AND available >= 0 AND reserved >= 0 AND sold >= 0",
            name="ck_inventory_nonnegative",
        ),
        sa.CheckConstraint("available + reserved + sold = initial", name="ck_inventory_balance"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_inventory_product", "inventory_scenario", ["product_id"])
    op.create_table(
        "purchase_order",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "scenario_id",
            sa.String(32, collation="ascii_bin"),
            sa.ForeignKey("inventory_scenario.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("lab_user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(36, collation="ascii_bin"), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", DATETIME(fsp=6), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_purchase_idempotency"),
        sa.CheckConstraint("quantity > 0 AND quantity <= 100", name="ck_purchase_quantity"),
        sa.CheckConstraint(
            "unit_price >= 0 AND total = quantity * unit_price", name="ck_purchase_money"
        ),
        sa.CheckConstraint("status IN ('reserved','paid','cancelled')", name="ck_purchase_state"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_purchase_scenario_status", "purchase_order", ["scenario_id", "status"])
    op.create_index("ix_purchase_user", "purchase_order", ["user_id"])


def downgrade():
    op.drop_table("purchase_order")
    op.drop_table("inventory_scenario")
