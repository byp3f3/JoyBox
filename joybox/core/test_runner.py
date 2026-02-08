"""
Кастомный test runner для JoyBox.

Поскольку модели используют managed = False, а схема БД создаётся
через SQL-скрипт (create_database.sql), стандартный Django test runner
не может создать таблицы через миграции (миграции ссылаются на user,
который создаётся SQL-скриптом, а не миграциями).

Решение: подключаемся к процессу создания тестовой БД и применяем
SQL-скрипт ДО того, как Django запустит миграции.
"""

from pathlib import Path
from django.test.runner import DiscoverRunner
from django.db import connections
from django.db.backends.postgresql.creation import DatabaseCreation as PgCreation
from django.core.management import call_command


# Путь к SQL-скрипту
SQL_SCHEMA_FILE = Path(__file__).resolve().parent.parent.parent / 'create_database.sql'


class JoyBoxDatabaseCreation(PgCreation):
    """
    Расширение стандартного PostgreSQL DatabaseCreation.
    Применяет create_database.sql после создания БД, но до миграций.
    """

    def create_test_db(self, verbosity=1, autoclobber=False, serialize=True, keepdb=False):
        """
        Переопределяем создание тестовой БД:
        1. Создаём пустую БД
        2. Применяем SQL-скрипт
        3. Запускаем миграции (для auth, authtoken и т.д.)
        """
        test_database_name = self._get_test_db_name()
        if verbosity >= 1:
            action = 'Using existing' if keepdb else 'Creating'
            self.log(f'{action} test database for alias {self.connection.alias}...')

        if not keepdb:
            self._create_test_db(verbosity, autoclobber, keepdb)

        self.connection.close()
        settings_dict = self.connection.settings_dict
        settings_dict['NAME'] = test_database_name

        # Теперь подключены к тестовой БД — применяем SQL-схему
        self._apply_sql_schema(verbosity)

        # Запускаем миграции (создаст auth, authtoken и другие managed-таблицы)
        if verbosity >= 1:
            self.log('Running migrations on test database...')
        call_command(
            'migrate',
            verbosity=max(verbosity - 1, 0),
            interactive=False,
            database=self.connection.alias,
            run_syncdb=True,
        )

        return test_database_name

    def _apply_sql_schema(self, verbosity=1):
        """Применяет create_database.sql к тестовой БД."""
        if not SQL_SCHEMA_FILE.exists():
            raise FileNotFoundError(
                f'SQL-скрипт не найден: {SQL_SCHEMA_FILE}\n'
                'Убедитесь, что create_database.sql находится в корне проекта.'
            )

        if verbosity >= 1:
            self.log(f'Applying SQL schema from {SQL_SCHEMA_FILE.name}...')

        sql_content = SQL_SCHEMA_FILE.read_text(encoding='utf-8')

        # Убираем строки создания/подключения БД
        lines = sql_content.split('\n')
        filtered = []
        for line in lines:
            stripped = line.strip().upper()
            if stripped.startswith('CREATE DATABASE') or stripped.startswith('\\C'):
                continue
            filtered.append(line)
        sql_content = '\n'.join(filtered)

        connection = connections[self.connection.alias]
        with connection.cursor() as cursor:
            cursor.execute(sql_content)

        if verbosity >= 1:
            self.log('SQL schema applied successfully.')


class JoyBoxTestRunner(DiscoverRunner):
    """
    Test runner, который подменяет DatabaseCreation на кастомный,
    чтобы SQL-скрипт выполнялся до миграций.
    """

    def setup_databases(self, **kwargs):
        # Подменяем creation class для default-соединения
        connection = connections['default']
        original_creation_class = connection.creation.__class__

        # Подменяем на наш кастомный
        connection.creation.__class__ = JoyBoxDatabaseCreation

        try:
            result = super().setup_databases(**kwargs)
        finally:
            # Восстанавливаем оригинальный класс
            connection.creation.__class__ = original_creation_class

        return result
