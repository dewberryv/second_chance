"""Проверка и приведение данных из форм. Чистые функции, без обращений к БД."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable, Optional

from .errors import ValidationError

_DATE_FORMATS = ("%Y-%m-%d", "%d.%m.%Y")
_MAX_DECIMAL = Decimal("99999999.99")


def clean_text(value, *, label: str, required: bool = False,
               max_length: Optional[int] = None) -> Optional[str]:
    """Обрезает пробелы; пустую строку превращает в None."""
    text = "" if value is None else str(value).strip()
    if not text:
        if required:
            raise ValidationError(f"Поле «{label}» обязательно для заполнения")
        return None
    if max_length is not None and len(text) > max_length:
        raise ValidationError(f"Поле «{label}» длиннее {max_length} символов")
    return text


def parse_date(value, *, label: str, required: bool = False) -> Optional[date]:
    text = clean_text(value, label=label, required=required)
    if text is None:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValidationError(f"Поле «{label}»: дата в формате ГГГГ-ММ-ДД или ДД.ММ.ГГГГ")


def parse_int(value, *, label: str, required: bool = False,
              minimum: Optional[int] = None) -> Optional[int]:
    text = clean_text(value, label=label, required=required)
    if text is None:
        return None
    try:
        number = int(text)
    except ValueError:
        raise ValidationError(f"Поле «{label}» должно быть целым числом") from None
    if minimum is not None and number < minimum:
        raise ValidationError(f"Поле «{label}» не может быть меньше {minimum}")
    return number


def parse_decimal(value, *, label: str, required: bool = True, positive: bool = True,
                  max_decimals: int = 2) -> Optional[Decimal]:
    text = clean_text(value, label=label, required=required)
    if text is None:
        return None
    try:
        number = Decimal(text.replace(",", "."))
    except InvalidOperation:
        raise ValidationError(f"Поле «{label}» должно быть числом") from None
    if not number.is_finite():
        raise ValidationError(f"Поле «{label}» должно быть числом")
    if positive and number <= 0:
        raise ValidationError(f"Поле «{label}» должно быть больше нуля")
    if not positive and number < 0:
        raise ValidationError(f"Поле «{label}» не может быть отрицательным")
    if -number.as_tuple().exponent > max_decimals:
        raise ValidationError(f"Поле «{label}»: не более {max_decimals} знаков после запятой")
    if number > _MAX_DECIMAL:
        raise ValidationError(f"Поле «{label}» слишком большое")
    return number


def choice(value, allowed: Iterable[str], *, label: str, required: bool = True) -> Optional[str]:
    text = clean_text(value, label=label, required=required)
    if text is None:
        return None
    if text not in tuple(allowed):
        raise ValidationError(f"Поле «{label}»: недопустимое значение «{text}»")
    return text


def like_pattern(text: str) -> str:
    """Шаблон для ILIKE: служебные символы пользователя экранируются."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
