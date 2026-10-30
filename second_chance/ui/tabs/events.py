from __future__ import annotations

from datetime import date
from tkinter import messagebox, ttk

from ..widgets import DataTable, Field, FormDialog, run_safely
from .base import BaseTab


class EventsTab(BaseTab):
    title = "Мероприятия"

    def build(self) -> None:
        bar = self.toolbar()
        if not self.user.is_admin:
            ttk.Button(bar, text="Создать мероприятие", command=self.create).pack(side="left", padx=2)
            ttk.Button(bar, text="Изменить статус", command=self.change_status).pack(side="left", padx=2)
        ttk.Button(bar, text="Обновить", command=self.refresh).pack(side="left", padx=2)
        self.table = DataTable(self, [("ID", 50), ("ИПР", 50), ("Резидент", 200), ("Тип", 120),
                                      ("Название", 220), ("Дата", 90), ("Статус", 110), ("Результат", 200)])
        self.table.pack(fill="both", expand=True, padx=5, pady=5)

    def load(self) -> None:
        self.table.set_rows(self.services.events.list())

    def create(self) -> None:
        def open_form():
            iprs = self.services.events.active_iprs()
            if not iprs:
                messagebox.showinfo("Нет активных ИПР", "Сначала создайте активную ИПР", parent=self)
                return
            fields = [
                Field("ipr_id", "ИПР", "choice", required=True, choices=iprs),
                Field("event_type", "Тип", "choice", required=True, choices=self.services.events.types),
                Field("title", "Название", required=True),
                Field("description", "Описание", "text"),
                Field("planned_date", "Плановая дата", required=True, default=date.today().isoformat()),
                Field("event_status", "Статус", "choice", required=True, choices=self.services.events.new_statuses),
                Field("org_id", "Организация", "choice",
                      choices=[("", "-")] + list(self.services.lookups.organizations())),
            ]
            FormDialog(self, "Новое мероприятие", fields,
                       on_submit=lambda values: (self.services.events.create(values), self.refresh()))
        run_safely(self, open_form)

    def change_status(self) -> None:
        row = self.table.selected()
        if row is None:
            messagebox.showwarning("Внимание", "Выберите мероприятие", parent=self)
            return
        event_id = int(row[0])
        fields = [
            Field("status", "Новый статус", "choice", required=True, choices=self.services.events.update_statuses),
            Field("result", "Результат", "text"),
        ]
        FormDialog(self, f"Мероприятие №{event_id}", fields,
                   on_submit=lambda v: (self.services.events.change_status(event_id, v["status"], v["result"]),
                                        self.refresh()))
