from __future__ import annotations

from tkinter import ttk

from ...models import CurrentUser
from ...services import Services
from ..widgets import run_safely


class BaseTab(ttk.Frame):
    """Вкладка главного окна: знает свои сервисы и умеет обновлять данные."""

    title = ""

    def __init__(self, parent, services: Services, user: CurrentUser) -> None:
        super().__init__(parent)
        self.services = services
        self.user = user
        self.build()
        self.refresh()

    def build(self) -> None:  # pragma: no cover - переопределяется
        raise NotImplementedError

    def load(self) -> None:  # pragma: no cover - переопределяется
        raise NotImplementedError

    def refresh(self) -> None:
        run_safely(self, self.load, title="Не удалось загрузить данные")

    def toolbar(self) -> ttk.Frame:
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=5, pady=5)
        return bar
