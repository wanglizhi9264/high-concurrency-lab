"""Durable task authority and immutable receipt, independent of transient transport."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from concurrency_lab.models.commerce import OPTIONS
from concurrency_lab.models.marker import Base


class OrderReceipt(Base):
    __tablename__ = "order_receipt"
    __table_args__ = (UniqueConstraint("order_id", name="uq_receipt_order"), OPTIONS)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("purchase_order.id", ondelete="RESTRICT"))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))


class DurableTask(Base):
    __tablename__ = "durable_task"
    __table_args__ = (
        CheckConstraint(
            "max_attempts BETWEEN 1 AND 5 AND attempts BETWEEN 0 AND max_attempts",
            name="ck_task_attempts",
        ),
        CheckConstraint("kind = 'order_receipt'", name="ck_task_kind"),
        CheckConstraint(
            "state IN ('queued','running','retry_wait','succeeded','failed')", name="ck_task_state"
        ),
        CheckConstraint(
            "(state = 'running' AND lease_token IS NOT NULL AND lease_until IS NOT NULL) "
            "OR (state <> 'running' AND lease_token IS NULL AND lease_until IS NULL)",
            name="ck_task_lease",
        ),
        CheckConstraint(
            "(state = 'succeeded' AND result_receipt_id IS NOT NULL) "
            "OR (state <> 'succeeded' AND result_receipt_id IS NULL)",
            name="ck_task_result",
        ),
        Index("ix_task_scope_due", "scenario_id", "state", "available_at"),
        Index("ix_task_order", "order_id"),
        Index("ix_task_lease", "scenario_id", "state", "lease_until"),
        OPTIONS,
    )
    id: Mapped[str] = mapped_column(String(32, collation="ascii_bin"), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(
        String(32, collation="ascii_bin"), ForeignKey("inventory_scenario.id", ondelete="RESTRICT")
    )
    order_id: Mapped[int] = mapped_column(ForeignKey("purchase_order.id", ondelete="RESTRICT"))
    kind: Mapped[str] = mapped_column(String(32))
    payload_sha256: Mapped[str] = mapped_column(String(64))
    fault_plan: Mapped[dict[str, Any] | None] = mapped_column(
        JSON(none_as_null=True), nullable=True
    )
    max_attempts: Mapped[int] = mapped_column(Integer)
    attempts: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(16))
    available_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    lease_token: Mapped[str | None] = mapped_column(String(32), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result_receipt_id: Mapped[int | None] = mapped_column(
        ForeignKey("order_receipt.id", ondelete="RESTRICT"), nullable=True
    )
    retry_of: Mapped[str | None] = mapped_column(
        String(32, collation="ascii_bin"),
        ForeignKey("durable_task.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    finished_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)


class TaskOutbox(Base):
    __tablename__ = "task_outbox"
    __table_args__ = (Index("ix_outbox_due", "next_publish_at"), OPTIONS)
    task_id: Mapped[str] = mapped_column(
        String(32, collation="ascii_bin"),
        ForeignKey("durable_task.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    next_publish_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    publish_count: Mapped[int] = mapped_column(Integer)
    last_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_published_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)


class TaskAttempt(Base):
    __tablename__ = "task_attempt"
    __table_args__ = (UniqueConstraint("task_id", "number", name="uq_task_attempt"), OPTIONS)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String(32, collation="ascii_bin"), ForeignKey("durable_task.id", ondelete="RESTRICT")
    )
    number: Mapped[int] = mapped_column(Integer)
    worker_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    started_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    finished_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    abandoned_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6), nullable=True)
    handler_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timeout_seconds: Mapped[float] = mapped_column(Float)
    lease_seconds: Mapped[float] = mapped_column(Float)


class TaskEvent(Base):
    __tablename__ = "task_event"
    __table_args__ = (Index("ix_event_task_id", "task_id", "id"), OPTIONS)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String(32, collation="ascii_bin"), ForeignKey("durable_task.id", ondelete="RESTRICT")
    )
    occurred_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    kind: Mapped[str] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(32))
    details: Mapped[dict[str, Any]] = mapped_column(JSON)
