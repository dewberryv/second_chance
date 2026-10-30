from __future__ import annotations

from tkinter import ttk

from ..widgets import DataTable, Field, FormDialog, run_safely
from .base import BaseTab


class AidTab(BaseTab):
    title = "Выдача помощи"

    def build(self) -> None:
        bar = self.toolbar()
        ttk.Button(bar, text="Выдать помощь", command=self.distribute).pack(side="left", padx=2)
        ttk.Button(bar, text="Обновить", command=self.refresh).pack(side="left", padx=2)
        self.table = DataTable(self, [("ID", 50), ("Дата", 130), ("Резидент", 220), ("Позиция", 200),
                                      ("Количество", 100), ("Выдал", 180)])
        self.table.pack(fill="both", expand=True, padx=5, pady=5)

    def load(self) -> None:
        self.table.set_rows(self.services.aid.list())

    def distribute(self) -> None:
        def open_form():
            fields = [
                Field("resident_id", "Резидент", "choice", required=True, choices=self.services.aid.residents()),
                Field("item_id", "Позиция", "choice", required=True, choices=self.services.warehouse.items_in_stock()),
                Field("quantity", "Количество", required=True),
                Field("purpose", "Цель выдачи"),
                Field("notes", "Примечания", "text"),
            ]
            FormDialog(self, "Выдача помощи", fields,
                       on_submit=lambda values: (self.services.aid.distribute(values), self.refresh()))
        run_safely(self, open_form)
