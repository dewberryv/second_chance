from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from ...services.reports import Report, export_csv
from ..widgets import DataTable, run_safely
from .base import BaseTab


class ReportWindow(tk.Toplevel):
    def __init__(self, parent, report: Report) -> None:
        super().__init__(parent)
        self.title(f"Отчёт: {report.title}")
        self.geometry("950x520")
        self._report = report
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=8)
        ttk.Label(bar, text=f"{report.title} - записей: {len(report.rows)}",
                  font=("TkDefaultFont", 11, "bold")).pack(side="left")
        ttk.Button(bar, text="Сохранить в CSV", command=self.save_csv).pack(side="right")
        table = DataTable(self, [(header, 140) for header in report.headers])
        table.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        table.set_rows(report.rows)

    def save_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".csv", filetypes=[("CSV", "*.csv"), ("Все файлы", "*.*")],
            initialfile=f"report_{datetime.now():%Y%m%d_%H%M%S}.csv")
        if not path:
            return

        def write():
            export_csv(path, self._report.headers, self._report.rows)
            messagebox.showinfo("Готово", f"Отчёт сохранён:\n{path}", parent=self)
        run_safely(self, write, title="Не удалось сохранить файл")


class ReportsTab(BaseTab):
    title = "Отчёты"

    def build(self) -> None:
        reports = self.services.reports
        buttons = ttk.Frame(self)
        buttons.pack(pady=30)
        for text, builder in (("Текущий состав резидентов", reports.current_residents),
                              ("Выполнение ИПР", reports.ipr_progress),
                              ("Выдача материальной помощи", reports.aid_issued)):
            ttk.Button(buttons, text=text, width=34,
                       command=lambda b=builder: self.show(b)).pack(pady=8, ipady=6)

    def load(self) -> None:
        pass  # отчёты строятся по нажатию

    def show(self, builder) -> None:
        def open_report():
            ReportWindow(self, builder())
        run_safely(self, open_report, title="Не удалось построить отчёт")
