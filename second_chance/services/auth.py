"""Вход в систему и создание пользователей."""
from __future__ import annotations

from functools import lru_cache

from ..constants import ROLE_ADMIN, ROLE_CURATOR
from ..errors import AuthError, ValidationError
from ..models import CurrentUser
from ..security import hash_password, verify_password
from ..validation import clean_text

MIN_PASSWORD_LENGTH = 8


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    # Проверяем пароль и для несуществующего логина, чтобы время ответа
    # не выдавало, есть ли такой пользователь.
    return hash_password("dummy-password")


def authenticate(db, username: str, password: str) -> CurrentUser:
    row = db.fetch_one(
        "SELECT user_id, username, full_name, role, curator_id, password_hash "
        "FROM SystemUsers WHERE username = %s",
        ((username or "").strip(),),
    )
    stored_hash = row[5] if row else _dummy_hash()
    password_ok = verify_password(password or "", stored_hash)
    if row is None or not password_ok:
        raise AuthError("Неверный логин или пароль")
    return CurrentUser(id=row[0], username=row[1], full_name=row[2],
                       role=row[3], curator_id=row[4])


def create_user(db, *, username: str, password: str, full_name: str, role: str,
                curator_id=None, email=None, phone=None) -> int:
    username = clean_text(username, label="Логин", required=True, max_length=50)
    full_name = clean_text(full_name, label="ФИО", required=True, max_length=100)
    if role not in (ROLE_ADMIN, ROLE_CURATOR):
        raise ValidationError(f"Неизвестная роль: {role}")
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов")
    with db.transaction() as cur:
        cur.execute(
            "INSERT INTO SystemUsers (username, password_hash, full_name, role, curator_id, email, phone) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING user_id",
            (username, hash_password(password), full_name, role, curator_id, email, phone),
        )
        return cur.fetchone()[0]
