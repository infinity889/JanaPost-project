#!/usr/bin/env python3
"""
scripts/gazetteer_report.py — Отчёт о полноте и структуре гео-справочника kaz_geo.sqlite
(используется для раздела «Инженерная часть — 30%» на защите).
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Отчёт по базе kaz_geo.sqlite")
    parser.add_argument("--db", default="backend/data/kaz_geo.sqlite", help="Путь к SQLite базе")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"База {db_path} не найдена. Сначала запустите: python3 scripts/build_gazetteer.py")
        return

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    settlements_cnt = cur.execute("SELECT COUNT(DISTINCT city) FROM settlements").fetchone()[0]
    aliases_cnt = cur.execute("SELECT COUNT(*) FROM settlements").fetchone()[0]
    districts_cnt = cur.execute("SELECT COUNT(DISTINCT district || city) FROM urban_districts").fetchone()[0]
    streets_cnt = cur.execute("SELECT COUNT(DISTINCT city || name_canonical) FROM streets").fetchone()[0]
    street_aliases_cnt = cur.execute("SELECT COUNT(*) FROM streets").fetchone()[0]
    buildings_cnt = cur.execute("SELECT COUNT(*) FROM buildings").fetchone()[0]

    print("=" * 64)
    print("JANA ADDRESS — ОТЧЁТ О ГЕО-СПРАВОЧНИКЕ (kaz_geo.sqlite)")
    print("=" * 64)
    print(f"Файл базы:                        {db_path} ({db_path.stat().st_size / 1024:.1f} KB)")
    print(f"Населённые пункты КАТО:           {settlements_cnt} (алиасов: {aliases_cnt})")
    print(f"Районы городов и областей:        {districts_cnt}")
    print(f"Улицы, мкр и кварталы (OSM+КАТО): {streets_cnt} (поисковых форм: {street_aliases_cnt})")
    print(f"Адресные привязки домов (OSM):    {buildings_cnt}")
    print("-" * 64)
    print("Распределение улиц и микрорайонов по городам:")
    for city, cnt in cur.execute(
        "SELECT city, COUNT(DISTINCT name_canonical) FROM streets GROUP BY city ORDER BY COUNT(DISTINCT name_canonical) DESC"
    ):
        print(f"  - {city:<20}: {cnt} объектов")
    print("=" * 64)
    conn.close()


if __name__ == "__main__":
    main()
