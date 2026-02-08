#!/usr/bin/env bash
# ============================================================
#  JoyBox — Восстановление БД из резервной копии
#  Использование:
#    ./restore.sh                     — из последнего бэкапа
#    ./restore.sh path/to/file.backup — из указанного файла
# ============================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/../joybox"

if [ -z "$1" ]; then
    echo ""
    echo "[JoyBox] Восстановление из последнего бэкапа..."
    echo ""
    python manage.py restore_db --latest
else
    echo ""
    echo "[JoyBox] Восстановление из файла: $1"
    echo ""
    python manage.py restore_db "$1"
fi

echo ""
echo "[OK] Готово."
