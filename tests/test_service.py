"""Тесты бизнес-логики: временная БД, категории, операции, итоги."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from finance.categories import DEFAULT_CATEGORIES, CategoryStore
from finance.database import Database
from finance.demo import add_demo_transactions
from finance.repository import FinanceService, TransactionFilter
from finance.utils import (
    format_money,
    parse_amount,
    parse_date,
    previous_month_bounds,
)


class ServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self._tmp.name) / "test.db")
        self.db.init()
        self.service = FinanceService(self.db)
        self.categories = {
            item.name: item for item in self.service.categories()
        }

    def tearDown(self) -> None:
        self.db.engine.dispose()
        self._tmp.cleanup()

    def add(self, name: str, amount: str, day: str = "2026-11-01", comment: str = "") -> int:
        return self.service.add_transaction(
            category_id=self.categories[name].id,
            amount=Decimal(amount),
            occurred_on=parse_date(day),
            comment=comment,
        )

    # ------------------------------------------------------------------
    def test_default_categories_seeded_from_dictionary(self) -> None:
        expected = sum(len(names) for names in DEFAULT_CATEGORIES.values())
        self.assertEqual(len(self.service.categories()), expected)
        self.assertIn("Зарплата", self.categories)
        self.assertEqual(self.categories["Зарплата"].kind, "income")

    def test_category_store_dictionary(self) -> None:
        store = CategoryStore()
        store.reload(self.service.categories())
        self.assertEqual(len(store), len(self.categories))
        self.assertIsNotNone(store.by_name("Продукты"))
        self.assertIsNotNone(store.get(self.categories["Продукты"].id))
        self.assertEqual(
            {item.kind for item in store.all("income")}, {"income"}
        )
        self.assertIn("Продукты", store)

    def test_add_update_delete_transaction(self) -> None:
        transaction_id = self.add("Зарплата", "50000", "2026-11-02", "Аванс")
        rows = self.service.transactions(TransactionFilter())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].kind, "income")
        self.assertEqual(rows[0].amount, Decimal("50000.00"))

        self.service.update_transaction(
            transaction_id,
            self.categories["Продукты"].id,
            Decimal("1234.56"),
            date(2026, 11, 3),
            "Пятёрочка",
        )
        row = self.service.transactions(TransactionFilter())[0]
        self.assertEqual(row.category_name, "Продукты")
        self.assertEqual(row.amount, Decimal("1234.56"))
        self.assertEqual(row.comment, "Пятёрочка")

        self.service.delete_transaction(transaction_id)
        self.assertEqual(self.service.transactions(TransactionFilter()), [])
        self.assertEqual(self.service.count_transactions(), 0)

    def test_filters_by_period_kind_category_and_search(self) -> None:
        self.add("Зарплата", "80000", "2026-11-02")
        self.add("Продукты", "1500", "2026-11-03", "Молоко")
        self.add("Продукты", "900", "2026-10-20", "Хлеб")
        self.add("Транспорт", "700", "2026-11-04", "Метро")

        november = TransactionFilter(
            date_from=date(2026, 11, 1), date_to=date(2026, 11, 30)
        )
        self.assertEqual(len(self.service.transactions(november)), 3)

        expenses = TransactionFilter(
            date_from=date(2026, 11, 1),
            date_to=date(2026, 11, 30),
            kind="expense",
        )
        self.assertEqual(len(self.service.transactions(expenses)), 2)

        milk = self.service.transactions(
            TransactionFilter(search="молОКо")
        )
        self.assertEqual([row.comment for row in milk], ["Молоко"])

        by_category = self.service.transactions(
            TransactionFilter(category_id=self.categories["Транспорт"].id)
        )
        self.assertEqual(len(by_category), 1)

    def test_summary_and_totals(self) -> None:
        self.add("Зарплата", "80000", "2026-11-02")
        self.add("Подработка", "12000", "2026-11-03")
        self.add("Продукты", "1500", "2026-11-03")
        self.add("Транспорт", "700", "2026-11-04")

        flt = TransactionFilter(
            date_from=date(2026, 11, 1), date_to=date(2026, 11, 30)
        )
        summary = self.service.summary(flt)
        self.assertEqual(summary.income, Decimal("92000.00"))
        self.assertEqual(summary.expense, Decimal("2200.00"))
        self.assertEqual(summary.balance, Decimal("89800.00"))

        totals = self.service.totals_by_category(flt, "expense")
        self.assertEqual(
            totals,
            [("Продукты", Decimal("1500.00")), ("Транспорт", Decimal("700.00"))],
        )

    def test_category_crud_and_guards(self) -> None:
        new_id = self.service.add_category("  Хобби  ", "expense")
        names = [item.name for item in self.service.categories()]
        self.assertIn("Хобби", names)

        with self.assertRaises(ValueError):
            self.service.add_category("хобби", "expense")

        self.service.rename_category(new_id, "Хобби и творчество")
        self.assertIn(
            "Хобби и творчество", [item.name for item in self.service.categories()]
        )

        self.service.delete_category(new_id)
        self.assertNotIn(
            "Хобби и творчество", [item.name for item in self.service.categories()]
        )

        used_id = self.categories["Продукты"].id
        self.add("Продукты", "100")
        with self.assertRaises(ValueError):
            self.service.delete_category(used_id)

    def test_demo_data_added_once(self) -> None:
        added = add_demo_transactions(self.service)
        self.assertGreater(added, 0)
        self.assertEqual(self.service.count_transactions(), added)
        self.assertEqual(add_demo_transactions(self.service), 0)


class UtilsTestCase(unittest.TestCase):
    def test_parse_amount(self) -> None:
        self.assertEqual(parse_amount("1 250,50"), Decimal("1250.50"))
        self.assertEqual(parse_amount("1250.5"), Decimal("1250.50"))
        self.assertEqual(parse_amount("1.250,50 ₽"), Decimal("1250.50"))
        for bad in ("", "abc", "0", "-5"):
            with self.assertRaises(ValueError):
                parse_amount(bad)

    def test_format_money(self) -> None:
        self.assertIn("1\xa0234,50", format_money(Decimal("1234.5")))
        self.assertTrue(format_money(Decimal(-10)).startswith("−"))

    def test_previous_month_bounds(self) -> None:
        self.assertEqual(
            previous_month_bounds(date(2026, 1, 15)),
            (date(2025, 12, 1), date(2025, 12, 31)),
        )


if __name__ == "__main__":
    unittest.main()
