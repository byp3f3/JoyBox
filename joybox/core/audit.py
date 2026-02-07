"""
Журнал аудита: запись действий администраторов и менеджеров в auditLog.
Кто / когда / что менял (до/после).
"""
from decimal import Decimal
from django.utils import timezone
from django.db import connection
from .models import AuditLog


def set_audit_user(user):
    """
    Устанавливает ID текущего пользователя в сессии PostgreSQL.
    Используется триггерами аудита (fn_audit_log) для записи,
    кто именно выполнил операцию.
    """
    if user and hasattr(user, 'pk') and user.pk:
        with connection.cursor() as cursor:
            cursor.execute("SET app.current_user_id = %s", [str(user.pk)])


# Поля, которые не логируем (пароли и т.п.)
SENSITIVE_FIELDS = frozenset({'password', 'password_hash'})


def _json_safe(val):
    """Приводит значение к виду, пригодному для JSON (в т.ч. JSONField)."""
    if val is None:
        return None
    if hasattr(val, 'pk'):
        return val.pk
    if hasattr(val, 'isoformat'):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (int, float, str, bool)):
        return val
    if isinstance(val, (list, tuple)):
        return [_json_safe(v) for v in val]
    if isinstance(val, dict):
        return {k: _json_safe(v) for k, v in val.items()}
    return str(val)


def model_to_log_dict(instance):
    """Преобразует экземпляр модели в словарь для лога (JSON-сериализуемый)."""
    if instance is None:
        return None
    data = {}
    for f in instance._meta.fields:
        if f.name in SENSITIVE_FIELDS:
            continue
        try:
            val = getattr(instance, f.name)
            data[f.name] = _json_safe(val)
        except Exception:
            pass
    return data


def get_pk(instance):
    """Возвращает primary key значения экземпляра (число)."""
    if instance is None:
        return None
    pk = getattr(instance, 'pk', None)
    if pk is not None:
        return int(pk)
    # Модели с кастомным pk (userId, productId и т.д.)
    for f in instance._meta.fields:
        if f.primary_key:
            return int(getattr(instance, f.name, None))
    return None


def log_audit(user, action, table_name, record_id, old_values=None, new_values=None):
    """
    Записывает действие в auditLog.
    user — экземпляр User (кто выполнил действие),
    action — строка действия (например "CREATE", "UPDATE", "DELETE"),
    table_name — имя таблицы/сущности,
    record_id — id записи,
    old_values / new_values — dict или None (до/после).
    Ошибки записи не прерывают основной запрос.
    """
    try:
        if user is None:
            return
        user_id = getattr(user, 'userId', getattr(user, 'pk', None))
        if user_id is None:
            return
        if record_id is None:
            return
        AuditLog.objects.create(
            userId_id=int(user_id),
            action=(action or '')[:100],
            tableName=(table_name or '')[:100],
            recordId=record_id,
            oldValues=old_values,
            newValues=new_values,
            createdAt=timezone.now(),
        )
    except Exception:
        pass  # не ломаем основной запрос из-за ошибки аудита
