# Second Chance

Десктопное приложение для центра социальной адаптации: учёт резидентов, комнат,
индивидуальных программ реабилитации (ИПР), мероприятий, склада гуманитарной
помощи и её выдачи, отчёты с выгрузкой в CSV.

**Стек:** Python 3.10+, Tkinter, PostgreSQL 13+, psycopg2, pytest.

## Архитектура

second_chance/
  config.py        настройки БД из окружения / .env
  db.py            соединение, транзакции, перевод ошибок драйвера в понятные
  security.py      хэширование паролей (scrypt)
  validation.py    проверка данных форм (чистые функции)
  services/        вся бизнес-логика и SQL (по модулю на сущность)
  ui/              Tkinter: формы, таблицы, вкладки - без SQL и бизнес-правил
sql/               schema.sql, демо-данные
scripts/init_db.py создание БД, схемы и пользователей
tests/             pytest; БД подменяется поддельной, Tkinter не нужен

Интерфейс вызывает только сервисы; сервисы ничего не знают про Tkinter. Поэтому
логику можно тестировать без графики и без работающего PostgreSQL.

## Запуск

```bash
python -m second_chance
```

`init_db.py` спросит пароли для `admin` и `curator` (или возьмёт из переменных
`SC_ADMIN_PASSWORD`, `SC_CURATOR_PASSWORD`). Без демо-данных: `--no-demo`.
Пересоздать таблицы: `--reset` (удаляет данные, а также позволяет самим установить удобный пароль).

## Роли

| Возможность                              | Администратор | Куратор                |
|------------------------------------------|:-------------:|:----------------------:|
| Резиденты: просмотр                      | все           | только свои            |
| Резиденты: добавить / изменить / удалить | да            | нет                    |
| ИПР и мероприятия: просмотр              | все           | только свои            |
| ИПР и мероприятия: создание, статус      | нет           | да, в своих ИПР        |
| Выдача помощи                            | всем          | только своим резидентам|
| Склад: пополнение, статистика            | да            | нет                    |
| Отчёты и выгрузка в CSV                  | все данные    | только свои данные     |

Куратор привязан к сотруднику через `SystemUsers.curator_id`, поэтому видит
именно своих подопечных, а не данные «куратора №1».

## Тесты

```bash
pip install -r requirements-dev.txt
pytest
```

Проверяются: хэширование паролей, валидация, права доступа, вместимость комнат,
атомарное списание со склада, область видимости куратора, CSV-экспорт.


## Ограничения

- Редактирование ИПР и добавление новых позиций склада пока не реализованы.
- Демо-данные вымышленные.
- Учётные записи создаются скриптом; управления пользователями в интерфейсе нет.

## Скриншоты

### Резиденты и поиск
<img src="docs/screenshots/residents.png" width="800" alt="Список резидентов">

<img src="docs/screenshots/addition-of-a-resident-into-the-system-by-an-admin.png" width="500" alt="Добавление резидента администратором">

### ИПР и мероприятия
<img src="docs/screenshots/ipr.png" width="800" alt="Список ИПР">

<img src="docs/screenshots/events.png" width="800" alt="Мероприятия">

### Склад и выдача помощи
<img src="docs/screenshots/warehouse.png" width="800" alt="Склад">

<img src="docs/screenshots/distribution-of-aid.png" width="800" alt="Выдача помощи">

### Отчёты и статистика
<img src="docs/screenshots/reports.png" width="800" alt="Отчёты">

<img src="docs/screenshots/statistics.png" width="800" alt="Статистика">

<details>
<summary>Ещё скриншоты: формы, отчёты, CSV</summary>

<img src="docs/screenshots/ipr-assignment-by-curator.png" width="500" alt="Создание ИПР куратором">
<img src="docs/screenshots/event-assignment-by-curator.png" width="500" alt="Создание мероприятия куратором">
<img src="docs/screenshots/supplement-of-warehouse-by-admin.png" width="500" alt="Пополнение склада администратором">
<img src="docs/screenshots/aid-distribution-by-admin.png" width="500" alt="Выдача помощи администратором">
<img src="docs/screenshots/rooms.png" width="800" alt="Комнаты и заполненность">
<img src="docs/screenshots/current-list-of-residents.png" width="800" alt="Отчёт: текущий состав">
<img src="docs/screenshots/fulfillment-of-ipr.png" width="800" alt="Отчёт: выполнение ИПР">
<img src="docs/screenshots/distribution-of-aid-report.png" width="800" alt="Отчёт: выдача помощи">
<img src="docs/screenshots/csv-format-working-for-reports.png" width="800" alt="Выгрузка отчёта в CSV">

</details>