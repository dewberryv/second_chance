"""Хэширование паролей (scrypt из стандартной библиотеки).

Формат хранимой строки: scrypt$N$r$p$salt(base64)$hash(base64).
Параметры лежат внутри строки, поэтому их можно усиливать позже:
старые хэши продолжат проверяться.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os

_N, _R, _P = 2 ** 14, 8, 1
_SALT_BYTES = 16
_KEY_BYTES = 32


def hash_password(password: str, *, n: int = _N, r: int = _R, p: int = _P) -> str:
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=_KEY_BYTES)
    return "$".join((
        "scrypt", str(n), str(r), str(p),
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    ))


def verify_password(password: str, stored: str) -> bool:
    """True, если пароль подходит. Битая строка хэша -> False, а не исключение."""
    try:
        scheme, n, r, p, salt_b64, hash_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt,
                                n=int(n), r=int(r), p=int(p), dklen=len(expected))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)
