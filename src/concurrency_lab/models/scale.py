"""Independent analytical metadata; never imported into the business migration context."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import DeclarativeBase


class ScaleBase(DeclarativeBase):
    pass


metadata = ScaleBase.metadata
QUERY_TABLES = ("scale_order", "scale_order_partitioned")
PROBE_TABLES = {
    "single": "scale_write_single",
    "composite": "scale_write_composite",
    "covering": "scale_write_covering",
}
TABLE_NAMES = frozenset((*QUERY_TABLES, *PROBE_TABLES.values()))

ownership = Table(
    "scale_ownership",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=False),
    Column("purpose", String(40), nullable=False),
    CheckConstraint("id=1", name="ck_scale_owner_singleton"),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)
dataset = Table(
    "scale_dataset",
    metadata,
    Column("id", Integer, ForeignKey("scale_ownership.id", ondelete="RESTRICT"), primary_key=True),
    Column("seed", BigInteger, nullable=False),
    Column("order_count", BigInteger, nullable=False),
    Column("batch_size", Integer, nullable=False),
    Column("generator_version", Integer, nullable=False),
    Column("digest", String(64), nullable=False),
    Column("status", String(16), nullable=False),
    Column("created_at", DATETIME(fsp=6), nullable=False),
    CheckConstraint("status IN ('loading','ready')", name="ck_scale_dataset_state"),
    mysql_engine="InnoDB",
    mysql_charset="utf8mb4",
)


def _define_table(name: str) -> Table:
    return Table(
        name,
        metadata,
        Column("id", BigInteger, primary_key=True),
        Column("created_at", DATETIME(fsp=6), primary_key=True),
        Column("user_id", BigInteger, nullable=False),
        Column("total", Numeric(14, 2), nullable=False),
        Column("status", String(16), nullable=False),
        Column("payload", String(160), nullable=False),
        CheckConstraint("id>0 AND user_id>0 AND total>=0", name=f"ck_{name}_values"),
        CheckConstraint("status IN ('created','paid','cancelled')", name=f"ck_{name}_status"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )


tables = {name: _define_table(name) for name in sorted(TABLE_NAMES)}

for table in tables.values():
    Index("ix_user", table.c.user_id)
