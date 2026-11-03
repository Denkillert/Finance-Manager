"""Бизнес-логика и запросы к базе данных."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import contains_eager

from .database import Database
from .dto import CategoryInfo, Summary, TransactionRow
from .models import KIND_EXPENSE, KIND_INCOME, Category, Transaction
from .utils import (
    TWO_PLACES,
    month_bounds,
    previous_month_bounds,
    year_bounds,
)

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class TransactionFilter:
    """Неизменяемый набор условий фильтрации операций."""

    date_from: date | None = None
    date_to: date | None = None
    kind: str | None = None
    category_id: int | None = None
    search: str = ""

    def with_dates(self, start: date | None, end: date | None) -> TransactionFilter:
        return replace(self, date_from=start, date_to=end)

    def date_conditions(self) -> list:
        conditions = []
        if self.date_from is not None:
            conditions.append(Transaction.occurred_on >= self.date_from)
        if self.date_to is not None:
            conditions.append(Transaction.occurred_on <= self.date_to)
        return conditions


def period_filter(
    code: str,
    today: date | None = None,
    custom: tuple[date | None, date | None] = (None, None),
) -> TransactionFilter:
    """Строит фильтр по коду периода из настроек."""
    today = today or date.today()
    if code == "month":
        start, end = month_bounds(today)
    elif code == "prev_month":
        start, end = previous_month_bounds(today)
    elif code == "year":
        start, end = year_bounds(today)
    elif code == "custom":
        start, end = custom
    else:
        start, end = None, None
    return TransactionFilter(date_from=start, date_to=end)


class FinanceService:
    """Все операции приложения с базой данных."""

    def __init__(self, database: Database) -> None:
        self.db = database

    # ------------------------------------------------------------------
    # Категории
    # ------------------------------------------------------------------
    def categories(self) -> list[CategoryInfo]:
        """Категории вместе с количеством и суммой операций."""
        stmt = (
            select(
                Category.id,
                Category.name,
                Category.kind,
                Category.is_default,
                func.count(Transaction.id),
                func.coalesce(func.sum(Transaction.amount), 0),
            )
            .outerjoin(Transaction, Transaction.category_id == Category.id)
            .group_by(Category.id)
            .order_by(
                case((Category.kind == KIND_INCOME, 0), else_=1),
                Category.name,
            )
        )
        with self.db.session() as session:
            rows = session.execute(stmt).all()
        return [
            CategoryInfo(
                id=row[0],
                name=row[1],
                kind=row[2],
                is_default=bool(row[3]),
                transactions=int(row[4]),
                total=_to_decimal(row[5]),
            )
            for row in rows
        ]

    def add_category(self, name: str, kind: str) -> int:
        name = _clean_name(name)
        if kind not in (KIND_INCOME, KIND_EXPENSE):
            raise ValueError("Неизвестный вид операции")
        with self.db.session() as session:
            if _name_taken(session, name):
                raise ValueError(f"Категория «{name}» уже существует")
            category = Category(name=name, kind=kind, is_default=False)
            session.add(category)
            session.flush()
            return category.id

    def rename_category(self, category_id: int, name: str) -> None:
        name = _clean_name(name)
        with self.db.session() as session:
            category = _get_category(session, category_id)
            if _name_taken(session, name, exclude_id=category_id):
                raise ValueError(f"Категория «{name}» уже существует")
            category.name = name

    def delete_category(self, category_id: int) -> None:
        with self.db.session() as session:
            category = _get_category(session, category_id)
            used = session.scalar(
                select(func.count())
                .select_from(Transaction)
                .where(Transaction.category_id == category_id)
            )
            if used:
                raise ValueError(
                    f"Нельзя удалить категорию «{category.name}»: "
                    f"с ней связано операций — {used}"
                )
            session.delete(category)

    # ------------------------------------------------------------------
    # Операции
    # ------------------------------------------------------------------
    def transactions(self, flt: TransactionFilter) -> list[TransactionRow]:
        stmt = (
            select(Transaction)
            .join(Transaction.category)
            .options(contains_eager(Transaction.category))
            .where(*flt.date_conditions())
        )
        if flt.kind:
            stmt = stmt.where(Category.kind == flt.kind)
        if flt.category_id is not None:
            stmt = stmt.where(Transaction.category_id == flt.category_id)
        stmt = stmt.order_by(Transaction.occurred_on.desc(), Transaction.id.desc())

        with self.db.session() as session:
            items = session.scalars(stmt).all()
            rows = [
                TransactionRow(
                    id=item.id,
                    occurred_on=item.occurred_on,
                    kind=item.category.kind,
                    category_id=item.category_id,
                    category_name=item.category.name,
                    amount=_to_decimal(item.amount),
                    comment=item.comment,
                )
                for item in items
            ]

        # Поиск выполняется в Python: LIKE в SQLite не учитывает
        # регистр кириллицы, а объём данных в личном приложении небольшой.
        needle = flt.search.strip().lower()
        if needle:
            rows = [
                row
                for row in rows
                if needle in row.comment.lower()
                or needle in row.category_name.lower()
                or needle in str(row.amount)
            ]
        return rows

    def add_transaction(
        self,
        category_id: int,
        amount: Decimal,
        occurred_on: date,
        comment: str = "",
    ) -> int:
        with self.db.session() as session:
            _get_category(session, category_id)
            transaction = Transaction(
                category_id=category_id,
                amount=_quantize(amount),
                occurred_on=occurred_on,
                comment=(comment or "").strip()[:255],
            )
            session.add(transaction)
            session.flush()
            return transaction.id

    def update_transaction(
        self,
        transaction_id: int,
        category_id: int,
        amount: Decimal,
        occurred_on: date,
        comment: str = "",
    ) -> None:
        with self.db.session() as session:
            transaction = session.get(Transaction, transaction_id)
            if transaction is None:
                raise ValueError("Операция не найдена — возможно, она уже удалена")
            _get_category(session, category_id)
            transaction.category_id = category_id
            transaction.amount = _quantize(amount)
            transaction.occurred_on = occurred_on
            transaction.comment = (comment or "").strip()[:255]

    def delete_transaction(self, transaction_id: int) -> None:
        with self.db.session() as session:
            transaction = session.get(Transaction, transaction_id)
            if transaction is None:
                raise ValueError("Операция не найдена — возможно, она уже удалена")
            session.delete(transaction)

    def count_transactions(self) -> int:
        with self.db.session() as session:
            return int(
                session.scalar(select(func.count()).select_from(Transaction)) or 0
            )

    # ------------------------------------------------------------------
    # Аналитика
    # ------------------------------------------------------------------
    def summary(self, flt: TransactionFilter) -> Summary:
        """Итоги по доходам и расходам за период."""
        stmt = (
            select(Category.kind, func.coalesce(func.sum(Transaction.amount), 0))
            .join(Transaction, Transaction.category_id == Category.id)
            .where(*flt.date_conditions())
            .group_by(Category.kind)
        )
        totals: dict[str, Decimal] = {}
        with self.db.session() as session:
            for kind, total in session.execute(stmt):
                totals[kind] = _to_decimal(total)
        return Summary(
            income=totals.get(KIND_INCOME, ZERO),
            expense=totals.get(KIND_EXPENSE, ZERO),
        )

    def totals_by_category(
        self, flt: TransactionFilter, kind: str
    ) -> list[tuple[str, Decimal]]:
        """Суммы по категориям заданного вида, по убыванию."""
        stmt = (
            select(Category.name, func.sum(Transaction.amount))
            .join(Transaction, Transaction.category_id == Category.id)
            .where(Category.kind == kind, *flt.date_conditions())
            .group_by(Category.id)
            .order_by(func.sum(Transaction.amount).desc())
        )
        with self.db.session() as session:
            rows = session.execute(stmt).all()
        return [(name, _to_decimal(total)) for name, total in rows]


# ----------------------------------------------------------------------
# Вспомогательные функции
# ----------------------------------------------------------------------
def _get_category(session, category_id: int) -> Category:
    category = session.get(Category, category_id)
    if category is None:
        raise ValueError("Категория не найдена")
    return category


def _name_taken(session, name: str, exclude_id: int | None = None) -> bool:
    """Проверяет название без учёта регистра.

    ``lower()`` в SQLite не понимает кириллицу, поэтому сравниваем в Python.
    """
    stmt = select(Category.name)
    if exclude_id is not None:
        stmt = stmt.where(Category.id != exclude_id)
    target = name.casefold()
    return any(row[0].casefold() == target for row in session.execute(stmt))


def _clean_name(name: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned:
        raise ValueError("Введите название категории")
    if len(cleaned) > 60:
        raise ValueError("Название категории не должно превышать 60 символов")
    return cleaned


def _to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value.quantize(TWO_PLACES)
    return Decimal(str(value or 0)).quantize(TWO_PLACES)


def _quantize(amount: Decimal) -> Decimal:
    return Decimal(amount).quantize(TWO_PLACES)
