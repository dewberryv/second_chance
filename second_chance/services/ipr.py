"""ИПР - индивидуальные программы реабилитации."""
from __future__ import annotations

from datetime import date
from typing import Dict, List

from ..constants import IPR_NEW_STATUSES
from ..errors import NotFound, PermissionDenied, ValidationError
from ..validation import choice, clean_text, parse_date, parse_int
from .base import Service, where_clause


def clean_ipr(data: Dict[str, object]) -> Dict[str, object]:
    start = parse_date(data.get("start_date"), label="Дата начала", required=True)
    end = parse_date(data.get("end_date"), label="Дата окончания")
    if end is not None and end < start:
        raise ValidationError("Дата окончания не может быть раньше даты начала")
    return {
        "resident_id": parse_int(data.get("resident_id"), label="Резидент", required=True, minimum=1),
        "start_date": start,
        "end_date": end,
        "ipr_status": choice(data.get("ipr_status"), IPR_NEW_STATUSES, label="Статус"),
        "main_goal": clean_text(data.get("main_goal"), label="Основная цель", required=True),
        "specific_goals": clean_text(data.get("specific_goals"), label="Конкретные задачи"),
        "success_criteria": clean_text(data.get("success_criteria"), label="Критерии успеха"),
        "notes": clean_text(data.get("notes"), label="Примечания"),
    }


class IprService(Service):
    statuses = IPR_NEW_STATUSES

    def list(self) -> List[tuple]:
        conditions, params = self._scope("i.curator_id")
        return self.db.fetch_all(
            "SELECT i.ipr_id, r.full_name, TO_CHAR(i.creation_date, 'DD.MM.YYYY'), i.ipr_status, "
            "       LEFT(i.main_goal, 50), c.full_name "
            "FROM IPR i JOIN Residents r ON i.resident_id = r.resident_id "
            "JOIN Curators c ON i.curator_id = c.curator_id"
            + where_clause(conditions) + " ORDER BY i.creation_date DESC, i.ipr_id DESC",
            params,
        )

    def residents_without_ipr(self) -> List[tuple]:
        conditions, params = self._scope("r.curator_id")
        conditions.append("i.ipr_id IS NULL")
        return self.db.fetch_all(
            "SELECT r.resident_id, r.full_name FROM Residents r "
            "LEFT JOIN IPR i ON r.resident_id = i.resident_id"
            + where_clause(conditions) + " ORDER BY r.full_name",
            params,
        )

    def create(self, data: Dict[str, object]) -> int:
        curator_id = self._require_curator()
        values = clean_ipr(data)
        with self.db.transaction() as cur:
            cur.execute("SELECT curator_id FROM Residents WHERE resident_id = %s", (values["resident_id"],))
            owner = cur.fetchone()
            if owner is None:
                raise NotFound("Резидент не найден")
            if owner[0] != curator_id:
                raise PermissionDenied("Можно создавать ИПР только для своих резидентов")
            cur.execute(
                "INSERT INTO IPR (resident_id, curator_id, creation_date, start_date, end_date, "
                "ipr_status, main_goal, specific_goals, success_criteria, notes) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING ipr_id",
                (values["resident_id"], curator_id, date.today(), values["start_date"],
                 values["end_date"], values["ipr_status"], values["main_goal"],
                 values["specific_goals"], values["success_criteria"], values["notes"]),
            )
            return cur.fetchone()[0]

    def delete(self, ipr_id: int) -> None:
        curator_id = self._require_curator()
        deleted = self.db.execute("DELETE FROM IPR WHERE ipr_id = %s AND curator_id = %s",
                                  (ipr_id, curator_id))
        if deleted == 0:
            raise NotFound("ИПР не найдена или принадлежит другому куратору")
