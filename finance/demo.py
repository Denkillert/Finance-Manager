"""Демонстрационные данные для быстрого знакомства с приложением."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from .repository import FinanceService

# (вид, категория, сумма, сколько дней назад, комментарий)
DEMO_TRANSACTIONS: tuple[tuple[str, str, str, int, str], ...] = (
    ("income", "Зарплата", "85000", 2, "Зарплата за месяц"),
    ("income", "Зарплата", "85000", 32, "Зарплата за прошлый месяц"),
    ("income", "Подработка", "12000", 12, "Фриланс-проект"),
    ("income", "Инвестиции", "3400", 25, "Дивиденды"),
    ("income", "Подарки", "5000", 40, "Подарок на день рождения"),
    ("expense", "Продукты", "2340", 1, "Пятёрочка"),
    ("expense", "Продукты", "3120", 3, "Лента"),
    ("expense", "Продукты", "2780", 6, "Магнит"),
    ("expense", "Продукты", "4100", 20, "Продукты на неделю"),
    ("expense", "Жильё и ЖКХ", "6400", 4, "Квартплата"),
    ("expense", "Жильё и ЖКХ", "6400", 34, "Квартплата"),
    ("expense", "Транспорт", "1250", 5, "Проездной"),
    ("expense", "Транспорт", "1250", 35, "Проездной"),
    ("expense", "Кафе и рестораны", "1850", 8, "Ужин с друзьями"),
    ("expense", "Кафе и рестораны", "2200", 22, "Ресторан"),
    ("expense", "Развлечения", "900", 10, "Кино"),
    ("expense", "Здоровье", "2400", 14, "Аптека"),
    ("expense", "Одежда", "5600", 16, "Куртка"),
    ("expense", "Связь и интернет", "900", 7, "Мобильная связь"),
    ("expense", "Образование", "3900", 28, "Онлайн-курс"),
)


def add_demo_transactions(service: FinanceService) -> int:
    """Добавляет примеры операций, если база ещё пустая."""
    if service.count_transactions():
        return 0
    categories = {item.name: item for item in service.categories()}
    today = date.today()
    added = 0
    for kind, category_name, amount, days_ago, comment in DEMO_TRANSACTIONS:
        category = categories.get(category_name)
        if category is None or category.kind != kind:
            continue
        service.add_transaction(
            category_id=category.id,
            amount=Decimal(amount),
            occurred_on=today - timedelta(days=days_ago),
            comment=comment,
        )
        added += 1
    return added
