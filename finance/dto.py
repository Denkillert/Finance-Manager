"""Простые неизменяемые структуры для обмена данными с интерфейсом.

ORM-объекты привязаны к сессии, поэтому наружу (в Tkinter) отдаём
обычные frozen dataclass'ы. Их нельзя случайно изменить, а читать
их можно в любой момент.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class CategoryInfo:
    """Категория с агрегированной статистикой."""

    id: int
    name: str
    kind: str
    is_default: bool = False
    transactions: int = 0
    total: Decimal = ZERO


@dataclass(frozen=True)
class TransactionRow:
    """Одна операция в том виде, в котором её показывает таблица."""

    id: int
    occurred_on: date
    kind: str
    category_id: int
    category_name: str
    amount: Decimal
    comment: str = ""


@dataclass(frozen=True)
class Summary:
    """Итоги по доходам и расходам."""

    income: Decimal = ZERO
    expense: Decimal = ZERO

    @property
    def balance(self) -> Decimal:
        return self.income - self.expense
