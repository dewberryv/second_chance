"""Общая часть сервисов: доступ к БД, текущий пользователь, права."""
from __future__ import annotations

from typing import List, Sequence, Tuple

from ..errors import PermissionDenied
from ..models import CurrentUser


def where_clause(conditions: Sequence[str]) -> str:
    return (" WHERE " + " AND ".join(conditions)) if conditions else ""


class Service:
    def __init__(self, db, user: CurrentUser) -> None:
        self.db = db
        self.user = user

    def _require_admin(self) -> None:
        if not self.user.is_admin:
            raise PermissionDenied("Действие доступно только администратору")

    def _require_curator(self) -> int:
        """Куратор, привязанный к записи в Curators. Возвращает его curator_id."""
        if self.user.is_admin or self.user.curator_id is None:
            raise PermissionDenied(
                "Действие доступно куратору, учётная запись которого привязана к сотруднику")
        return self.user.curator_id

    def _scope(self, column: str) -> Tuple[List[str], list]:
        """Условие видимости: администратор видит всё, куратор - только свои записи."""
        if self.user.is_admin:
            return [], []
        return [f"{column} = %s"], [self.user.curator_id]
