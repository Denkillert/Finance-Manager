"""Неизменяемые настройки приложения.

Все значения, которые не должны меняться во время работы, хранятся здесь
в кортежах. Кортеж нельзя изменить после создания, поэтому такие настройки
защищены от случайной перезаписи (в отличие от списка или словаря).
"""

from __future__ import annotations

APP_NAME = "Менеджер личных финансов"
APP_VERSION = "1.0.0"

# (ширина, высота) главного окна и минимальный размер — кортежи
WINDOW_SIZE = (1180, 780)
MIN_WINDOW_SIZE = (1024, 680)

# Формат даты, используемый в интерфейсе
DATE_FORMAT = "%d.%m.%Y"
DB_FILENAME = "finance.db"

# Символ валюты приложения
CURRENCY_SYMBOL = "₽"

# Виды операций: (код, подпись, цвет)
KINDS = (
    ("income", "Доход", "#15803D"),
    ("expense", "Расход", "#B91C1C"),
)
KIND_LABELS = {code: label for code, label, _color in KINDS}
KIND_COLORS = {code: color for code, _label, color in KINDS}

# Периоды для фильтра: (подпись, код)
PERIODS = (
    ("Текущий месяц", "month"),
    ("Прошлый месяц", "prev_month"),
    ("Текущий год", "year"),
    ("Всё время", "all"),
    ("Свой период", "custom"),
)
PERIOD_CODES = {label: code for label, code in PERIODS}

# Палитра для диаграммы
CHART_COLORS = (
    "#3B82F6",
    "#8B5CF6",
    "#EC4899",
    "#F59E0B",
    "#10B981",
    "#06B6D4",
    "#EF4444",
    "#84CC16",
)
