"""Форматирование и разбор денег и дат, границы периодов."""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from .settings import CURRENCY_SYMBOL, DATE_FORMAT

NBSP = "\u00a0"
TWO_PLACES = Decimal("0.01")
MAX_AMOUNT = Decimal("999999999.99")
ZERO = Decimal("0.00")


def format_amount(value: Decimal | float) -> str:
    """Число без символа валюты: ``12 345,67``."""
    amount = Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    text = f"{abs(amount):,.2f}"
    return text.replace(",", NBSP).replace(".", ",")


def format_money(value: Decimal | float, *, with_symbol: bool = True) -> str:
    """Денежная сумма с символом валюты и знаком минус для отрицательных."""
    amount = Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    sign = "−" if amount < 0 else ""
    symbol = f"{NBSP}{CURRENCY_SYMBOL}" if with_symbol else ""
    return f"{sign}{format_amount(amount)}{symbol}"


def parse_amount(raw: str) -> Decimal:
    """Разбирает сумму из строки. Поддерживает ``1 250,50`` и ``1250.50``."""
    text = raw.strip().replace(NBSP, "").replace("\u2009", "").replace(" ", "")
    text = text.replace(CURRENCY_SYMBOL, "").replace("₽", "")
    if not text:
        raise ValueError("Введите сумму операции")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        amount = Decimal(text)
    except InvalidOperation:
        raise ValueError("Сумма должна быть числом, например 1250,50") from None
    if not amount.is_finite():
        raise ValueError("Сумма должна быть числом")
    if amount <= 0:
        raise ValueError("Сумма должна быть больше нуля")
    if amount > MAX_AMOUNT:
        raise ValueError("Слишком большая сумма (максимум 999 999 999,99)")
    return amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def format_date(value: date) -> str:
    return value.strftime(DATE_FORMAT)


def parse_date(raw: str) -> date:
    """Разбирает дату из строки в форматах ДД.ММ.ГГГГ, ГГГГ-ММ-ДД, ДД/ММ/ГГГГ."""
    text = raw.strip()
    if not text:
        raise ValueError("Укажите дату операции")
    for fmt in (DATE_FORMAT, "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError("Не удалось разобрать дату. Используйте формат ДД.ММ.ГГГГ")


def month_bounds(day: date) -> tuple[date, date]:
    first = day.replace(day=1)
    last = day.replace(day=calendar.monthrange(day.year, day.month)[1])
    return first, last


def previous_month_bounds(day: date) -> tuple[date, date]:
    first_current = day.replace(day=1)
    return month_bounds(first_current - timedelta(days=1))


def year_bounds(day: date) -> tuple[date, date]:
    return date(day.year, 1, 1), date(day.year, 12, 31)


def format_period(start: date | None, end: date | None) -> str:
    """Человекочитаемое описание периода."""
    if start is None and end is None:
        return "всё время"
    if start is not None and end is not None:
        return f"{format_date(start)} — {format_date(end)}"
    if start is not None:
        return f"с {format_date(start)}"
    return f"по {format_date(end)}"
