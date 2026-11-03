"""Подключение к SQLite, создание схемы и управление сессиями."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .categories import DEFAULT_CATEGORIES
from .models import Base, Category


class Database:
    """Обёртка над движком SQLAlchemy и фабрикой сессий."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.engine: Engine = create_engine(
            f"sqlite:///{self.path.as_posix()}", future=True
        )
        event.listens_for(self.engine, "connect")(_enable_foreign_keys)
        self._session_factory = sessionmaker(
            bind=self.engine, expire_on_commit=False, future=True
        )

    def create_schema(self) -> None:
        """Создаёт таблицы, если их ещё нет."""
        Base.metadata.create_all(self.engine)

    def close(self) -> None:
        """Закрывает соединения с базой данных."""
        self.engine.dispose()

    def init(self) -> None:
        """Создаёт схему и наполняет категориями при первом запуске."""
        self.create_schema()
        with self.session() as session:
            self._seed_default_categories(session)

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Сессия с автоматическим commit/rollback."""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _seed_default_categories(session: Session) -> None:
        """Наполняет пустую таблицу категорий значениями из словаря."""
        already_filled = session.scalar(select(func.count()).select_from(Category))
        if already_filled:
            return
        for kind, names in DEFAULT_CATEGORIES.items():
            for name in names:
                session.add(Category(name=name, kind=kind, is_default=True))


def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
    """SQLite по умолчанию не проверяет внешние ключи — включаем их."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()
