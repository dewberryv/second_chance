"""Поддельная БД для тестов сервисов: записывает запросы и отдаёт заранее заданные ответы.

Ответы берутся по очереди при каждом fetchone/fetchall/fetch_one/fetch_all.
Тесты проверяют логику сервиса (порядок запросов, параметры, права, ошибки),
а не работу самого PostgreSQL.
"""
from contextlib import contextmanager

from second_chance.models import CurrentUser

ADMIN = CurrentUser(id=1, username="admin", full_name="Админ", role="admin", curator_id=None)
CURATOR = CurrentUser(id=2, username="curator", full_name="Куратор", role="curator", curator_id=5)
CURATOR_WITHOUT_PROFILE = CurrentUser(id=3, username="c2", full_name="Без профиля",
                                      role="curator", curator_id=None)


class FakeCursor:
    def __init__(self, db):
        self._db = db
        self.rowcount = 0

    def execute(self, sql, params=()):
        self._db.calls.append((sql, tuple(params)))
        self.rowcount = self._db.next_rowcount()

    def fetchone(self):
        return self._db.next_result()

    def fetchall(self):
        return self._db.next_result()


class FakeDatabase:
    def __init__(self, results=(), rowcounts=(), error=None):
        self.calls = []
        self.committed = 0
        self.rolled_back = 0
        self._results = list(results)
        self._rowcounts = list(rowcounts)
        self._error = error

    def next_result(self):
        return self._results.pop(0) if self._results else None

    def next_rowcount(self):
        return self._rowcounts.pop(0) if self._rowcounts else 1

    def _record(self, sql, params):
        self.calls.append((sql, tuple(params)))
        if self._error is not None:
            raise self._error

    def fetch_all(self, sql, params=()):
        self._record(sql, params)
        return self.next_result() or []

    def fetch_one(self, sql, params=()):
        self._record(sql, params)
        return self.next_result()

    def execute(self, sql, params=()):
        self._record(sql, params)
        return self.next_rowcount()

    @contextmanager
    def transaction(self):
        try:
            yield FakeCursor(self)
        except Exception:
            self.rolled_back += 1
            raise
        else:
            self.committed += 1

    def sql_log(self):
        return [sql for sql, _ in self.calls]
