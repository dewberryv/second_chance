"""Выдача материальной помощи резидентам."""
from __future__ import annotations

from typing import Dict, List

from ..errors import NotFound, PermissionDenied, ServiceError
from ..validation import clean_text, parse_decimal, parse_int
from .base import Service, where_clause


class AidService(Service):
    def list(self) -> List[tuple]:
        conditions, params = self._scope("r.curator_id")
        return self.db.fetch_all(
            "SELECT a.distribution_id, TO_CHAR(a.distribution_date, 'DD.MM.YYYY HH24:MI'), "
            "       r.full_name, w.name, a.quantity || ' ' || w.unit, u.full_name "
            "FROM AidDistribution a "
            "JOIN Residents r ON a.resident_id = r.resident_id "
            "JOIN Warehouse w ON a.item_id = w.item_id "
            "JOIN SystemUsers u ON a.issued_by = u.user_id"
            + where_clause(conditions) + " ORDER BY a.distribution_date DESC, a.distribution_id DESC",
            params,
        )

    def residents(self) -> List[tuple]:
        conditions, params = self._scope("curator_id")
        return self.db.fetch_all(
            "SELECT resident_id, full_name FROM Residents"
            + where_clause(conditions) + " ORDER BY full_name",
            params,
        )

    def distribute(self, data: Dict[str, object]) -> int:
        resident_id = parse_int(data.get("resident_id"), label="Резидент", required=True, minimum=1)
        item_id = parse_int(data.get("item_id"), label="Позиция", required=True, minimum=1)
        quantity = parse_decimal(data.get("quantity"), label="Количество")
        purpose = clean_text(data.get("purpose"), label="Цель выдачи")
        notes = clean_text(data.get("notes"), label="Примечания")

        with self.db.transaction() as cur:
            cur.execute("SELECT curator_id FROM Residents WHERE resident_id = %s", (resident_id,))
            resident = cur.fetchone()
            if resident is None:
                raise NotFound("Резидент не найден")
            if not self.user.is_admin and resident[0] != self.user.curator_id:
                raise PermissionDenied("Помощь можно выдавать только своим резидентам")

            # Проверка остатка и списание - одним атомарным запросом. Схема
            # "прочитать остаток, потом вычесть" даёт гонку: два оператора одновременно
            # выдают последние единицы, и остаток уходит в минус.
            cur.execute(
                "UPDATE Warehouse SET current_quantity = current_quantity - %s "
                "WHERE item_id = %s AND current_quantity >= %s RETURNING current_quantity",
                (quantity, item_id, quantity),
            )
            if cur.fetchone() is None:
                cur.execute("SELECT current_quantity FROM Warehouse WHERE item_id = %s", (item_id,))
                stock = cur.fetchone()
                if stock is None:
                    raise NotFound("Позиция не найдена")
                raise ServiceError(f"Недостаточно на складе. Доступно: {stock[0]}")

            cur.execute(
                "INSERT INTO AidDistribution (resident_id, item_id, quantity, issued_by, purpose, notes) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING distribution_id",
                (resident_id, item_id, quantity, self.user.id, purpose, notes),
            )
            return cur.fetchone()[0]
