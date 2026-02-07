"""
Централизованный обработчик исключений для DRF.
Перехватывает все ошибки и возвращает человекочитаемые сообщения на русском языке
в единообразном формате: { "detail": "...", "code": "..." }
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404
import logging

logger = logging.getLogger(__name__)

# Маппинг стандартных HTTP-кодов на русскоязычные описания
HTTP_STATUS_MESSAGES = {
    400: 'Некорректный запрос.',
    401: 'Необходима авторизация.',
    403: 'Доступ запрещён.',
    404: 'Ресурс не найден.',
    405: 'Метод не поддерживается.',
    406: 'Формат ответа не поддерживается.',
    409: 'Конфликт данных.',
    415: 'Неподдерживаемый тип данных.',
    429: 'Слишком много запросов. Попробуйте позже.',
    500: 'Внутренняя ошибка сервера. Попробуйте позже.',
}

# Маппинг кодов ошибок DRF на русские сообщения
DRF_CODE_MESSAGES = {
    'authentication_failed': 'Ошибка аутентификации. Проверьте логин и пароль.',
    'not_authenticated': 'Необходима авторизация. Войдите в аккаунт.',
    'permission_denied': 'У вас нет прав для выполнения этого действия.',
    'not_found': 'Запрашиваемый ресурс не найден.',
    'method_not_allowed': 'Данный HTTP-метод не поддерживается для этого адреса.',
    'unsupported_media_type': 'Неподдерживаемый формат данных.',
    'throttled': 'Слишком много запросов. Повторите через некоторое время.',
    'parse_error': 'Ошибка разбора данных запроса. Проверьте формат JSON.',
    'invalid': 'Некорректное значение.',
    'required': 'Это поле обязательно для заполнения.',
    'blank': 'Это поле не может быть пустым.',
    'null': 'Это поле не может быть пустым.',
    'max_length': 'Превышена максимальная длина.',
    'min_length': 'Слишком короткое значение.',
    'max_value': 'Значение слишком большое.',
    'min_value': 'Значение слишком маленькое.',
    'unique': 'Объект с таким значением уже существует.',
    'does_not_exist': 'Указанный объект не найден.',
    'invalid_choice': 'Недопустимое значение.',
}

# Маппинг английских фраз DRF на русские
ENGLISH_TO_RUSSIAN = {
    'This field is required.': 'Это поле обязательно для заполнения.',
    'This field may not be blank.': 'Это поле не может быть пустым.',
    'This field may not be null.': 'Это поле не может быть пустым.',
    'Invalid pk': 'Указанный объект не найден.',
    'Ensure this field has no more than': 'Превышена максимальная длина поля.',
    'Ensure this field has at least': 'Слишком короткое значение поля.',
    'A valid integer is required.': 'Требуется целое число.',
    'A valid number is required.': 'Требуется число.',
    'Enter a valid email address.': 'Введите корректный email-адрес.',
    'This password is too short.': 'Пароль слишком короткий.',
    'This password is too common.': 'Пароль слишком простой.',
    'This password is entirely numeric.': 'Пароль не может состоять только из цифр.',
    'Unable to log in with provided credentials.': 'Неверный email или пароль.',
    'User account is disabled.': 'Аккаунт заблокирован.',
    'Invalid token.': 'Недействительный токен авторизации.',
    'Token has expired.': 'Токен авторизации истёк. Войдите заново.',
    'Not found.': 'Ресурс не найден.',
    'Authentication credentials were not provided.': 'Необходима авторизация. Войдите в аккаунт.',
    'You do not have permission to perform this action.': 'У вас нет прав для выполнения этого действия.',
    'Method "{method}" not allowed.': 'Метод не поддерживается.',
}

# Маппинг названий полей на русские
FIELD_NAMES_RU = {
    'email': 'Email',
    'password': 'Пароль',
    'confirmPassword': 'Подтверждение пароля',
    'firstName': 'Имя',
    'lastName': 'Фамилия',
    'middleName': 'Отчество',
    'phone': 'Телефон',
    'birthDate': 'Дата рождения',
    'productName': 'Название товара',
    'productDescription': 'Описание товара',
    'price': 'Цена',
    'quantity': 'Количество',
    'ageRating': 'Возрастной рейтинг',
    'categoryId': 'Категория',
    'brandId': 'Бренд',
    'categoryName': 'Название категории',
    'categoryDescription': 'Описание категории',
    'brandName': 'Название бренда',
    'brandCountry': 'Страна бренда',
    'brandDescription': 'Описание бренда',
    'city': 'Город',
    'street': 'Улица',
    'house': 'Дом',
    'flat': 'Квартира',
    'index': 'Индекс',
    'rating': 'Оценка',
    'comment': 'Комментарий',
    'roleId': 'Роль',
    'non_field_errors': 'Ошибка',
    'detail': 'Ошибка',
}


def _translate_message(msg):
    """Пытается перевести английское сообщение на русский."""
    if not isinstance(msg, str):
        return str(msg)

    # Точное совпадение
    if msg in ENGLISH_TO_RUSSIAN:
        return ENGLISH_TO_RUSSIAN[msg]

    # Частичное совпадение
    for eng, rus in ENGLISH_TO_RUSSIAN.items():
        if eng in msg:
            return rus

    return msg


def _flatten_errors(errors, parent_key=''):
    """
    Преобразует вложенный словарь ошибок DRF в плоский список
    человекочитаемых сообщений.
    """
    messages = []

    if isinstance(errors, str):
        messages.append(_translate_message(errors))
    elif isinstance(errors, list):
        for item in errors:
            if isinstance(item, dict):
                messages.extend(_flatten_errors(item, parent_key))
            else:
                translated = _translate_message(str(item))
                if parent_key:
                    field_name = FIELD_NAMES_RU.get(parent_key, parent_key)
                    messages.append(f'{field_name}: {translated}')
                else:
                    messages.append(translated)
    elif isinstance(errors, dict):
        for key, value in errors.items():
            if key in ('non_field_errors', 'detail'):
                messages.extend(_flatten_errors(value, ''))
            else:
                messages.extend(_flatten_errors(value, key))

    return messages


def custom_exception_handler(exc, context):
    """
    Централизованный обработчик исключений.
    Возвращает ответ в формате: { "detail": "сообщение", "code": "код_ошибки" }
    """

    # Конвертируем Django ValidationError в DRF ValidationError
    if isinstance(exc, DjangoValidationError):
        from rest_framework.exceptions import ValidationError as DRFValidationError
        if hasattr(exc, 'message_dict'):
            exc = DRFValidationError(detail=exc.message_dict)
        elif hasattr(exc, 'messages'):
            exc = DRFValidationError(detail=exc.messages)
        else:
            exc = DRFValidationError(detail=str(exc))

    # Стандартный обработчик DRF
    response = exception_handler(exc, context)

    if response is not None:
        # Обработка данных ответа
        detail = response.data
        code = getattr(exc, 'default_code', 'error')
        status_code = response.status_code

        # Извлекаем и переводим сообщения
        if isinstance(detail, dict):
            if 'detail' in detail and len(detail) == 1:
                # Простая ошибка вида {"detail": "message"}
                msg = _translate_message(str(detail['detail']))
            else:
                # Ошибки валидации — собираем в одну строку
                flat_messages = _flatten_errors(detail)
                msg = '; '.join(flat_messages) if flat_messages else HTTP_STATUS_MESSAGES.get(status_code, 'Произошла ошибка.')
        elif isinstance(detail, list):
            flat_messages = _flatten_errors(detail)
            msg = '; '.join(flat_messages) if flat_messages else HTTP_STATUS_MESSAGES.get(status_code, 'Произошла ошибка.')
        else:
            msg = _translate_message(str(detail))

        # Формируем единообразный ответ
        response.data = {
            'detail': msg,
            'code': str(code),
        }

        return response

    # Обработка исключений, не перехваченных стандартным обработчиком DRF

    if isinstance(exc, IntegrityError):
        logger.exception("IntegrityError в API")
        error_msg = str(exc)
        # Пытаемся распознать тип ошибки целостности
        if 'unique' in error_msg.lower() or 'duplicate' in error_msg.lower():
            detail = 'Запись с такими данными уже существует.'
        elif 'foreign key' in error_msg.lower() or 'violates foreign key' in error_msg.lower():
            detail = 'Невозможно выполнить операцию: связанные данные не найдены.'
        elif 'not-null' in error_msg.lower() or 'null value' in error_msg.lower():
            detail = 'Не заполнено обязательное поле.'
        elif 'check' in error_msg.lower():
            detail = 'Данные не прошли проверку ограничений.'
        else:
            detail = 'Ошибка целостности данных.'
        return Response(
            {'detail': detail, 'code': 'integrity_error'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if isinstance(exc, Http404):
        return Response(
            {'detail': 'Запрашиваемый ресурс не найден.', 'code': 'not_found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Непредвиденная ошибка
    logger.exception("Необработанное исключение в API: %s", exc)
    return Response(
        {'detail': 'Внутренняя ошибка сервера. Попробуйте позже.', 'code': 'server_error'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
