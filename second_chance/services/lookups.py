"""Справочники для выпадающих списков: список пар (id, название)."""
from __future__ import annotations

from typing import List, Tuple

from .base import Service


class LookupService(Service):
    def active_curators(self) -> List[Tuple[int, str]]:
        return self.db.fetch_all(
            "SELECT curator_id, full_name FROM Curators WHERE status = 'Активен' ORDER BY full_name")

    def organizations(self) -> List[Tuple[int, str]]:
        return self.db.fetch_all(
            "SELECT org_id, name || ' (' || org_type || ')' FROM ExternalOrganizations ORDER BY name")
