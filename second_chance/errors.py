"""Исключения приложения.

Все ошибки, текст которых можно показать пользователю, наследуются от
ServiceError. Остальные исключения считаются непредвиденными: интерфейс
пишет их в лог и показывает общее сообщение.
"""


class ServiceError(Exception):
    """Ошибка с понятным пользователю сообщением."""


class ValidationError(ServiceError):
    """Некорректные данные формы."""


class AuthError(ServiceError):
    """Неверный логин или пароль."""


class PermissionDenied(ServiceError):
    """У пользователя нет прав на действие."""


class NotFound(ServiceError):
    """Запись не найдена (или не видна пользователю)."""


class DuplicateError(ServiceError):
    """Нарушено ограничение уникальности."""


class IntegrityConflict(ServiceError):
    """Нарушена связь между таблицами (внешний ключ)."""


class DatabaseUnavailable(ServiceError):
    """Нет соединения с базой данных."""
