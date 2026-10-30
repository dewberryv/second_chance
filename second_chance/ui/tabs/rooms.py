from __future__ import annotations

from tkinter import ttk

from ..widgets import DataTable
from .base import BaseTab


class RoomsTab(BaseTab):
    title = "Комнаты"

    def build(self) -> None:
        ttk.Button(self.toolbar(), text="Обновить", command=self.refresh).pack(side="left")
        self.table = DataTable(self, [("Номер", 70), ("Вместимость", 100), ("Занято мест", 100),
                                      ("Статус", 110), ("Этаж", 60), ("Примечания", 300)])
        self.table.pack(fill="both", expand=True, padx=5, pady=5)

    def load(self) -> None:
        self.table.set_rows(self.services.rooms.list())
