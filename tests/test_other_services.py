from decimal import Decimal

import pytest

from fakes import ADMIN, CURATOR, CURATOR_WITHOUT_PROFILE, FakeDatabase
from second_chance.errors import AuthError, NotFound, PermissionDenied, ServiceError, ValidationError
from second_chance.security import hash_password
from second_chance.services import auth
from second_chance.services.aid import AidService
from second_chance.services.events import EventService
from second_chance.services.ipr import IprService
from second_chance.services.reports import ReportService, export_csv
from second_chance.services.warehouse import WarehouseService


class TestAuth:
    def _row(self, password="Пароль-123"):
        return (1, "admin", "Админ", "admin", None, hash_password(password))

    def test_success(self):
        user = auth.authenticate(FakeDatabase(results=[self._row()]), " admin ", "Пароль-123")
        assert (user.id, user.role, user.is_admin) == (1, "admin", True)

    def test_wrong_password(self):
        with pytest.raises(AuthError):
            auth.authenticate(FakeDatabase(results=[self._row()]), "admin", "неверный")

    def test_unknown_user_gives_same_error(self):
        with pytest.raises(AuthError, match="Неверный логин или пароль"):
            auth.authenticate(FakeDatabase(results=[None]), "ghost", "что-угодно")

    def test_empty_password_rejected(self):
        with pytest.raises(AuthError):
            auth.authenticate(FakeDatabase(results=[self._row()]), "admin", "")

    def test_short_password_not_allowed_for_new_user(self):
        with pytest.raises(ValidationError):
            auth.create_user(FakeDatabase(), username="u", password="123", full_name="Тест", role="admin")

    def test_new_user_stores_hash_not_password(self):
        db = FakeDatabase(results=[(9,)])
        auth.create_user(db, username="u", password="Пароль-123", full_name="Тест", role="admin")
        params = db.calls[0][1]
        assert "Пароль-123" not in params
        assert any(isinstance(p, str) and p.startswith("scrypt$") for p in params)


class TestAid:
    DATA = {"resident_id": "3", "item_id": "8", "quantity": "2", "purpose": "Одежда"}

    def test_success_order_of_queries(self):
        db = FakeDatabase(results=[(5,), (Decimal("8"),), (11,)])
        assert AidService(db, CURATOR).distribute(self.DATA) == 11
        assert [s.split()[0] for s in db.sql_log()] == ["SELECT", "UPDATE", "INSERT"]
        assert db.committed == 1

    def test_stock_is_checked_atomically_in_the_update(self):
        db = FakeDatabase(results=[(5,), (Decimal("8"),), (11,)])
        AidService(db, CURATOR).distribute(self.DATA)
        assert "current_quantity >= %s" in db.calls[1][0]

    def test_not_enough_stock(self):
        db = FakeDatabase(results=[(5,), None, (Decimal("1.5"),)])
        with pytest.raises(ServiceError, match="Доступно: 1.5"):
            AidService(db, CURATOR).distribute(self.DATA)
        assert not any(s.startswith("INSERT") for s in db.sql_log())
        assert db.rolled_back == 1

    def test_curator_cannot_help_foreign_resident(self):
        db = FakeDatabase(results=[(77,)])
        with pytest.raises(PermissionDenied):
            AidService(db, CURATOR).distribute(self.DATA)
        assert len(db.calls) == 1

    def test_admin_can_help_any_resident(self):
        db = FakeDatabase(results=[(77,), (Decimal("8"),), (11,)])
        assert AidService(db, ADMIN).distribute(self.DATA) == 11

    def test_unknown_resident(self):
        with pytest.raises(NotFound):
            AidService(FakeDatabase(results=[None]), ADMIN).distribute(self.DATA)

    @pytest.mark.parametrize("quantity", ["0", "-2", "abc", ""])
    def test_bad_quantity_never_reaches_database(self, quantity):
        db = FakeDatabase()
        with pytest.raises(ValidationError):
            AidService(db, ADMIN).distribute({**self.DATA, "quantity": quantity})
        assert db.calls == []


