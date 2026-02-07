"""
Команда для создания резервной копии базы данных PostgreSQL.

Использование:
    python manage.py backup_db                  # Полный бэкап (custom format)
    python manage.py backup_db --format sql     # SQL-дамп
    python manage.py backup_db --data-only      # Только данные
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = 'Создание резервной копии базы данных PostgreSQL (pg_dump)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            type=str,
            choices=['custom', 'sql'],
            default='custom',
            help='Формат дампа: custom (.backup, сжатый) или sql (.sql, текстовый). По умолчанию: custom',
        )
        parser.add_argument(
            '--data-only',
            action='store_true',
            help='Выгрузить только данные (без схемы)',
        )
        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='Путь к выходному файлу (по умолчанию — авто в BACKUP_DIR)',
        )

    def handle(self, *args, **options):
        db = settings.DATABASES['default']
        backup_dir = Path(settings.BACKUP_DIR)
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        db_name = db['NAME']
        fmt = options['format']

        # Определяем расширение и аргументы формата
        if fmt == 'custom':
            ext = '.backup'
            format_args = ['--format=custom']
        else:
            ext = '.sql'
            format_args = ['--format=plain']

        suffix = '_data' if options['data_only'] else ''
        default_filename = f'{db_name}_{timestamp}{suffix}{ext}'

        output_path = options['output'] or str(backup_dir / default_filename)

        # Формируем команду pg_dump
        pg_bin = getattr(settings, 'PG_BIN_PATH', '')
        pg_dump = os.path.join(pg_bin, 'pg_dump') if pg_bin else 'pg_dump'

        cmd = [
            pg_dump,
            f'--host={db["HOST"]}',
            f'--port={db["PORT"]}',
            f'--username={db["USER"]}',
            '--no-password',
            f'--file={output_path}',
        ]
        cmd.extend(format_args)

        if options['data_only']:
            cmd.append('--data-only')

        cmd.append(db_name)

        # Передаём пароль через переменную окружения
        env = os.environ.copy()
        env['PGPASSWORD'] = db['PASSWORD']

        self.stdout.write(f'Создание резервной копии БД «{db_name}»...')
        self.stdout.write(f'Формат: {fmt}, Только данные: {options["data_only"]}')

        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=600,  # 10 минут
            )
            if result.returncode != 0:
                raise CommandError(
                    f'pg_dump завершился с ошибкой (код {result.returncode}):\n{result.stderr}'
                )
        except FileNotFoundError:
            raise CommandError(
                'pg_dump не найден. Убедитесь, что PostgreSQL client tools установлены '
                'и добавлены в PATH.'
            )
        except subprocess.TimeoutExpired:
            raise CommandError('pg_dump превысил время ожидания (10 мин).')

        file_size = os.path.getsize(output_path)
        size_str = self._human_size(file_size)

        self.stdout.write(self.style.SUCCESS(
            f'Резервная копия создана: {output_path} ({size_str})'
        ))

        # Ротация старых бэкапов
        self._rotate_backups(backup_dir)

        return output_path

    def _rotate_backups(self, backup_dir):
        """Удаляет старые бэкапы, оставляя не более BACKUP_MAX_COUNT."""
        max_count = getattr(settings, 'BACKUP_MAX_COUNT', 10)
        backups = sorted(
            [f for f in backup_dir.iterdir() if f.is_file() and f.suffix in ('.backup', '.sql')],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if len(backups) > max_count:
            for old in backups[max_count:]:
                old.unlink()
                self.stdout.write(f'  Удалён старый бэкап: {old.name}')

    @staticmethod
    def _human_size(nbytes):
        for unit in ('Б', 'КБ', 'МБ', 'ГБ'):
            if abs(nbytes) < 1024:
                return f'{nbytes:.1f} {unit}'
            nbytes /= 1024
        return f'{nbytes:.1f} ТБ'
