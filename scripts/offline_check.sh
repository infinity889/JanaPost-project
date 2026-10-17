#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="python3"
if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
fi

echo "============================================================"
echo "  Jana Address — Offline Verification & Stress Test"
echo "============================================================"

echo "[1/4] Сборка локального гео-справочника SQLite (КАТО + OSM)..."
"$PYTHON_BIN" scripts/build_gazetteer.py
"$PYTHON_BIN" scripts/gazetteer_report.py

echo ""
echo "[2/4] Запуск конвейера парсера на валидационной выборке и батче 1000 записей..."
"$PYTHON_BIN" scripts/run_eval.py

echo ""
echo "[3/4] Проверка точности по формуле ТЗ (60% / 25% / 15% + 30% защита)..."
"$PYTHON_BIN" evaluate.py --gt data/val_ground_truth.json --pred data/val_pred.json

echo ""
echo "[4/4] Проверка сборки Frontend (TypeScript + Vite)..."
if command -v npm >/dev/null 2>&1; then
  (cd frontend && npm run build)
fi

echo ""
echo "Все проверки успешно пройдены!"
