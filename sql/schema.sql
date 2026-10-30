-- =====================================================================
-- Second Chance: схема БД (PostgreSQL 13+)
-- Порядок создания учитывает внешние ключи. Пользователей создаёт
-- scripts/init_db.py (пароли хранятся только в виде хэша).
-- =====================================================================

CREATE TABLE Rooms (
    room_number INTEGER PRIMARY KEY,
    capacity    INTEGER NOT NULL CHECK (capacity > 0),
    -- административный статус; заполненность считается по резидентам
    room_status VARCHAR(50) NOT NULL CHECK (room_status IN ('Свободно', 'Занято', 'На ремонте')),
    floor       INTEGER,
    notes       TEXT
);

CREATE TABLE Curators (
    curator_id     SERIAL PRIMARY KEY,
    full_name      VARCHAR(100) NOT NULL,
    position       VARCHAR(100) NOT NULL,
    phone          VARCHAR(20),
    email          VARCHAR(100),
    specialization TEXT,
    hire_date      DATE NOT NULL,
    status         VARCHAR(20) NOT NULL DEFAULT 'Активен'
                   CHECK (status IN ('Активен', 'В отпуске', 'Уволен'))
);

CREATE TABLE SystemUsers (
    user_id       SERIAL PRIMARY KEY,
    username      VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(100) NOT NULL,
    role          VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'curator')),
    -- связь учётной записи с сотрудником: по ней куратор видит только своих резидентов
    curator_id    INTEGER REFERENCES Curators(curator_id) ON DELETE SET NULL,
    email         VARCHAR(100),
    phone         VARCHAR(20),
    created_date  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Residents (
    resident_id         SERIAL PRIMARY KEY,
    full_name           VARCHAR(100) NOT NULL,
    birth_date          DATE,
    document_type       VARCHAR(50),
    document_number     VARCHAR(50),
    document_issued_by  VARCHAR(200),
    document_issue_date DATE,
    phone               VARCHAR(20),
    email               VARCHAR(100),
    admission_date      DATE NOT NULL,
    admission_reason    TEXT,
    status              VARCHAR(50) NOT NULL
                        CHECK (status IN ('На карантине', 'Основной поток', 'На выезде', 'Выбыл')),
    health_status       TEXT,
    social_status       VARCHAR(100),
    room_number         INTEGER,
    curator_id          INTEGER,
    created_by          INTEGER,
    created_date        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_date        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- номер документа - альтернативный ключ (NULL допустим: документы могут быть утеряны)
    CONSTRAINT residents_ak_document UNIQUE (document_number),
    CONSTRAINT fk_residents_room
        FOREIGN KEY (room_number) REFERENCES Rooms(room_number)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_residents_curator
        FOREIGN KEY (curator_id) REFERENCES Curators(curator_id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_residents_created_by
        FOREIGN KEY (created_by) REFERENCES SystemUsers(user_id)
        ON DELETE SET NULL ON UPDATE CASCADE
);

-- ИПР - индивидуальные программы реабилитации
CREATE TABLE IPR (
    ipr_id           SERIAL PRIMARY KEY,
    resident_id      INTEGER NOT NULL REFERENCES Residents(resident_id),
    curator_id       INTEGER NOT NULL REFERENCES Curators(curator_id),
    creation_date    DATE NOT NULL,
    start_date       DATE NOT NULL,
    end_date         DATE,
    ipr_status       VARCHAR(50) NOT NULL DEFAULT 'Активна'
                     CHECK (ipr_status IN ('Активна', 'Приостановлена', 'Завершена', 'Назначена')),
    main_goal        TEXT NOT NULL,
    specific_goals   TEXT,
    success_criteria TEXT,
    notes            TEXT,
    CONSTRAINT ipr_date_check CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE TABLE ExternalOrganizations (
    org_id         SERIAL PRIMARY KEY,
    name           VARCHAR(200) NOT NULL,
    org_type       VARCHAR(100) NOT NULL
                   CHECK (org_type IN ('Медицинская', 'Трудовая', 'Социальная',
                                       'Образовательная', 'Правовая', 'Психологическая')),
    address        TEXT,
    phone          VARCHAR(20),
    email          VARCHAR(100),
    contact_person VARCHAR(100),
    working_hours  TEXT,
    notes          TEXT
);

CREATE TABLE Events (
    event_id               SERIAL PRIMARY KEY,
    ipr_id                 INTEGER NOT NULL REFERENCES IPR(ipr_id) ON DELETE CASCADE,
    event_type             VARCHAR(100) NOT NULL
                           CHECK (event_type IN ('Медицинское', 'Социальное', 'Трудовое',
                                                 'Образовательное', 'Психологическое', 'Правовое')),
    title                  VARCHAR(200) NOT NULL,
    description            TEXT,
    planned_date           DATE NOT NULL,
    actual_date            DATE,
    event_status           VARCHAR(50) NOT NULL DEFAULT 'Запланировано'
                           CHECK (event_status IN ('Запланировано', 'В процессе', 'Выполнено',
                                                   'Провалено', 'Отменено')),
    result                 TEXT,
    notes                  TEXT,
    org_id                 INTEGER REFERENCES ExternalOrganizations(org_id),
    responsible_curator_id INTEGER REFERENCES Curators(curator_id),
    cost                   DECIMAL(10,2),
    location               VARCHAR(200)
);

CREATE TABLE Warehouse (
    item_id            SERIAL PRIMARY KEY,
    name               VARCHAR(200) NOT NULL,
    category           VARCHAR(100) NOT NULL
                       CHECK (category IN ('Одежда', 'Гигиена', 'Продукты', 'Обувь',
                                           'Постельное белье', 'Бытовая техника', 'Другое')),
    description        TEXT,
    unit               VARCHAR(50) NOT NULL,
    min_quantity       INTEGER DEFAULT 5,
    current_quantity   DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK (current_quantity >= 0),
    unit_price         DECIMAL(10,2) CHECK (unit_price IS NULL OR unit_price >= 0),
    storage_location   VARCHAR(100),
    supplier           VARCHAR(200),
    last_delivery_date DATE
);

CREATE TABLE AidDistribution (
    distribution_id   SERIAL PRIMARY KEY,
    resident_id       INTEGER NOT NULL REFERENCES Residents(resident_id),
    item_id           INTEGER NOT NULL REFERENCES Warehouse(item_id),
    distribution_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    quantity          DECIMAL(10,2) NOT NULL CHECK (quantity > 0),
    issued_by         INTEGER NOT NULL REFERENCES SystemUsers(user_id),
    purpose           TEXT,
    notes             TEXT
);

-- Индексы под реальные запросы приложения (фильтры по куратору, внешние ключи)
CREATE INDEX idx_residents_status  ON Residents(status);
CREATE INDEX idx_residents_room    ON Residents(room_number);
CREATE INDEX idx_residents_curator ON Residents(curator_id);
CREATE INDEX idx_ipr_resident      ON IPR(resident_id);
CREATE INDEX idx_ipr_curator       ON IPR(curator_id);
CREATE INDEX idx_events_ipr        ON Events(ipr_id);
CREATE INDEX idx_events_curator    ON Events(responsible_curator_id);
CREATE INDEX idx_events_date       ON Events(planned_date);
CREATE INDEX idx_aid_resident      ON AidDistribution(resident_id);
CREATE INDEX idx_aid_item          ON AidDistribution(item_id);
