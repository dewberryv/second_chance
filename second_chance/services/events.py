"""Мероприятия в рамках ИПР."""
from __future__ import annotations

from typing import Dict, List

from ..constants import (EVENT_FINISHED_STATUSES, EVENT_NEW_STATUSES, EVENT_TYPES,
                         EVENT_UPDATE_STATUSES, IPR_STATUS_ACTIVE)
from ..errors import NotFound, PermissionDenied
from ..validation import choice, clean_text, parse_date, parse_int
from .base import Service, where_clause


def clean_event(data: Dict[str, object]) -> Dict[str, object]:
    return {
        "ipr_id": parse_int(data.get("ipr_id"), label="ИПР", required=True, minimum=1),
        "event_type": choice(data.get("event_type"), EVENT_TYPES, label="Тип"),
        "title": clean_text(data.get("title"), label="Название", required=True, max_length=200),
        "description": clean_text(data.get("description"), label="Описание"),
        "planned_date": parse_date(data.get("planned_date"), label="Плановая дата", required=True),
        "event_status": choice(data.get("event_status"), EVENT_NEW_STATUSES, label="Статус"),
        "org_id": parse_int(data.get("org_id"), label="Организация", minimum=1),
    }


class EventService(Service):
    types = EVENT_TYPES
    new_statuses = EVENT_NEW_STATUSES
    update_statuses = EVENT_UPDATE_STATUSES

    def list(self) -> List[tuple]:
        conditions, params = self._scope("e.responsible_curator_id")
        return self.db.fetch_all(
            "SELECT e.event_id, i.ipr_id, r.full_name, e.event_type, e.title, "
            "       TO_CHAR(e.planned_date, 'DD.MM.YYYY'), e.event_status, "
            "       COALESCE(LEFT(e.result, 30), 'Нет') "
            "FROM Events e JOIN IPR i ON e.ipr_id = i.ipr_id "
            "JOIN Residents r ON i.resident_id = r.resident_id"
            + where_clause(conditions) + " ORDER BY e.planned_date DESC, e.event_id DESC",
            params,
        )

    def active_iprs(self) -> List[tuple]:
        conditions, params = self._scope("i.curator_id")
        conditions.append("i.ipr_status = %s")
        params.append(IPR_STATUS_ACTIVE)
        return self.db.fetch_all(
            "SELECT i.ipr_id, r.full_name || ' - ' || LEFT(i.main_goal, 40) "
            "FROM IPR i JOIN Residents r ON i.resident_id = r.resident_id"
            + where_clause(conditions) + " ORDER BY r.full_name",
            params,
        )

    def create(self, data: Dict[str, object]) -> int:
        curator_id = self._require_curator()
        values = clean_event(data)
        with self.db.transaction() as cur:
            cur.execute("SELECT 1 FROM IPR WHERE ipr_id = %s AND curator_id = %s",
                        (values["ipr_id"], curator_id))
            if cur.fetchone() is None:
                raise PermissionDenied("Можно добавлять мероприятия только в свои ИПР")
            cur.execute(
                "INSERT INTO Events (ipr_id, event_type, title, description, planned_date, "
                "event_status, org_id, responsible_curator_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING event_id",
                (values["ipr_id"], values["event_type"], values["title"], values["description"],
                 values["planned_date"], values["event_status"], values["org_id"], curator_id),
            )
            return cur.fetchone()[0]

    def change_status(self, event_id: int, status: str, result: str = "") -> None:
        curator_id = self._require_curator()
        status = choice(status, EVENT_UPDATE_STATUSES, label="Статус")
        result = clean_text(result, label="Результат")
        updated = self.db.execute(
            "UPDATE Events SET event_status = %s, result = %s, "
            "actual_date = CASE WHEN %s IN %s THEN CURRENT_DATE ELSE actual_date END "
            "WHERE event_id = %s AND responsible_curator_id = %s",
            (status, result, status, EVENT_FINISHED_STATUSES, event_id, curator_id),
        )
        if updated == 0:
            raise NotFound("Мероприятие не найдено или принадлежит другому куратору")
