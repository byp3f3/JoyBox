# python manage.py restore_db backups/joybox_test_20260207.backup
# python manage.py restore_db backups/joybox_test_20260207.sql
# python manage.py restore_db --latest  - Восстановить из последнего бэкапа

import os
import subprocess
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            'backup_file',
            nargs='?',
            type=str,
            default=None,
            help='Путь к файлу резервной копии (.backup или .sql)',
        )
        parser.add_argument(
            '--latest',
            action='store_true',
            help='Восстановить из последнего бэкапа в BACKUP_DIR',
        )
        parser.add_argument(
            '--no-confirm',
            action='store_true',
            help='Не запрашивать подтверждение',
        )

    def handle(self, *args, **options):
        backup_file = options['backup_file']

        if options['latest']:
            backup_file = self._find_latest()
        elif not backup_file:
            raise CommandError(
                'Укажите путь к файлу бэкапа или используйте --latest.'
            )

        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise CommandError(f'Файл не найден: {backup_file}')

        db = settings.DATABASES['default']
        db_name = db['NAME']

        # Подтверждение
        if not options['no_confirm']:
            self.stdout.write(self.style.WARNING(
                f'\n  ВНИМАНИЕ! Все текущие данные в БД «{db_name}» будут заменены '
                f'данными из файла:\n  {backup_path}\n'
            ))
            confirm = input('  Продолжить? (yes/no): ')
            if confirm.lower() not in ('yes', 'y', 'да'):
                self.stdout.write('Отменено.')
                return

        env = os.environ.copy()
        env['PGPASSWORD'] = db['PASSWORD']

        pg_bin = getattr(settings, 'PG_BIN_PATH', '')
        ext = backup_path.suffix.lower()

        if ext == '.backup':
            pg_restore = os.path.join(pg_bin, 'pg_restore') if pg_bin else 'pg_restore'
            cmd = [
                pg_restore,
                f'--host={db["HOST"]}',
                f'--port={db["PORT"]}',
                f'--username={db["USER"]}',
                f'--dbname={db_name}',
                '--no-password',
                '--clean',          # DROP объектов перед восстановлением
                '--if-exists',      
                str(backup_path),
            ]
            tool = 'pg_restore'
        elif ext == '.sql':
            # SQL format — используем psql
            psql = os.path.join(pg_bin, 'psql') if pg_bin else 'psql'
            cmd = [
                psql,
                f'--host={db["HOST"]}',
                f'--port={db["PORT"]}',
                f'--username={db["USER"]}',
                f'--dbname={db_name}',
                '--no-password',
                '-f', str(backup_path),
            ]
            tool = 'psql'
        else:
            raise CommandError(
                f'Неподдерживаемое расширение «{ext}». Используйте .backup или .sql.'
            )

        self.stdout.write(f'Восстановление БД «{db_name}» из {backup_path.name}...')

        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=600,
            )
            # pg_restore может вернуть предупреждения (код 1) при --clean --if-exists
            if result.returncode not in (0, 1) and ext == '.backup':
                raise CommandError(
                    f'{tool} завершился с ошибкой (код {result.returncode}):\n{result.stderr}'
                )
            if result.returncode != 0 and ext == '.sql':
                # psql: предупреждения допустимы
                if 'ERROR' in result.stderr:
                    self.stdout.write(self.style.WARNING(
                        f'Предупреждения psql:\n{result.stderr[:1000]}'
                    ))
        except FileNotFoundError:
            raise CommandError(
                f'{tool} не найден. Убедитесь, что PostgreSQL client tools '
                'установлены и добавлены в PATH.'
            )
        except subprocess.TimeoutExpired:
            raise CommandError(f'{tool} превысил время ожидания (10 мин).')

        self.stdout.write(self.style.SUCCESS(
            f'База данных «{db_name}» успешно восстановлена из {backup_path.name}.'
        ))

    # Находит последний бэкап в BACKUP_DIR
    def _find_latest(self):
        backup_dir = Path(settings.BACKUP_DIR)
        if not backup_dir.exists():
            raise CommandError(f'Директория бэкапов не найдена: {backup_dir}')

        backups = sorted(
            [f for f in backup_dir.iterdir() if f.is_file() and f.suffix in ('.backup', '.sql')],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if not backups:
            raise CommandError(f'Бэкапы не найдены в {backup_dir}')

        self.stdout.write(f'Найден последний бэкап: {backups[0].name}')
        return str(backups[0])
