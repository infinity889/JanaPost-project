#!/usr/bin/env python3
"""
evaluate.py — Скрипт оценки качества разбора адресов строго по правилам ТЗ Jana Address.

Формула авто-метрики (45% итоговой оценки):
  Score = 0.60 * Address + 0.25 * Details + 0.15 * Reference_In_String

Где:
  - Address (60%): province, city, street_name, house
  - Details (25%): apartment, entrance, floor
  - Reference_In_String (15%): district, living_area — ТОЛЬКО по записям, где они есть в строке raw_address.

Правила ТЗ:
  1. Поля, которых нет ни в строке/эталоне, ни в ответе (null == null), исключаются из подсчёта по этому полю.
  2. Сравнение посимвольное после приведения к нижнему регистру, удаления пунктуации и лишних пробелов
     (для номеров домов и квартир дробь '/' сохраняется: «1/2» != «1» и «1/2» != «12»).
  3. street_type, landmark и поля district, поднятые из справочника (когда их нет в строке),
     в авто-метрику не входят и оцениваются отдельно в блоке «Инженерная часть (30%)».
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ADDRESS_FIELDS = ("province", "city", "street_name", "house")
DETAIL_FIELDS = ("apartment", "entrance", "floor")
REFERENCE_FIELDS = ("district", "living_area")
EXTRA_DEFENSE_FIELDS = ("street_type", "landmark")


def normalize_value(val: Optional[Any], preserve_slash: bool = False) -> Optional[str]:
    """Приводит значение к нижнему регистру, убирает пунктуацию и лишние пробелы."""
    if val is None:
        return None
    s = str(val).strip().lower()
    if not s:
        return None
    # Приводим казахские/русские кавычки и тире к пробелам
    if preserve_slash:
        # Сохраняем '/' для дробных домов («1/2», «55/6»), убирая остальную пунктуацию
        s = re.sub(r"[^\w\s/әіңғүұқөһё]", " ", s, flags=re.UNICODE)
        s = re.sub(r"\s*/\s*", "/", s)
    else:
        s = re.sub(r"[^\w\sәіңғүұқөһё]", " ", s, flags=re.UNICODE)
    s = re.sub(r"_+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s if s else None


def is_value_in_raw_string(raw_address: str, field_value: Optional[str]) -> bool:
    """Проверяет, присутствует ли значение поля непосредственно в тексте raw_address."""
    if not field_value:
        return False
    norm_raw = normalize_value(raw_address, preserve_slash=True) or ""
    norm_val = normalize_value(field_value, preserve_slash=True) or ""
    if not norm_val:
        return False
    return norm_val in norm_raw


def evaluate_predictions(
    ground_truth: List[Dict[str, Any]],
    predictions: List[Dict[str, Any]],
    verbose: bool = False,
) -> Dict[str, Any]:
    gt_by_id = {str(item["id"]): item for item in ground_truth}
    pred_by_id = {str(item["id"]): item for item in predictions}

    invariant_errors: List[str] = []
    if len(predictions) != len(ground_truth):
        invariant_errors.append(
            f"Количество записей не совпадает: ground_truth={len(ground_truth)}, predictions={len(predictions)}"
        )

    missing_ids = [rec_id for rec_id in gt_by_id if rec_id not in pred_by_id]
    if missing_ids:
        invariant_errors.append(
            f"Пропущены записи (запрещено ТЗ!): {len(missing_ids)} шт. Примеры: {missing_ids[:5]}"
        )

    field_stats: Dict[str, Dict[str, int]] = {
        f: {"correct": 0, "total": 0}
        for f in (*ADDRESS_FIELDS, *DETAIL_FIELDS, *REFERENCE_FIELDS, *EXTRA_DEFENSE_FIELDS)
    }
    enrichment_stats = {
        "district_from_db_correct": 0,
        "district_from_db_total": 0,
        "street_type_correct": 0,
        "street_type_total": 0,
    }
    substring_violations: List[str] = []
    mismatches: List[Dict[str, Any]] = []

    for rec_id, gt in gt_by_id.items():
        pred = pred_by_id.get(rec_id)
        raw_address = str(gt.get("raw_address", ""))

        if pred is None:
            # Пропущенная запись штрафуется по всем непустым полям эталона
            for f in (*ADDRESS_FIELDS, *DETAIL_FIELDS):
                if normalize_value(gt.get(f), preserve_slash=(f in ("house", "apartment"))) is not None:
                    field_stats[f]["total"] += 1
            for f in REFERENCE_FIELDS:
                gt_val = gt.get(f)
                if gt_val and is_value_in_raw_string(raw_address, str(gt_val)):
                    field_stats[f]["total"] += 1
            continue

        if str(pred.get("raw_address", "")) != raw_address:
            invariant_errors.append(f"[{rec_id}] raw_address был изменён!")

        # Проверка инварианта подстроки для street_name
        pred_street = pred.get("street_name")
        if pred_street and not is_value_in_raw_string(raw_address, str(pred_street)):
            substring_violations.append(
                f"[{rec_id}] street_name='{pred_street}' не является подстрокой raw_address='{raw_address}'"
            )

        # 1. Address (60%) & Details (25%)
        for f in (*ADDRESS_FIELDS, *DETAIL_FIELDS):
            keep_slash = f in ("house", "apartment")
            # Если в строке явно не было города/области, проверяем по эталону
            gt_norm = normalize_value(gt.get(f), preserve_slash=keep_slash)
            pred_norm = normalize_value(pred.get(f), preserve_slash=keep_slash)

            if gt_norm is None and pred_norm is None:
                continue

            field_stats[f]["total"] += 1
            if gt_norm == pred_norm:
                field_stats[f]["correct"] += 1
            else:
                mismatches.append(
                    {
                        "id": rec_id,
                        "field": f,
                        "raw_address": raw_address,
                        "expected": gt.get(f),
                        "actual": pred.get(f),
                    }
                )

        # 2. Reference fields (15%): district и living_area
        for f in REFERENCE_FIELDS:
            gt_raw_val = gt.get(f)
            pred_raw_val = pred.get(f)
            gt_norm = normalize_value(gt_raw_val)
            pred_norm = normalize_value(pred_raw_val)

            in_string = is_value_in_raw_string(raw_address, str(gt_raw_val) if gt_raw_val else None) or (
                f == "district"
                and bool(re.search(r"\b(?:район|р-н|ауданы)\b", raw_address, flags=re.IGNORECASE))
            )

            if in_string:
                # Данные есть в строке -> входят в 15% авто-метрику
                if gt_norm is None and pred_norm is None:
                    continue
                field_stats[f]["total"] += 1
                if gt_norm == pred_norm:
                    field_stats[f]["correct"] += 1
                else:
                    mismatches.append(
                        {
                            "id": rec_id,
                            "field": f"{f} (in_string)",
                            "raw_address": raw_address,
                            "expected": gt_raw_val,
                            "actual": pred_raw_val,
                        }
                    )
            else:
                # Данных в строке нет: если в эталоне есть район из БД — считаем в инженерную метрику (30%)
                if f == "district" and gt_norm is not None:
                    enrichment_stats["district_from_db_total"] += 1
                    if gt_norm == pred_norm:
                        enrichment_stats["district_from_db_correct"] += 1
                elif f == "living_area" and pred_norm is not None and gt_norm is None:
                    # Ошибочно заполнен living_area, когда его нет
                    field_stats[f]["total"] += 1
                    mismatches.append(
                        {
                            "id": rec_id,
                            "field": f,
                            "raw_address": raw_address,
                            "expected": None,
                            "actual": pred_raw_val,
                        }
                    )

        # 3. Дополнительные поля для защиты (street_type, landmark)
        for f in EXTRA_DEFENSE_FIELDS:
            gt_norm = normalize_value(gt.get(f))
            pred_norm = normalize_value(pred.get(f))
            if gt_norm is None and pred_norm is None:
                continue
            field_stats[f]["total"] += 1
            if gt_norm == pred_norm:
                field_stats[f]["correct"] += 1
            else:
                mismatches.append(
                    {
                        "id": rec_id,
                        "field": f"{f} (defense)",
                        "raw_address": raw_address,
                        "expected": gt.get(f),
                        "actual": pred.get(f),
                    }
                )
            if f == "street_type" and gt_norm is not None:
                enrichment_stats["street_type_total"] += 1
                if gt_norm == pred_norm:
                    enrichment_stats["street_type_correct"] += 1

    def calc_field_acc(f_name: str) -> float:
        st = field_stats[f_name]
        return (st["correct"] / st["total"]) if st["total"] > 0 else 1.0

    def calc_group_acc(fields: Tuple[str, ...]) -> float:
        active = [calc_field_acc(f) for f in fields if field_stats[f]["total"] > 0]
        return sum(active) / len(active) if active else 1.0

    address_score = calc_group_acc(ADDRESS_FIELDS)
    details_score = calc_group_acc(DETAIL_FIELDS)
    reference_score = calc_group_acc(REFERENCE_FIELDS)
    final_auto_score = 0.60 * address_score + 0.25 * details_score + 0.15 * reference_score

    return {
        "final_auto_score": final_auto_score,
        "address_score": address_score,
        "details_score": details_score,
        "reference_score": reference_score,
        "field_stats": field_stats,
        "enrichment_stats": enrichment_stats,
        "invariant_errors": invariant_errors,
        "substring_violations": substring_violations,
        "mismatches": mismatches,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Оценка точности парсера Jana Address по формуле ТЗ")
    parser.add_argument("--gt", required=True, help="Путь к эталонному JSON (sample_output.json / val_gt.json)")
    parser.add_argument("--pred", required=True, help="Путь к предсказанному JSON")
    parser.add_argument("--show-errors", type=int, default=15, help="Сколько несовпадений вывести")
    args = parser.parse_args()

    gt_data = json.loads(Path(args.gt).read_text(encoding="utf-8"))
    pred_data = json.loads(Path(args.pred).read_text(encoding="utf-8"))

    if isinstance(gt_data, dict):
        gt_data = gt_data.get("records") or gt_data.get("results") or []
    if isinstance(pred_data, dict):
        pred_data = pred_data.get("records") or pred_data.get("results") or []

    report = evaluate_predictions(gt_data, pred_data)

    print("=" * 72)
    print("JANA ADDRESS — ОТЧЁТ ОЦЕНКИ ПО МЕТРИКАМ ТЗ")
    print("=" * 72)
    print(f"Всего записей в эталоне: {len(gt_data)}")
    print("-" * 72)
    print(f"{'Поле':<20} | {'Верно / Всего':<15} | {'Точность':<10} | {'Группа'}")
    print("-" * 72)

    for f in ADDRESS_FIELDS:
        st = report["field_stats"][f]
        acc = (st["correct"] / st["total"] * 100) if st["total"] else 100.0
        print(f"{f:<20} | {st['correct']:>5} / {st['total']:<7} | {acc:>7.2f}%   | Адрес (60%)")

    for f in DETAIL_FIELDS:
        st = report["field_stats"][f]
        acc = (st["correct"] / st["total"] * 100) if st["total"] else 100.0
        print(f"{f:<20} | {st['correct']:>5} / {st['total']:<7} | {acc:>7.2f}%   | Детали (25%)")

    for f in REFERENCE_FIELDS:
        st = report["field_stats"][f]
        acc = (st["correct"] / st["total"] * 100) if st["total"] else 100.0
        print(f"{f:<20} | {st['correct']:>5} / {st['total']:<7} | {acc:>7.2f}%   | Справочные в строке (15%)")

    print("-" * 72)
    for f in EXTRA_DEFENSE_FIELDS:
        st = report["field_stats"][f]
        acc = (st["correct"] / st["total"] * 100) if st["total"] else 100.0
        print(f"{f:<20} | {st['correct']:>5} / {st['total']:<7} | {acc:>7.2f}%   | На защите (30%)")

    enr = report["enrichment_stats"]
    if enr["district_from_db_total"] > 0:
        d_acc = enr["district_from_db_correct"] / enr["district_from_db_total"] * 100
        print(
            f"{'district (из БД)':<20} | {enr['district_from_db_correct']:>5} / {enr['district_from_db_total']:<7} | {d_acc:>7.2f}%   | Гео-обогащение (30%)"
        )

    print("=" * 72)
    print(f"1. Точность адреса (вес 60%):            {report['address_score'] * 100:6.2f}%")
    print(f"2. Точность деталей (вес 25%):           {report['details_score'] * 100:6.2f}%")
    print(f"3. Справочные поля в строке (вес 15%):   {report['reference_score'] * 100:6.2f}%")
    print("-" * 72)
    print(f"ИТОГОВЫЙ СКОР АВТО-МЕТРИКИ:              {report['final_auto_score'] * 100:6.2f}%")
    print("=" * 72)

    if report["invariant_errors"]:
        print("\n[!] НАРУШЕНИЯ ИНВАРИАНТОВ ТЗ:")
        for err in report["invariant_errors"]:
            print(f"  - {err}")

    if report["substring_violations"]:
        print("\n[!] НАРУШЕНИЯ ПРАВИЛА ПОДСТРОКИ (street_name):")
        for v in report["substring_violations"][:10]:
            print(f"  - {v}")

    if report["mismatches"] and args.show_errors > 0:
        print(f"\nПримеры расхождений (показано до {args.show_errors} из {len(report['mismatches'])}):")
        for m in report["mismatches"][: args.show_errors]:
            print(
                f"  [{m['id']}] поле={m['field']}: ожидалось={m['expected']!r}, получено={m['actual']!r} | raw='{m['raw_address']}'"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
