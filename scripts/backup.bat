@echo off
chcp 65001 >nul
REM ============================================================
REM  JoyBox — Резервное копирование БД
REM  Использование:
REM    backup.bat              — полный бэкап (custom format)
REM    backup.bat sql          — SQL-дамп
REM    backup.bat data         — только данные
REM ============================================================

cd /d "%~dp0\..\joybox"

set FORMAT=custom
set EXTRA=

if /i "%1"=="sql"  set FORMAT=sql
if /i "%1"=="data" set EXTRA=--data-only

echo.
echo [JoyBox] Запуск резервного копирования...
echo   Формат: %FORMAT%
echo.

python manage.py backup_db --format %FORMAT% %EXTRA%

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ОШИБКА] Резервное копирование не удалось.
    pause
    exit /b 1
)

echo.
echo [OK] Готово.
pause
