"""Cover the user/time projection, keep globally ordered pagination index."""

from alembic import op

revision = "scale003"
down_revision = "scale002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("scale_order", "scale_order_partitioned", "scale_write_covering"):
        op.drop_index("ix_user_time", table_name=table)
        op.create_index("ix_user_cover", table, ["user_id", "created_at", "id", "total", "status"])


def downgrade() -> None:
    raise ValueError("Recorded009phase history retained; no automated downgrade")
