@echo off
chcp 65001 >nul
REM ============================================================
REM  JoyBox — Восстановление БД из резервной копии
REM  Использование:
REM    restore.bat                      — из последнего бэкапа
REM    restore.bat path\to\file.backup  — из указанного файла
REM ============================================================

cd /d "%~dp0\..\joybox"

if "%1"=="" (
    echo.
    echo [JoyBox] Восстановление из последнего бэкапа...
    echo.
    python manage.py restore_db --latest
) else (
    echo.
    echo [JoyBox] Восстановление из файла: %1
    echo.
    python manage.py restore_db "%1"
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ОШИБКА] Восстановление не удалось.
    pause
    exit /b 1
)

echo.
echo [OK] Готово.
pause
