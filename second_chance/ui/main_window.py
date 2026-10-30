from __future__ import annotations

from tkinter import ttk
from typing import Callable

from ..models import CurrentUser
from ..services import build_services
from .tabs.admin import AdminTab
from .tabs.aid import AidTab
from .tabs.events import EventsTab
from .tabs.ipr import IprTab
from .tabs.reports import ReportsTab
from .tabs.residents import ResidentsTab
from .tabs.rooms import RoomsTab
from .tabs.warehouse import WarehouseTab

COMMON_TABS = (ResidentsTab, RoomsTab, IprTab, EventsTab, WarehouseTab, AidTab, ReportsTab)


class MainWindow(ttk.Frame):
    def __init__(self, parent, db, user: CurrentUser, on_logout: Callable[[], None]) -> None:
        super().__init__(parent)
        services = build_services(db, user)

        header = ttk.Frame(self, padding=(10, 6))
        header.pack(fill="x")
        role = "Администратор" if user.is_admin else "Куратор"
        ttk.Label(header, text=f"{user.full_name}  |  {role}",
                  font=("TkDefaultFont", 10, "bold")).pack(side="left")
        ttk.Button(header, text="Выход", command=on_logout).pack(side="right")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        tab_classes = COMMON_TABS + ((AdminTab,) if user.is_admin else ())
        for tab_class in tab_classes:
            notebook.add(tab_class(notebook, services, user), text=tab_class.title)
