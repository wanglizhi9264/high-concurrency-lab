"""Query-specific secondary indexes, after a saved baseline in experiment CLI."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_user_email", "lab_user", ["email"])
    op.create_index("ix_order_user_time", "lab_order", ["user_id", "created_at", "id"])
    op.create_index("ix_order_time", "lab_order", ["created_at", "id"])


def downgrade():
    # A supporting FK index must exist before removing its composite alternative.
    indexes = sa.inspect(op.get_bind()).get_indexes("lab_order")
    if not any(index["name"] == "ix_order_user" for index in indexes):
        op.create_index("ix_order_user", "lab_order", ["user_id"])
    op.drop_index("ix_order_time", table_name="lab_order")
    op.drop_index("ix_order_user_time", table_name="lab_order")
    op.drop_index("ix_user_email", table_name="lab_user")
