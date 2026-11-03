"""Точка входа приложения «Менеджер личных финансов»."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from finance.settings import DB_FILENAME


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Учёт личных доходов и расходов")
    parser.add_argument(
        "--db",
        metavar="PATH",
        help="путь к файлу базы данных (по умолчанию finance.db рядом с main.py)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="добавить демонстрационные операции, если база пустая",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        from finance.database import Database
        from finance.repository import FinanceService
        from finance.ui.app import FinanceApp
    except ModuleNotFoundError as exc:
        if exc.name in ("tkinter", "_tkinter"):
            print(
                "В этой сборке Python отсутствует Tkinter.\n"
                "Запустите приложение через run.bat или командой:\n"
                r"  .venv\Scripts\python.exe main.py",
                file=sys.stderr,
            )
            return 1
        print(
            f"Не удалось загрузить приложение: нет модуля «{exc.name}».\n"
            "Установите зависимости командой: pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 1

    db_path = (
        Path(args.db).expanduser()
        if args.db
        else Path(__file__).resolve().parent / DB_FILENAME
    )
    database = Database(db_path)
    service = FinanceService(database)
    service.db.init()

    if args.demo:
        from finance.demo import add_demo_transactions

        added = add_demo_transactions(service)
        if added:
            print(f"Добавлено демонстрационных операций: {added}")

    app = FinanceApp(service)
    app.mainloop()
    database.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
