"""Replace single-user index with useful ordering paths, preserving query data."""

from alembic import op

revision = "scale002"
down_revision = "scale001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in (
        "scale_order",
        "scale_order_partitioned",
        "scale_write_composite",
        "scale_write_covering",
    ):
        op.drop_index("ix_user", table_name=table)
        op.create_index("ix_user_time", table, ["user_id", "created_at", "id"])
        op.create_index("ix_time", table, ["created_at", "id"])


def downgrade() -> None:
    raise ValueError("Recorded009phase history retained; no automated downgrade")
