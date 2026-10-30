"""Резиденты: список с поиском, добавление, изменение, удаление."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from typing import Dict, List, Optional

from ..constants import DOCUMENT_TYPES, RESIDENT_STATUSES, STATUS_LEFT
from ..errors import DuplicateError, IntegrityConflict, NotFound, ServiceError, ValidationError
from ..validation import choice, clean_text, like_pattern, parse_date, parse_int
from .base import Service, where_clause

_LIST_SQL = """
    SELECT r.resident_id, r.full_name,
           COALESCE(r.document_number, 'Нет'), COALESCE(r.document_type, 'Нет'),
           COALESCE(r.phone, 'Нет'), TO_CHAR(r.admission_date, 'DD.MM.YYYY'),
           r.status, COALESCE(r.room_number::text, 'Нет'), COALESCE(c.full_name, 'Нет')
    FROM Residents r
    LEFT JOIN Curators c ON r.curator_id = c.curator_id
"""

_FORM_FIELDS = ("full_name", "birth_date", "document_type", "document_number", "phone",
                "admission_date", "status", "room_number", "curator_id")
_GET_SQL = "SELECT " + ", ".join(_FORM_FIELDS) + " FROM Residents"


def clean_resident(data: Dict[str, object]) -> Dict[str, object]:
    """Проверяет данные формы резидента и приводит их к типам БД."""
    birth_date = parse_date(data.get("birth_date"), label="Дата рождения")
    if birth_date is not None and not (date(1900, 1, 1) <= birth_date <= date.today()):
        raise ValidationError("Поле «Дата рождения»: дата вне допустимого диапазона")
    return {
        "full_name": clean_text(data.get("full_name"), label="ФИО", required=True, max_length=100),
        "birth_date": birth_date,
        "document_type": clean_text(data.get("document_type"), label="Тип документа", max_length=50),
        "document_number": clean_text(data.get("document_number"), label="Номер документа", max_length=50),
        "phone": clean_text(data.get("phone"), label="Телефон", max_length=20),
        "admission_date": parse_date(data.get("admission_date"), label="Дата поступления", required=True),
        "status": choice(data.get("status"), RESIDENT_STATUSES, label="Статус"),
        "room_number": parse_int(data.get("room_number"), label="Комната", minimum=1),
        "curator_id": parse_int(data.get("curator_id"), label="Куратор", minimum=1),
    }


class ResidentService(Service):
    document_types = DOCUMENT_TYPES
    statuses = RESIDENT_STATUSES

    def list(self, search: str = "") -> List[tuple]:
        """Резиденты, видимые пользователю. Поиск: каждое слово должно встретиться в ФИО."""
        conditions, params = self._scope("r.curator_id")
        for word in (search or "").split():
            conditions.append("r.full_name ILIKE %s")
            params.append(like_pattern(word))
        sql = _LIST_SQL + where_clause(conditions) + " ORDER BY r.resident_id"
        return self.db.fetch_all(sql, params)

    def get(self, resident_id: int) -> Dict[str, str]:
        conditions, params = self._scope("curator_id")
        conditions.append("resident_id = %s")
        params.append(resident_id)
        row = self.db.fetch_one(_GET_SQL + where_clause(conditions), params)
        if row is None:
            raise NotFound("Резидент не найден")
        return {name: "" if value is None else str(value) for name, value in zip(_FORM_FIELDS, row)}

    def create(self, data: Dict[str, object]) -> int:
        self._require_admin()
        values = clean_resident(data)
        with self._duplicate_message():
            with self.db.transaction() as cur:
                self._ensure_room_available(cur, values["room_number"], values["status"])
                cur.execute(
                    "INSERT INTO Residents (full_name, birth_date, document_type, document_number, "
                    "phone, admission_date, status, room_number, curator_id, created_by) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING resident_id",
                    (*(values[name] for name in _FORM_FIELDS), self.user.id),
                )
                return cur.fetchone()[0]

    def update(self, resident_id: int, data: Dict[str, object]) -> None:
        self._require_admin()
        values = clean_resident(data)
        with self._duplicate_message():
            with self.db.transaction() as cur:
                self._ensure_room_available(cur, values["room_number"], values["status"],
                                            exclude_resident_id=resident_id)
                cur.execute(
                    "UPDATE Residents SET full_name = %s, birth_date = %s, document_type = %s, "
                    "document_number = %s, phone = %s, admission_date = %s, status = %s, "
                    "room_number = %s, curator_id = %s, updated_date = CURRENT_TIMESTAMP "
                    "WHERE resident_id = %s",
                    (*(values[name] for name in _FORM_FIELDS), resident_id),
                )
                if cur.rowcount == 0:
                    raise NotFound("Резидент не найден")

    def delete(self, resident_id: int) -> None:
        self._require_admin()
        try:
            deleted = self.db.execute("DELETE FROM Residents WHERE resident_id = %s", (resident_id,))
        except IntegrityConflict:
            raise IntegrityConflict(
                "Нельзя удалить резидента: есть связанные ИПР или выдачи помощи. "
                f"Установите статус «{STATUS_LEFT}».") from None
        if deleted == 0:
            raise NotFound("Резидент не найден")

    @staticmethod
    @contextmanager
    def _duplicate_message():
        try:
            yield
        except DuplicateError:
            raise DuplicateError("Резидент с таким номером документа уже существует") from None

    @staticmethod
    def _ensure_room_available(cur, room_number: Optional[int], status: str,
                               exclude_resident_id: Optional[int] = None) -> None:
        """Комната существует, не на ремонте и в ней есть свободное место."""
        if room_number is None or status == STATUS_LEFT:
            return
        # FOR UPDATE: два одновременных заселения в последнюю свободную койку не пройдут оба.
        cur.execute("SELECT capacity, room_status FROM Rooms WHERE room_number = %s FOR UPDATE",
                    (room_number,))
        room = cur.fetchone()
        if room is None:
            raise ServiceError(f"Комнаты №{room_number} не существует")
        capacity, room_status = room
        if room_status == "На ремонте":
            raise ServiceError(f"Комната №{room_number} на ремонте")
        cur.execute(
            "SELECT COUNT(*) FROM Residents WHERE room_number = %s AND status <> %s "
            "AND resident_id IS DISTINCT FROM %s",
            (room_number, STATUS_LEFT, exclude_resident_id),
        )
        occupied = cur.fetchone()[0]
        if occupied >= capacity:
            raise ServiceError(f"Комната №{room_number} заполнена ({occupied} из {capacity})")
