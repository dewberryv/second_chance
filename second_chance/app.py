"""Точка входа GUI: одно окно Tk, внутри которого меняются экраны входа и работы."""
from __future__ import annotations

import logging
import tkinter as tk

from .config import PROJECT_ROOT, load_db_config
from .db import Database
from .models import CurrentUser
from .ui.login import LoginFrame
from .ui.main_window import MainWindow


class App:
    def __init__(self, root: tk.Tk, db: Database) -> None:
        self.root = root
        self.db = db
        self._screen = None

    def _show(self, screen) -> None:
        if self._screen is not None:
            self._screen.destroy()
        self._screen = screen
        screen.pack(fill="both", expand=True)

    def show_login(self) -> None:
        self.root.title("Second Chance - вход")
        self._show(LoginFrame(self.root, self.db, self.show_main))

    def show_main(self, user: CurrentUser) -> None:
        self.root.title(f"Second Chance - {user.full_name}")
        self._show(MainWindow(self.root, self.db, user, on_logout=self.show_login))


def run() -> None:
    logging.basicConfig(
        filename=PROJECT_ROOT / "second_chance.log", level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s", encoding="utf-8")
    db = Database(load_db_config())
    root = tk.Tk()
    root.geometry("1200x700")
    root.minsize(900, 500)
    App(root, db).show_login()
    try:
        root.mainloop()
    finally:
        db.close()
