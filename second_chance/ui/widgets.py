"""Переиспользуемые элементы: таблица, универсальная форма, безопасный запуск действий."""
from __future__ import annotations

import logging
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import messagebox, ttk
from typing import Callable, Dict, Optional, Sequence, Tuple, Union

from ..errors import ServiceError

log = logging.getLogger(__name__)

Choice = Union[str, Tuple[object, str]]  # "значение" или (значение, подпись)


def run_safely(parent, action: Callable[[], object], *, title: str = "Ошибка") -> bool:
    """Выполняет действие. Ожидаемые ошибки показывает как предупреждение,
    непредвиденные пишет в лог. True, если действие прошло без ошибок."""
    try:
        action()
        return True
    except ServiceError as exc:
        messagebox.showwarning(title, str(exc), parent=parent)
    except Exception:  # noqa: BLE001 - последний рубеж интерфейса, ошибка уходит в лог
        log.exception("Непредвиденная ошибка")
        messagebox.showerror(
            title, "Произошла непредвиденная ошибка. Подробности записаны в second_chance.log.",
            parent=parent)
    return False


class DataTable(ttk.Frame):
    """Treeview с прокруткой. Колонки: [(заголовок, ширина), ...]."""

    def __init__(self, parent, columns: Sequence[Tuple[str, int]]) -> None:
        super().__init__(parent)
        names = [name for name, _ in columns]
        self.tree = ttk.Treeview(self, columns=names, show="headings", height=18)
        for name, width in columns:
            self.tree.heading(name, text=name)
            self.tree.column(name, width=width, anchor="w")
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def set_rows(self, rows: Sequence[Sequence]) -> None:
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", "end", values=["" if cell is None else cell for cell in row])

    def selected(self) -> Optional[tuple]:
        selection = self.tree.selection()
        if not selection:
            return None
        return tuple(self.tree.item(selection[0])["values"])


@dataclass
class Field:
    """Описание поля формы.

    kind: "entry" - строка; "text" - многострочный текст;
          "choice" - только выбор из списка; "choice_free" - список с возможностью ввода своего.
    choices: строки или пары (значение, подпись); для пар форма вернёт значение.
    """
    name: str
    label: str
    kind: str = "entry"
    required: bool = False
    default: str = ""
    choices: Sequence[Choice] = field(default_factory=tuple)


class FormDialog(tk.Toplevel):
    """Модальная форма по списку полей.

    on_submit(values: dict) вызывается при нажатии «Сохранить». Если он бросает
    ServiceError, форма остаётся открытой и показывает сообщение; иначе закрывается.
    """

    def __init__(self, parent, title: str, fields: Sequence[Field],
                 on_submit: Callable[[Dict[str, str]], object],
                 initial: Optional[Dict[str, str]] = None, submit_text: str = "Сохранить") -> None:
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self._fields = list(fields)
        self._on_submit = on_submit
        self._widgets: Dict[str, tk.Widget] = {}
        self._labels_to_values: Dict[str, Dict[str, object]] = {}
        initial = initial or {}

        body = ttk.Frame(self, padding=15)
        body.pack(fill="both", expand=True)
        for row, spec in enumerate(self._fields):
            mark = " *" if spec.required else ""
            ttk.Label(body, text=f"{spec.label}{mark}:").grid(row=row, column=0, sticky="nw", pady=4, padx=(0, 10))
            widget = self._make_widget(body, spec, initial.get(spec.name, spec.default))
            widget.grid(row=row, column=1, sticky="w", pady=4)
            self._widgets[spec.name] = widget

        buttons = ttk.Frame(body)
        buttons.grid(row=len(self._fields), column=0, columnspan=2, pady=(15, 0))
        ttk.Button(buttons, text=submit_text, command=self._submit).pack(side="left", padx=5)
        ttk.Button(buttons, text="Отмена", command=self.destroy).pack(side="left", padx=5)
        self.bind("<Escape>", lambda _event: self.destroy())

        if self._fields:
            self._widgets[self._fields[0].name].focus_set()
        try:
            self.wait_visibility()
            self.grab_set()  # модальность; на некоторых платформах окно должно сначала появиться
        except tk.TclError:
            pass

    def _make_widget(self, parent, spec: Field, value) -> tk.Widget:
        if spec.kind == "text":
            widget = tk.Text(parent, width=42, height=4, wrap="word")
            widget.insert("1.0", value or "")
            return widget
        if spec.kind in ("choice", "choice_free"):
            mapping: Dict[str, object] = {}
            labels = []
            for item in spec.choices:
                key, label = (item if isinstance(item, tuple) else (item, item))
                mapping[str(label)] = key
                labels.append(str(label))
            self._labels_to_values[spec.name] = mapping
            state = "readonly" if spec.kind == "choice" else "normal"
            widget = ttk.Combobox(parent, values=labels, width=40, state=state)
            shown = next((str(label) for label, key in mapping.items() if str(key) == str(value)), value or "")
            if not shown and labels and spec.required and spec.kind == "choice":
                shown = labels[0]
            widget.set(shown)
            return widget
        widget = ttk.Entry(parent, width=43)
        widget.insert(0, value or "")
        return widget

    def _collect(self) -> Dict[str, str]:
        values: Dict[str, str] = {}
        for spec in self._fields:
            widget = self._widgets[spec.name]
            raw = widget.get("1.0", "end").strip() if spec.kind == "text" else widget.get().strip()
            if spec.name in self._labels_to_values:
                raw = self._labels_to_values[spec.name].get(raw, raw)
            values[spec.name] = "" if raw is None else str(raw)
        return values

    def _submit(self) -> None:
        values = self._collect()
        for spec in self._fields:
            if spec.required and not values[spec.name]:
                messagebox.showwarning("Проверьте данные",
                                       f"Поле «{spec.label}» обязательно для заполнения", parent=self)
                return
        if run_safely(self, lambda: self._on_submit(values), title="Не удалось сохранить"):
            self.destroy()
