"""Слой доступа к PostgreSQL.

Сервисы работают через Database.fetch_all / fetch_one / transaction и не знают
про psycopg2. Это упрощает тесты (в них подставляется поддельная БД) и
позволяет в одном месте превращать ошибки драйвера в понятные исключения.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator, Sequence

from .config import DbConfig
from .errors import (DatabaseUnavailable, DuplicateError, IntegrityConflict,
                     ServiceError)

log = logging.getLogger(__name__)


def translate_db_error(exc: Exception) -> Exception:
    """Ошибка драйвера -> исключение приложения (или та же ошибка, если не знаем её)."""
    code = getattr(exc, "pgcode", None)
    constraint = getattr(getattr(exc, "diag", None), "constraint_name", None) or "?"
    if code == "23505":
        return DuplicateError(f"Такая запись уже существует (ограничение {constraint})")
    if code == "23503":
        return IntegrityConflict(f"Операция нарушает связи между данными (ограничение {constraint})")
    if code == "23514":
        return ServiceError(f"Данные не проходят проверку (ограничение {constraint})")
    if type(exc).__name__ == "OperationalError":
        return DatabaseUnavailable("Потеряно соединение с базой данных")
    return exc


class Database:
    def __init__(self, config: DbConfig) -> None:
        self._config = config
        self._conn = None

    @property
    def is_connected(self) -> bool:
        return self._conn is not None and not self._conn.closed

    def connect(self) -> None:
        import psycopg2  # импорт здесь, чтобы тесты работали без драйвера

        cfg = self._config
        try:
            self._conn = psycopg2.connect(
                host=cfg.host, port=cfg.port, dbname=cfg.name,
                user=cfg.user, password=cfg.password, connect_timeout=5,
            )
        except psycopg2.OperationalError as exc:
            log.error("Не удалось подключиться к БД: %s", exc)
            raise DatabaseUnavailable(
                f"Не удалось подключиться к базе «{cfg.name}» на {cfg.host}:{cfg.port}. "
                "Проверьте, что PostgreSQL запущен и настройки в .env верны."
            ) from exc

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @contextmanager
    def transaction(self) -> Iterator:
        """Курсор в транзакции: commit при успехе, rollback при любой ошибке."""
        if not self.is_connected:
            raise DatabaseUnavailable("Нет подключения к базе данных")
        cursor = self._conn.cursor()
        try:
            yield cursor
            self._conn.commit()
        except ServiceError:
            self._conn.rollback()
            raise
        except Exception as exc:
            self._conn.rollback()
            translated = translate_db_error(exc)
            if translated is exc:
                raise
            raise translated from exc
        finally:
            cursor.close()

    def fetch_all(self, sql: str, params: Sequence = ()) -> list:
        with self.transaction() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def fetch_one(self, sql: str, params: Sequence = ()):
        with self.transaction() as cur:
            cur.execute(sql, params)
            return cur.fetchone()

    def execute(self, sql: str, params: Sequence = ()) -> int:
        with self.transaction() as cur:
            cur.execute(sql, params)
            return cur.rowcount
