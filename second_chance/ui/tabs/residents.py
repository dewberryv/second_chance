from __future__ import annotations

from datetime import date
from tkinter import messagebox, ttk

from ..widgets import DataTable, Field, FormDialog, run_safely
from .base import BaseTab

SEARCH_DELAY_MS = 300


class ResidentsTab(BaseTab):
    title = "Резиденты"

    def build(self) -> None:
        bar = self.toolbar()
        if self.user.is_admin:
            ttk.Button(bar, text="Добавить", command=self.add).pack(side="left", padx=2)
            ttk.Button(bar, text="Изменить", command=self.edit).pack(side="left", padx=2)
            ttk.Button(bar, text="Удалить", command=self.delete).pack(side="left", padx=2)
        ttk.Button(bar, text="Обновить", command=self.refresh).pack(side="left", padx=2)

        ttk.Label(bar, text="Поиск по ФИО:").pack(side="left", padx=(20, 5))
        self.search_var = ttk.Entry(bar, width=30)
        self.search_var.pack(side="left")
        self.search_var.bind("<KeyRelease>", self._on_key)
        ttk.Button(bar, text="Сброс", command=self.clear_search).pack(side="left", padx=5)
        self._search_job = None

        self.table = DataTable(self, [
            ("ID", 50), ("ФИО", 220), ("Документ", 110), ("Тип документа", 130), ("Телефон", 110),
            ("Дата поступления", 110), ("Статус", 110), ("Комната", 70), ("Куратор", 180)])
        self.table.pack(fill="both", expand=True, padx=5, pady=5)

    def load(self) -> None:
        self.table.set_rows(self.services.residents.list(self.search_var.get()))

    def _on_key(self, _event) -> None:
        # задержка, чтобы не отправлять запрос на каждый символ
        if self._search_job is not None:
            self.after_cancel(self._search_job)
        self._search_job = self.after(SEARCH_DELAY_MS, self.refresh)

    def clear_search(self) -> None:
        self.search_var.delete(0, "end")
        self.refresh()

    def _fields(self):
        residents = self.services.residents
        curators = self.services.lookups.active_curators()
        return [
            Field("full_name", "ФИО", required=True),
            Field("birth_date", "Дата рождения (ГГГГ-ММ-ДД)"),
            Field("document_type", "Тип документа", "choice_free", choices=residents.document_types),
            Field("document_number", "Номер документа"),
            Field("phone", "Телефон"),
            Field("admission_date", "Дата поступления", required=True, default=date.today().isoformat()),
            Field("status", "Статус", "choice", required=True, choices=residents.statuses),
            Field("room_number", "Комната"),
            Field("curator_id", "Куратор", "choice", choices=[("", "-")] + list(curators)),
        ]

    def add(self) -> None:
        def open_form():
            FormDialog(self, "Добавить резидента", self._fields(),
                       on_submit=lambda values: (self.services.residents.create(values), self.refresh()))
        run_safely(self, open_form)

    def edit(self) -> None:
        row = self.table.selected()
        if row is None:
            messagebox.showwarning("Внимание", "Выберите резидента", parent=self)
            return
        resident_id = int(row[0])

        def open_form():
            initial = self.services.residents.get(resident_id)
            FormDialog(self, f"Резидент №{resident_id}", self._fields(),
                       on_submit=lambda values: (self.services.residents.update(resident_id, values),
                                                 self.refresh()),
                       initial=initial)
        run_safely(self, open_form)

    def delete(self) -> None:
        row = self.table.selected()
        if row is None:
            messagebox.showwarning("Внимание", "Выберите резидента", parent=self)
            return
        if messagebox.askyesno("Подтверждение", f"Удалить резидента:\n{row[1]}?", parent=self):
            if run_safely(self, lambda: self.services.residents.delete(int(row[0]))):
                self.refresh()
