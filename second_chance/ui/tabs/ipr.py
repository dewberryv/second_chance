from __future__ import annotations

from datetime import date
from tkinter import messagebox, ttk

from ..widgets import DataTable, Field, FormDialog, run_safely
from .base import BaseTab


class IprTab(BaseTab):
    title = "ИПР"

    def build(self) -> None:
        bar = self.toolbar()
        if not self.user.is_admin:
            ttk.Button(bar, text="Создать ИПР", command=self.create).pack(side="left", padx=2)
            ttk.Button(bar, text="Удалить", command=self.delete).pack(side="left", padx=2)
        ttk.Button(bar, text="Обновить", command=self.refresh).pack(side="left", padx=2)
        self.table = DataTable(self, [("ID", 50), ("Резидент", 220), ("Создана", 100),
                                      ("Статус", 120), ("Основная цель", 320), ("Куратор", 180)])
        self.table.pack(fill="both", expand=True, padx=5, pady=5)

    def load(self) -> None:
        self.table.set_rows(self.services.ipr.list())

    def create(self) -> None:
        def open_form():
            residents = self.services.ipr.residents_without_ipr()
            if not residents:
                messagebox.showinfo("Нет резидентов", "У всех ваших резидентов уже есть ИПР", parent=self)
                return
            fields = [
                Field("resident_id", "Резидент", "choice", required=True, choices=residents),
                Field("start_date", "Дата начала", required=True, default=date.today().isoformat()),
                Field("end_date", "Дата окончания"),
                Field("ipr_status", "Статус", "choice", required=True, choices=self.services.ipr.statuses),
                Field("main_goal", "Основная цель", "text", required=True),
                Field("specific_goals", "Конкретные задачи", "text"),
                Field("success_criteria", "Критерии успеха", "text"),
                Field("notes", "Примечания", "text"),
            ]
            FormDialog(self, "Новая ИПР", fields,
                       on_submit=lambda values: (self.services.ipr.create(values), self.refresh()))
        run_safely(self, open_form)

    def delete(self) -> None:
        row = self.table.selected()
        if row is None:
            messagebox.showwarning("Внимание", "Выберите ИПР", parent=self)
            return
        if messagebox.askyesno("Подтверждение",
                               f"Удалить ИПР резидента {row[1]}?\nВсе её мероприятия тоже будут удалены.",
                               parent=self):
            if run_safely(self, lambda: self.services.ipr.delete(int(row[0]))):
                self.refresh()
