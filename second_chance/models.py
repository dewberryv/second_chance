from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .constants import ROLE_ADMIN


@dataclass(frozen=True)
class CurrentUser:
    id: int
    username: str
    full_name: str
    role: str
    curator_id: Optional[int] = None

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN
