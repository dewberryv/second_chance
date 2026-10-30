from __future__ import annotations

from tkinter import ttk

from ..widgets import DataTable, Field, FormDialog, run_safely
from .base import BaseTab


class WarehouseTab(BaseTab):
    title = "Склад"

    def build(self) -> None:
        bar = self.toolbar()
        if self.user.is_admin:
            ttk.Button(bar, text="Пополнить склад", command=self.restock).pack(side="left", padx=2)
        ttk.Button(bar, text="Обновить", command=self.refresh).pack(side="left", padx=2)
        self.table = DataTable(self, [("ID", 50), ("Наименование", 220), ("Категория", 140), ("Остаток", 90),
                                      ("Ед.", 60), ("Цена", 80), ("Место", 200)])
        self.table.pack(fill="both", expand=True, padx=5, pady=5)

    def load(self) -> None:
        self.table.set_rows(self.services.warehouse.list())

    def restock(self) -> None:
        def open_form():
            fields = [
                Field("item_id", "Позиция", "choice", required=True, choices=self.services.warehouse.items()),
                Field("quantity", "Количество", required=True),
                Field("unit_price", "Новая цена (необязательно)"),
                Field("supplier", "Поставщик (необязательно)"),
            ]
            FormDialog(self, "Пополнение склада", fields,
                       on_submit=lambda values: (self.services.warehouse.restock(values), self.refresh()))
        run_safely(self, open_form)
