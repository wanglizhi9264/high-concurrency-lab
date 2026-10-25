"""Frozen durable receipt tasks and transactional publication intent."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "order_receipt",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["purchase_order.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_receipt_order"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.create_table(
        "durable_task",
        sa.Column("id", sa.String(length=32, collation="ascii_bin"), nullable=False),
        sa.Column("scenario_id", sa.String(length=32, collation="ascii_bin"), nullable=False),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("fault_plan", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("available_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("lease_token", sa.String(length=32), nullable=True),
        sa.Column("lease_until", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("last_error", sa.String(length=64), nullable=True),
        sa.Column("result_receipt_id", sa.BigInteger(), nullable=True),
        sa.Column("retry_of", sa.String(length=32, collation="ascii_bin"), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("finished_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.CheckConstraint(
            "(state = 'running' AND lease_token IS NOT NULL AND lease_until IS NOT NULL) "
            "OR (state <> 'running' AND lease_token IS NULL AND lease_until IS NULL)",
            name="ck_task_lease",
        ),
        sa.CheckConstraint(
            "(state = 'succeeded' AND result_receipt_id IS NOT NULL) "
            "OR (state <> 'succeeded' AND result_receipt_id IS NULL)",
            name="ck_task_result",
        ),
        sa.CheckConstraint("kind = 'order_receipt'", name="ck_task_kind"),
        sa.CheckConstraint(
            "state IN ('queued','running','retry_wait','succeeded','failed')", name="ck_task_state"
        ),
        sa.CheckConstraint(
            "max_attempts BETWEEN 1 AND 5 AND attempts BETWEEN 0 AND max_attempts",
            name="ck_task_attempts",
        ),
        sa.ForeignKeyConstraint(["order_id"], ["purchase_order.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["result_receipt_id"], ["order_receipt.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["retry_of"], ["durable_task.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["scenario_id"], ["inventory_scenario.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.create_index(
        "ix_task_lease", "durable_task", ["scenario_id", "state", "lease_until"], unique=False
    )
    op.create_index("ix_task_order", "durable_task", ["order_id"], unique=False)
    op.create_index(
        "ix_task_scope_due", "durable_task", ["scenario_id", "state", "available_at"], unique=False
    )
    op.create_table(
        "task_outbox",
        sa.Column("task_id", sa.String(length=32, collation="ascii_bin"), nullable=False),
        sa.Column("next_publish_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("publish_count", sa.Integer(), nullable=False),
        sa.Column("last_message_id", sa.String(length=64), nullable=True),
        sa.Column("last_published_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["durable_task.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("task_id"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_outbox_due", "task_outbox", ["next_publish_at"], unique=False)
    op.create_table(
        "task_attempt",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=32, collation="ascii_bin"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("worker_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("finished_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("abandoned_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("handler_ms", sa.Float(), nullable=True),
        sa.Column("error", sa.String(length=64), nullable=True),
        sa.Column("timeout_seconds", sa.Float(), nullable=False),
        sa.Column("lease_seconds", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["durable_task.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "number", name="uq_task_attempt"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.create_table(
        "task_event",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=32, collation="ascii_bin"), nullable=False),
        sa.Column("occurred_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["durable_task.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_event_task_id", "task_event", ["task_id", "id"], unique=False)


def downgrade() -> None:
    op.drop_table("task_event")
    op.drop_table("task_attempt")
    op.drop_table("task_outbox")
    op.drop_table("durable_task")
    op.drop_table("order_receipt")
