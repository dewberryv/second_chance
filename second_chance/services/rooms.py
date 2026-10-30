from __future__ import annotations

from typing import List

from ..constants import STATUS_LEFT
from .base import Service


class RoomService(Service):
    def list(self) -> List[tuple]:
        """Комнаты с реальной заполненностью (считается по резидентам, а не хранится)."""
        return self.db.fetch_all(
            "SELECT rm.room_number, rm.capacity, "
            "       COUNT(r.resident_id) FILTER (WHERE r.status <> %s) AS occupied, "
            "       rm.room_status, COALESCE(rm.floor::text, ''), COALESCE(rm.notes, '') "
            "FROM Rooms rm LEFT JOIN Residents r ON r.room_number = rm.room_number "
            "GROUP BY rm.room_number ORDER BY rm.room_number",
            (STATUS_LEFT,),
        )
