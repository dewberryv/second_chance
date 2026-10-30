from __future__ import annotations

from tkinter import ttk

from ..services.auth import authenticate
from .widgets import run_safely


class LoginFrame(ttk.Frame):
    def __init__(self, parent, db, on_success) -> None:
        super().__init__(parent, padding=40)
        self._db = db
        self._on_success = on_success

        ttk.Label(self, text="Second Chance", font=("TkDefaultFont", 22, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 5))
        ttk.Label(self, text="Система управления центром социальной адаптации").grid(
            row=1, column=0, columnspan=2, pady=(0, 25))

        ttk.Label(self, text="Логин:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.username = ttk.Entry(self, width=28)
        self.username.grid(row=2, column=1, pady=5)
        ttk.Label(self, text="Пароль:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.password = ttk.Entry(self, width=28, show="•")
        self.password.grid(row=3, column=1, pady=5)

        ttk.Button(self, text="Войти", command=self.login).grid(row=4, column=0, columnspan=2, pady=20)
        self.username.focus_set()
        for widget in (self.username, self.password):
            widget.bind("<Return>", lambda _event: self.login())

    def login(self) -> None:
        def action():
            if not self._db.is_connected:
                self._db.connect()
            user = authenticate(self._db, self.username.get(), self.password.get())
            self._on_success(user)

        if not run_safely(self, action, title="Вход не выполнен"):
            self.password.delete(0, "end")
            self.password.focus_set()
