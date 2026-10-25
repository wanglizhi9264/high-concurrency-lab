"""Mutable scenario stock and minimal single-product orders, separate from seed fixtures."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
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


class InventoryScenario(Base):
    __tablename__ = "inventory_scenario"
    __table_args__ = (
        CheckConstraint(
            "initial >= 0 AND available >= 0 AND reserved >= 0 AND sold >= 0",
            name="ck_inventory_nonnegative",
        ),
        CheckConstraint("available + reserved + sold = initial", name="ck_inventory_balance"),
        Index("ix_inventory_product", "product_id"),
        OPTIONS,
    )
    id: Mapped[str] = mapped_column(String(32, collation="ascii_bin"), primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("lab_product.id", ondelete="RESTRICT"))
    initial: Mapped[int] = mapped_column(Integer)
    available: Mapped[int] = mapped_column(Integer)
    reserved: Mapped[int] = mapped_column(Integer)
    sold: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))


class PurchaseOrder(Base):
    __tablename__ = "purchase_order"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_purchase_idempotency"),
        CheckConstraint("quantity > 0 AND quantity <= 100", name="ck_purchase_quantity"),
        CheckConstraint(
            "unit_price >= 0 AND total = quantity * unit_price", name="ck_purchase_money"
        ),
        CheckConstraint("status IN ('reserved','paid','cancelled')", name="ck_purchase_state"),
        Index("ix_purchase_scenario_status", "scenario_id", "status"),
        Index("ix_purchase_user", "user_id"),
        OPTIONS,
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scenario_id: Mapped[str] = mapped_column(
        String(32, collation="ascii_bin"), ForeignKey("inventory_scenario.id", ondelete="RESTRICT")
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("lab_user.id", ondelete="RESTRICT"))
    idempotency_key: Mapped[str] = mapped_column(String(36, collation="ascii_bin"))
    payload_sha256: Mapped[str] = mapped_column(String(64))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    status: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    updated_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
