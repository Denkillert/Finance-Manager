"""Категории: словарь значений по умолчанию и хранилище в памяти.

Категории по умолчанию описаны вложенным словарём
``вид операции -> (названия категорий)``. Этот словарь используется
только при первом запуске, когда таблица ``categories`` ещё пуста.
Дальше приложение работает с данными из БД через :class:`CategoryStore` —
это тоже словарь, но уже с быстрым доступом по id и по названию.
"""

from __future__ import annotations

from collections.abc import Iterable

from .dto import CategoryInfo

# Словарь категорий по умолчанию. Ключ — код вида операции.
DEFAULT_CATEGORIES: dict[str, tuple[str, ...]] = {
    "income": (
        "Зарплата",
        "Подработка",
        "Инвестиции",
        "Подарки",
        "Прочие доходы",
    ),
    "expense": (
        "Продукты",
        "Жильё и ЖКХ",
        "Транспорт",
        "Здоровье",
        "Развлечения",
        "Одежда",
        "Образование",
        "Кафе и рестораны",
        "Связь и интернет",
        "Прочие расходы",
    ),
}


class CategoryStore:
    """Словарь категорий в памяти.

    Категории хранятся в двух словарях: ``id -> категория`` и
    ``название -> категория``. Это даёт доступ за O(1) и при построении
    таблиц, и при проверке названий на уникальность.
    """

    def __init__(self) -> None:
        self._by_id: dict[int, CategoryInfo] = {}
        self._by_name: dict[str, CategoryInfo] = {}

    def reload(self, categories: Iterable[CategoryInfo]) -> None:
        """Полностью перечитывает словарь категорий."""
        items = list(categories)
        self._by_id = {item.id: item for item in items}
        self._by_name = {item.name: item for item in items}

    def get(self, category_id: int) -> CategoryInfo | None:
        return self._by_id.get(category_id)

    def by_name(self, name: str) -> CategoryInfo | None:
        return self._by_name.get(name)

    def all(self, kind: str | None = None) -> list[CategoryInfo]:
        """Категории, отсортированные по виду операции и названию."""
        items = sorted(self._by_id.values(), key=_sort_key)
        if kind is None:
            return items
        return [item for item in items if item.kind == kind]

    def names(self, kind: str | None = None) -> list[str]:
        return [item.name for item in self.all(kind)]

    def __len__(self) -> int:
        return len(self._by_id)

    def __contains__(self, name: object) -> bool:
        return name in self._by_name


def _sort_key(category: CategoryInfo) -> tuple[int, str]:
    return (0 if category.kind == "income" else 1, category.name.lower())
