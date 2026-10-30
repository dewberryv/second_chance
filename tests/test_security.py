from second_chance.security import hash_password, verify_password


def test_roundtrip():
    stored = hash_password("Секретный-пароль-1")
    assert verify_password("Секретный-пароль-1", stored)


def test_wrong_password_rejected():
    assert not verify_password("не тот", hash_password("правильный"))


def test_same_password_gives_different_hashes():
    assert hash_password("abc12345") != hash_password("abc12345")


def test_password_is_not_stored_in_clear():
    assert "abc12345" not in hash_password("abc12345")


def test_broken_hash_returns_false_instead_of_raising():
    for broken in ("", "123", "scrypt$1$2", "md5$a$b$c$d$e", "scrypt$x$y$z$!!$!!"):
        assert verify_password("abc12345", broken) is False
