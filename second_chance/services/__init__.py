"""Сервисный слой: вся бизнес-логика и SQL. Интерфейс обращается только сюда."""
from __future__ import annotations

from dataclasses import dataclass

from ..models import CurrentUser
from .aid import AidService
from .events import EventService
from .ipr import IprService
from .lookups import LookupService
from .reports import ReportService
from .residents import ResidentService
from .rooms import RoomService
from .warehouse import WarehouseService


@dataclass
class Services:
    residents: ResidentService
    rooms: RoomService
    ipr: IprService
    events: EventService
    warehouse: WarehouseService
    aid: AidService
    reports: ReportService
    lookups: LookupService


def build_services(db, user: CurrentUser) -> Services:
    return Services(
        residents=ResidentService(db, user), rooms=RoomService(db, user),
        ipr=IprService(db, user), events=EventService(db, user),
        warehouse=WarehouseService(db, user), aid=AidService(db, user),
        reports=ReportService(db, user), lookups=LookupService(db, user),
    )
