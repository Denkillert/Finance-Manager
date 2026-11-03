"""ORM-модели: таблицы категорий и транзакций."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

KIND_INCOME = "income"
KIND_EXPENSE = "expense"
KIND_CODES = (KIND_INCOME, KIND_EXPENSE)


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""


class Category(Base):
    """Категория дохода или расхода."""

    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("name", name="uq_categories_name"),
        CheckConstraint("kind IN ('income', 'expense')", name="ck_categories_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    is_default: Mapped[bool] = mapped_column(nullable=False, default=False)

    transactions: Mapped[list[Transaction]] = relationship(back_populates="category")

    def __repr__(self) -> str:  # pragma: no cover - отладочное представление
        return f"Category(id={self.id!r}, name={self.name!r}, kind={self.kind!r})"


class Transaction(Base):
    """Финансовая операция: доход или расход."""

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    comment: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    category: Mapped[Category] = relationship(back_populates="transactions")

    def __repr__(self) -> str:  # pragma: no cover - отладочное представление
        return (
            f"Transaction(id={self.id!r}, amount={self.amount!r}, "
            f"date={self.occurred_on!r})"
        )
