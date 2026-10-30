from datetime import date
from decimal import Decimal

import pytest

from second_chance.errors import ValidationError
from second_chance.validation import (choice, clean_text, like_pattern, parse_date,
                                      parse_decimal, parse_int)


class TestText:
    def test_strips_and_empty_becomes_none(self):
        assert clean_text("  Иван ", label="ФИО") == "Иван"
        assert clean_text("   ", label="ФИО") is None
        assert clean_text(None, label="ФИО") is None

    def test_required(self):
        with pytest.raises(ValidationError, match="ФИО"):
            clean_text("", label="ФИО", required=True)

    def test_max_length(self):
        with pytest.raises(ValidationError):
            clean_text("a" * 11, label="X", max_length=10)


class TestDate:
    def test_formats(self):
        assert parse_date("2025-03-09", label="Д") == date(2025, 3, 9)
        assert parse_date("09.03.2025", label="Д") == date(2025, 3, 9)

    def test_empty_optional(self):
        assert parse_date("", label="Д") is None

    @pytest.mark.parametrize("bad", ["2025-13-01", "31.02.2025", "вчера", "2025/03/09"])
    def test_bad_dates(self, bad):
        with pytest.raises(ValidationError):
            parse_date(bad, label="Д")


class TestNumbers:
    def test_int(self):
        assert parse_int("12", label="Н") == 12
        assert parse_int("", label="Н") is None

    def test_int_errors(self):
        with pytest.raises(ValidationError):
            parse_int("1.5", label="Н")
        with pytest.raises(ValidationError):
            parse_int("0", label="Н", minimum=1)

    def test_decimal_accepts_comma(self):
        assert parse_decimal("3,5", label="К") == Decimal("3.5")

    @pytest.mark.parametrize("bad", ["0", "-1", "abc", "NaN", "Infinity", "1.234", "1e9"])
    def test_decimal_rejects(self, bad):
        with pytest.raises(ValidationError):
            parse_decimal(bad, label="К")

    def test_decimal_non_negative_allows_zero(self):
        assert parse_decimal("0", label="Цена", required=False, positive=False) == Decimal("0")


def test_choice():
    assert choice("Выбыл", ("Выбыл", "Другое"), label="С") == "Выбыл"
    with pytest.raises(ValidationError):
        choice("Неизвестно", ("Выбыл",), label="С")


def test_like_pattern_escapes_wildcards():
    assert like_pattern("50%_") == "%50\\%\\_%"
    assert like_pattern("a\\b") == "%a\\\\b%"
