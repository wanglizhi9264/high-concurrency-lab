"""Experimental relational schema. Metadata represents optimized Alembic head."""

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

from concurrency_lab.models.marker import Base

OPTIONS = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}


class LabUser(Base):
    __tablename__ = "lab_user"
    __table_args__ = (Index("ix_user_email", "email"), OPTIONS)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    email: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))


class LabProduct(Base):
    __tablename__ = "lab_product"
    __table_args__ = (CheckConstraint("price >= 0", name="ck_product_price"), OPTIONS)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sku: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class LabOrder(Base):
    __tablename__ = "lab_order"
    __table_args__ = (
        CheckConstraint("total >= 0", name="ck_order_total"),
        CheckConstraint("status IN ('created','paid','cancelled')", name="ck_order_status"),
        Index("ix_order_user", "user_id"),
        Index("ix_order_user_time", "user_id", "created_at", "id"),
        Index("ix_order_time", "created_at", "id"),
        OPTIONS,
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("lab_user.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(16))


class LabOrderItem(Base):
    __tablename__ = "lab_order_item"
    __table_args__ = (
        UniqueConstraint("order_id", "product_id", name="uq_item_order_product"),
        CheckConstraint("quantity > 0", name="ck_item_quantity"),
        CheckConstraint("unit_price >= 0", name="ck_item_price"),
        Index("ix_item_product", "product_id"),
        OPTIONS,
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("lab_order.id", ondelete="RESTRICT"))
    product_id: Mapped[int] = mapped_column(ForeignKey("lab_product.id", ondelete="RESTRICT"))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class ExperimentOwnership(Base):
    __tablename__ = "experiment_ownership"
    __table_args__ = OPTIONS
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purpose: Mapped[str] = mapped_column(String(64))


class ExperimentDataset(Base):
    __tablename__ = "experiment_dataset"
    __table_args__ = OPTIONS
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seed: Mapped[int] = mapped_column(BigInteger)
    order_count: Mapped[int] = mapped_column(BigInteger)
    digest: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
