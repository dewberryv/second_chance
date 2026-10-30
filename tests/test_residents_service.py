import pytest

from fakes import ADMIN, CURATOR, FakeDatabase
from second_chance.errors import (IntegrityConflict, NotFound, PermissionDenied,
                                  ServiceError, ValidationError)
from second_chance.services.residents import ResidentService

VALID = {"full_name": "Иванов Иван", "admission_date": "2025-01-10", "status": "Основной поток",
         "room_number": "101", "curator_id": "5"}


class TestList:
    def test_curator_sees_only_own_residents(self):
        db = FakeDatabase()
        ResidentService(db, CURATOR).list()
        sql, params = db.calls[0]
        assert "r.curator_id = %s" in sql
        assert params == (5,)

    def test_admin_sees_everyone(self):
        db = FakeDatabase()
        ResidentService(db, ADMIN).list()
        sql, params = db.calls[0]
        assert "WHERE" not in sql
        assert params == ()

    def test_every_search_word_must_match(self):
        db = FakeDatabase()
        ResidentService(db, ADMIN).list("иван  петров")
        sql, params = db.calls[0]
        assert sql.count("ILIKE") == 2
        assert params == ("%иван%", "%петров%")

    def test_wildcards_in_search_are_escaped(self):
        db = FakeDatabase()
        ResidentService(db, ADMIN).list("50%")
        assert db.calls[0][1] == ("%50\\%%",)


class TestCreate:
    def test_only_admin_can_create(self):
        db = FakeDatabase()
        with pytest.raises(PermissionDenied):
            ResidentService(db, CURATOR).create(VALID)
        assert db.calls == []

    def test_validation_happens_before_database(self):
        db = FakeDatabase()
        with pytest.raises(ValidationError):
            ResidentService(db, ADMIN).create({**VALID, "full_name": " "})
        assert db.calls == []

    def test_full_room_is_rejected_and_nothing_inserted(self):
        db = FakeDatabase(results=[(2, "Занято"), (2,)])  # вместимость 2, занято 2
        with pytest.raises(ServiceError, match="заполнена"):
            ResidentService(db, ADMIN).create(VALID)
        assert not any("INSERT" in sql for sql in db.sql_log())
        assert db.rolled_back == 1

    def test_room_under_repair_is_rejected(self):
        db = FakeDatabase(results=[(3, "На ремонте")])
        with pytest.raises(ServiceError, match="ремонте"):
            ResidentService(db, ADMIN).create(VALID)

    def test_unknown_room_is_rejected(self):
        db = FakeDatabase(results=[None])
        with pytest.raises(ServiceError, match="не существует"):
            ResidentService(db, ADMIN).create(VALID)

    def test_success_returns_new_id_and_records_author(self):
        db = FakeDatabase(results=[(3, "Свободно"), (1,), (42,)])
        assert ResidentService(db, ADMIN).create(VALID) == 42
        insert_sql, insert_params = db.calls[-1]
        assert insert_sql.startswith("INSERT INTO Residents")
        assert insert_params[-1] == ADMIN.id
        assert db.committed == 1

    def test_departed_resident_skips_room_check(self):
        db = FakeDatabase(results=[(7,)])
        ResidentService(db, ADMIN).create({**VALID, "status": "Выбыл"})
        assert db.calls[0][0].startswith("INSERT INTO Residents")


class TestUpdateAndDelete:
    def test_update_excludes_the_resident_from_room_count(self):
        db = FakeDatabase(results=[(2, "Занято"), (1,)])
        ResidentService(db, ADMIN).update(7, VALID)
        count_sql, count_params = db.calls[1]
        assert "IS DISTINCT FROM" in count_sql
        assert count_params[-1] == 7

    def test_update_missing_resident(self):
        db = FakeDatabase(results=[(2, "Занято"), (0,)], rowcounts=[1, 1, 0])
        with pytest.raises(NotFound):
            ResidentService(db, ADMIN).update(999, VALID)

    def test_delete_with_history_gives_helpful_message(self):
        db = FakeDatabase(error=IntegrityConflict("fk"))
        with pytest.raises(IntegrityConflict, match="Выбыл"):
            ResidentService(db, ADMIN).delete(1)

    def test_delete_missing(self):
        db = FakeDatabase(rowcounts=[0])
        with pytest.raises(NotFound):
            ResidentService(db, ADMIN).delete(1)

    def test_curator_cannot_delete(self):
        with pytest.raises(PermissionDenied):
            ResidentService(FakeDatabase(), CURATOR).delete(1)


def test_get_returns_strings_for_the_form():
    row = ("Иванов", None, "Паспорт РФ", None, None, "2025-01-10", "Основной поток", 101, 5)
    result = ResidentService(FakeDatabase(results=[row]), ADMIN).get(1)
    assert result["birth_date"] == "" and result["room_number"] == "101"


def test_get_hidden_from_other_curator():
    with pytest.raises(NotFound):
        ResidentService(FakeDatabase(results=[None]), CURATOR).get(1)
