"""Создание базы, схемы и пользователей.

    python scripts/init_db.py              # первая установка (с демо-данными)
    python scripts/init_db.py --no-demo    # пустая база, только администратор
    python scripts/init_db.py --reset      # ПОЛНОСТЬЮ пересоздать таблицы

Пароли берутся из переменных SC_ADMIN_PASSWORD / SC_CURATOR_PASSWORD
или запрашиваются в консоли. В коде и в SQL паролей нет.
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2  # noqa: E402
from psycopg2 import sql  # noqa: E402

from second_chance.config import SQL_DIR, load_db_config  # noqa: E402
from second_chance.constants import ROLE_ADMIN, ROLE_CURATOR  # noqa: E402
from second_chance.db import Database  # noqa: E402
from second_chance.services.auth import MIN_PASSWORD_LENGTH, create_user  # noqa: E402


def ensure_database(config) -> None:
    """Создаёт базу, если её ещё нет (подключаясь к служебной базе postgres)."""
    try:
        psycopg2.connect(host=config.host, port=config.port, dbname=config.name,
                         user=config.user, password=config.password, connect_timeout=5).close()
        return
    except psycopg2.OperationalError:
        pass
    admin_conn = psycopg2.connect(host=config.host, port=config.port, dbname="postgres",
                                  user=config.user, password=config.password, connect_timeout=5)
    admin_conn.autocommit = True
    with admin_conn.cursor() as cur:
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(config.name)))
    admin_conn.close()
    print(f"База «{config.name}» создана")


def read_password(env_name: str, who: str) -> str:
    password = os.environ.get(env_name)
    while not password or len(password) < MIN_PASSWORD_LENGTH:
        if password:
            print(f"Пароль должен быть не короче {MIN_PASSWORD_LENGTH} символов")
        password = getpass.getpass(f"Пароль для {who}: ")
        if password and getpass.getpass("Повторите пароль: ") != password:
            print("Пароли не совпали")
            password = ""
    return password


def run_script(db: Database, name: str) -> None:
    with db.transaction() as cur:
        cur.execute((SQL_DIR / name).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="удалить существующие таблицы и создать заново")
    parser.add_argument("--no-demo", action="store_true", help="не загружать демонстрационные данные")
    parser.add_argument("--yes", action="store_true", help="не спрашивать подтверждение для --reset")
    args = parser.parse_args()

    config = load_db_config()
    ensure_database(config)
    db = Database(config)
    db.connect()

    exists = db.fetch_one("SELECT to_regclass('public.systemusers') IS NOT NULL")[0]
    if exists and not args.reset:
        print("Таблицы уже есть. Чтобы пересоздать их, запустите с --reset (данные будут удалены).")
        return 1
    if exists and args.reset and not args.yes:
        answer = input(f"Все данные в «{config.name}» будут удалены. Введите имя базы для подтверждения: ")
        if answer != config.name:
            print("Отменено")
            return 1

    if exists:
        run_script(db, "drop.sql")
    run_script(db, "schema.sql")

    demo = not args.no_demo
    if demo:
        run_script(db, "seed_base.sql")

    # Порядок важен: демо-выдачи помощи ссылаются на user_id 1 (admin) и 2 (curator).
    create_user(db, username="admin", password=read_password("SC_ADMIN_PASSWORD", "admin"),
                full_name="Администратор", role=ROLE_ADMIN)
    if demo:
        create_user(db, username="curator", password=read_password("SC_CURATOR_PASSWORD", "curator"),
                    full_name="Сидоренко Ольга Константиновна", role=ROLE_CURATOR, curator_id=1)
        run_script(db, "seed_demo.sql")

    db.close()
    print("Готово. Запуск приложения: python -m second_chance")
    return 0


if __name__ == "__main__":
    sys.exit(main())
