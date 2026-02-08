#!/usr/bin/env bash
# ============================================================
#  JoyBox — Резервное копирование БД
#  Использование:
#    ./backup.sh              — полный бэкап (custom format)
#    ./backup.sh sql          — SQL-дамп
#    ./backup.sh data         — только данные
# ============================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/../joybox"

FORMAT="custom"
EXTRA=""

case "${1,,}" in
    sql)  FORMAT="sql" ;;
    data) EXTRA="--data-only" ;;
esac

echo ""
echo "[JoyBox] Запуск резервного копирования..."
echo "  Формат: $FORMAT"
echo ""

python manage.py backup_db --format "$FORMAT" $EXTRA

echo ""
echo "[OK] Готово."
