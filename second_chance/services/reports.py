"""Отчёты, статистика и выгрузка в CSV."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple

from ..constants import STATUS_LEFT
from .base import Service, where_clause

_FORMULA_PREFIXES = ("=", "+", "-", "@")


@dataclass(frozen=True)
class Report:
    title: str
    headers: Tuple[str, ...]
    rows: List[tuple]


def _safe_cell(value):
    """Защита от CSV-инъекции: Excel выполняет ячейки, начинающиеся с = + - @."""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def export_csv(path, headers: Sequence[str], rows: Sequence[Sequence]) -> None:
    """CSV под русский Excel: разделитель ';' и BOM, чтобы кириллица читалась."""
    with Path(path).open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([_safe_cell(cell) for cell in row])


class ReportService(Service):
    LIMIT = 500

    def current_residents(self) -> Report:
        conditions, params = self._scope("r.curator_id")
        conditions.append("r.status <> %s")
        params.append(STATUS_LEFT)
        rows = self.db.fetch_all(
            "SELECT r.full_name, COALESCE(r.room_number::text, 'Нет'), "
            "       TO_CHAR(r.admission_date, 'DD.MM.YYYY'), r.status, COALESCE(c.full_name, 'Нет'), "
            "       COALESCE((SELECT i.ipr_status FROM IPR i WHERE i.resident_id = r.resident_id "
            "                 ORDER BY i.creation_date DESC, i.ipr_id DESC LIMIT 1), 'Нет ИПР') "
            "FROM Residents r LEFT JOIN Curators c ON r.curator_id = c.curator_id"
            + where_clause(conditions) + " ORDER BY r.room_number, r.full_name",
            params,
        )
        return Report("Текущий состав резидентов",
                      ("ФИО", "Комната", "Дата поступления", "Статус", "Куратор", "ИПР"), rows)

    def ipr_progress(self) -> Report:
        conditions, params = self._scope("e.responsible_curator_id")
        rows = self.db.fetch_all(
            "SELECT r.full_name, i.main_goal, e.title, TO_CHAR(e.planned_date, 'DD.MM.YYYY'), "
            "       e.event_status, COALESCE(e.result, 'Нет результата') "
            "FROM Events e JOIN IPR i ON e.ipr_id = i.ipr_id "
            "JOIN Residents r ON i.resident_id = r.resident_id"
            + where_clause(conditions) + " ORDER BY e.planned_date DESC LIMIT %s",
            (*params, self.LIMIT),
        )
        return Report("Выполнение ИПР",
                      ("Резидент", "Цель ИПР", "Мероприятие", "Дата", "Статус", "Результат"), rows)

    def aid_issued(self) -> Report:
        conditions, params = self._scope("r.curator_id")
        rows = self.db.fetch_all(
            "SELECT TO_CHAR(a.distribution_date, 'DD.MM.YYYY'), r.full_name, w.name, "
            "       a.quantity || ' ' || w.unit, u.full_name "
            "FROM AidDistribution a JOIN Residents r ON a.resident_id = r.resident_id "
            "JOIN Warehouse w ON a.item_id = w.item_id "
            "JOIN SystemUsers u ON a.issued_by = u.user_id"
            + where_clause(conditions) + " ORDER BY a.distribution_date DESC LIMIT %s",
            (*params, self.LIMIT),
        )
        return Report("Выдача материальной помощи",
                      ("Дата", "Резидент", "Позиция", "Количество", "Выдал"), rows)

    def statistics(self) -> List[Tuple[str, int]]:
        self._require_admin()
        labels = ("Всего резидентов", "В основном потоке", "На карантине", "Свободных комнат",
                  "Занятых комнат", "Позиций на складе", "Активных ИПР", "Всего мероприятий",
                  "Выполненных мероприятий", "Всего выдач помощи")
        row = self.db.fetch_one(
            "SELECT (SELECT COUNT(*) FROM Residents), "
            "(SELECT COUNT(*) FROM Residents WHERE status = 'Основной поток'), "
            "(SELECT COUNT(*) FROM Residents WHERE status = 'На карантине'), "
            "(SELECT COUNT(*) FROM Rooms WHERE room_status = 'Свободно'), "
            "(SELECT COUNT(*) FROM Rooms WHERE room_status = 'Занято'), "
            "(SELECT COUNT(*) FROM Warehouse), "
            "(SELECT COUNT(*) FROM IPR WHERE ipr_status = 'Активна'), "
            "(SELECT COUNT(*) FROM Events), "
            "(SELECT COUNT(*) FROM Events WHERE event_status = 'Выполнено'), "
            "(SELECT COUNT(*) FROM AidDistribution)")
        return list(zip(labels, row))
