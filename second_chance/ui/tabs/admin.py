from __future__ import annotations

from tkinter import ttk

from ..widgets import DataTable
from .base import BaseTab


class AdminTab(BaseTab):
    title = "Статистика"

    def build(self) -> None:
        ttk.Button(self.toolbar(), text="Обновить", command=self.refresh).pack(side="left")
        self.table = DataTable(self, [("Показатель", 320), ("Значение", 120)])
        self.table.pack(fill="x", padx=5, pady=5)

    def load(self) -> None:
        self.table.set_rows(self.services.reports.statistics())