class TestWarehouse:
    def test_only_admin_restocks(self):
        with pytest.raises(PermissionDenied):
            WarehouseService(FakeDatabase(), CURATOR).restock({"item_id": "1", "quantity": "5"})

    def test_empty_price_and_supplier_become_null(self):
        db = FakeDatabase()
        WarehouseService(db, ADMIN).restock({"item_id": "1", "quantity": "5", "unit_price": "", "supplier": ""})
        assert db.calls[0][1] == (Decimal("5"), None, None, 1)

    def test_missing_item(self):
        with pytest.raises(NotFound):
            WarehouseService(FakeDatabase(rowcounts=[0]), ADMIN).restock({"item_id": "1", "quantity": "5"})


class TestIprAndEvents:
    IPR = {"resident_id": "3", "start_date": "2025-01-01", "ipr_status": "Активна", "main_goal": "Цель"}
    EVENT = {"ipr_id": "1", "event_type": "Социальное", "title": "Встреча",
             "planned_date": "2025-02-01", "event_status": "Запланировано"}

    def test_admin_cannot_create_ipr(self):
        with pytest.raises(PermissionDenied):
            IprService(FakeDatabase(), ADMIN).create(self.IPR)

    def test_curator_without_profile_cannot_create_ipr(self):
        with pytest.raises(PermissionDenied):
            IprService(FakeDatabase(), CURATOR_WITHOUT_PROFILE).create(self.IPR)

    def test_ipr_only_for_own_residents(self):
        with pytest.raises(PermissionDenied):
            IprService(FakeDatabase(results=[(99,)]), CURATOR).create(self.IPR)

    def test_ipr_uses_curators_own_id(self):
        db = FakeDatabase(results=[(5,), (10,)])
        assert IprService(db, CURATOR).create(self.IPR) == 10
        assert db.calls[1][1][1] == 5

    def test_ipr_end_before_start_rejected(self):
        with pytest.raises(ValidationError):
            IprService(FakeDatabase(), CURATOR).create({**self.IPR, "end_date": "2024-12-31"})

    def test_ipr_delete_scoped_to_curator(self):
        db = FakeDatabase()
        IprService(db, CURATOR).delete(4)
        assert db.calls[0][1] == (4, 5)

    def test_event_only_in_own_ipr(self):
        with pytest.raises(PermissionDenied):
            EventService(FakeDatabase(results=[None]), CURATOR).create(self.EVENT)

    def test_event_responsible_is_current_curator(self):
        db = FakeDatabase(results=[(1,), (7,)])
        assert EventService(db, CURATOR).create(self.EVENT) == 7
        assert db.calls[1][1][-1] == 5

    def test_event_status_must_be_known(self):
        with pytest.raises(ValidationError):
            EventService(FakeDatabase(), CURATOR).change_status(1, "Придумано", "")

    def test_event_status_not_found(self):
        with pytest.raises(NotFound):
            EventService(FakeDatabase(rowcounts=[0]), CURATOR).change_status(1, "Выполнено", "ок")


class TestReports:
    def test_statistics_only_for_admin(self):
        with pytest.raises(PermissionDenied):
            ReportService(FakeDatabase(), CURATOR).statistics()

    def test_statistics_pairs_labels_with_values(self):
        stats = ReportService(FakeDatabase(results=[tuple(range(10))]), ADMIN).statistics()
        assert stats[0] == ("Всего резидентов", 0) and len(stats) == 10

    def test_curator_reports_are_scoped(self):
        db = FakeDatabase()
        service = ReportService(db, CURATOR)
        service.current_residents()
        service.ipr_progress()
        service.aid_issued()
        assert all("= %s" in sql and 5 in params for sql, params in db.calls)

    def test_csv_export(self, tmp_path):
        path = tmp_path / "report.csv"
        export_csv(path, ("ФИО", "Заметка"), [("Иванов", "=HYPERLINK(\"evil\")"), ("Петров", "ок;точка")])
        raw = path.read_bytes()
        assert raw.startswith(b"\xef\xbb\xbf")  # BOM для Excel
        text = raw.decode("utf-8-sig")
        assert text.splitlines()[0] == "ФИО;Заметка"
        assert "'=HYPERLINK" in text            # формула обезврежена
        assert '"ок;точка"' in text             # разделитель внутри значения экранирован
