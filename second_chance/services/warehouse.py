"""Склад гуманитарной помощи."""
from __future__ import annotations

from typing import Dict, List

from ..errors import NotFound
from ..validation import clean_text, parse_decimal, parse_int
from .base import Service


class WarehouseService(Service):
    def list(self) -> List[tuple]:
        return self.db.fetch_all(
            "SELECT item_id, name, category, current_quantity, unit, "
            "       COALESCE(unit_price::text, 'Нет'), COALESCE(storage_location, '') "
            "FROM Warehouse ORDER BY category, name")

    def items(self) -> List[tuple]:
        """Все позиции для выбора при пополнении: (id, название)."""
        return self.db.fetch_all("SELECT item_id, name FROM Warehouse ORDER BY name")

    def items_in_stock(self) -> List[tuple]:
        """Позиции с остатком для выдачи: (id, 'название (остаток ед.)')."""
        return self.db.fetch_all(
            "SELECT item_id, name || ' (остаток: ' || current_quantity || ' ' || unit || ')' "
            "FROM Warehouse WHERE current_quantity > 0 ORDER BY category, name")

    def restock(self, data: Dict[str, object]) -> None:
        self._require_admin()
        item_id = parse_int(data.get("item_id"), label="Позиция", required=True, minimum=1)
        quantity = parse_decimal(data.get("quantity"), label="Количество")
        price = parse_decimal(data.get("unit_price"), label="Цена", required=False, positive=False)
        supplier = clean_text(data.get("supplier"), label="Поставщик", max_length=200)
        # Один UPDATE вместо трёх: COALESCE оставляет прежнюю цену/поставщика, если поле пустое.
        updated = self.db.execute(
            "UPDATE Warehouse SET current_quantity = current_quantity + %s, "
            "last_delivery_date = CURRENT_DATE, "
            "unit_price = COALESCE(%s, unit_price), supplier = COALESCE(%s, supplier) "
            "WHERE item_id = %s",
            (quantity, price, supplier, item_id),
        )
        if updated == 0:
            raise NotFound("Позиция не найдена")
