#!/usr/bin/env python3
"""
scripts/build_gazetteer.py — Сборка локального гео-справочника Казахстана (kaz_geo.sqlite)
на базе справочника КАТО (области, города, районы, нас. пункты РК) и данных OpenStreetMap
(городские районы, улицы, проспекты, переулки, микрорайоны, кварталы и адресные точки домов).

Поддерживает:
  1. Базовую предрассчитанную сборку (КАТО всех 20 регионов РК + районы и улицы/микрорайоны городов РК).
  2. Дополнительный импорт из CSV справочника КАТО (--kato-csv) и выгрузки OSM GeoJSON/JSONL (--osm-jsonl).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def normalize_lookup_key(text: str) -> str:
    """Нормализует название для быстрого и нечёткого поиска в справочнике."""
    s = text.lower().strip()
    s = s.replace("ё", "е")
    # Убираем точки, дефисы и кавычки
    s = re.sub(r"[^\w\sәіңғүұқөһ]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# 1. КАТО: Все области и города республиканского значения + основные города и посёлки РК
KATO_SETTLEMENTS: List[Dict[str, Any]] = [
    # Города республиканского значения
    {"city": "Алматы", "province": "Алматы", "district": None, "type": "город", "aliases": ["алматы", "алматы қаласы", "г алматы", "город алматы", "almaty"]},
    {"city": "Астана", "province": "Астана", "district": None, "type": "город", "aliases": ["астана", "астана қаласы", "нур султан", "нур-султан", "г астана", "город астана", "astana"]},
    {"city": "Шымкент", "province": "Шымкент", "district": None, "type": "город", "aliases": ["шымкент", "шымкент қаласы", "чимкент", "г шымкент", "город шымкент", "shymkent"]},
    # Областные центры и крупные города
    {"city": "Караганда", "province": "Карагандинская область", "district": None, "type": "город", "aliases": ["караганда", "қарағанды", "қарағанды қаласы", "караганда қаласы"]},
    {"city": "Темиртау", "province": "Карагандинская область", "district": None, "type": "город", "aliases": ["темиртау", "теміртау"]},
    {"city": "Актобе", "province": "Актюбинская область", "district": None, "type": "город", "aliases": ["актобе", "ақтөбе", "ақтөбе қаласы", "актюбинск"]},
    {"city": "Атырау", "province": "Атырауская область", "district": None, "type": "город", "aliases": ["атырау", "атырау қаласы", "гурьев"]},
    {"city": "Актау", "province": "Мангистауская область", "district": None, "type": "город", "aliases": ["актау", "ақтау", "ақтау қаласы"]},
    {"city": "Жанаозен", "province": "Мангистауская область", "district": None, "type": "город", "aliases": ["жанаозен", "жаңаөзен"]},
    {"city": "Павлодар", "province": "Павлодарская область", "district": None, "type": "город", "aliases": ["павлодар", "павлодар қаласы"]},
    {"city": "Экибастуз", "province": "Павлодарская область", "district": None, "type": "город", "aliases": ["экибастуз", "екібастұз"]},
    {"city": "Усть-Каменогорск", "province": "Восточно-Казахстанская область", "district": None, "type": "город", "aliases": ["усть каменогорск", "усть-каменогорск", "өскемен", "оскемен"]},
    {"city": "Семей", "province": "Абайская область", "district": None, "type": "город", "aliases": ["семей", "семей қаласы", "семипалатинск"]},
    {"city": "Тараз", "province": "Жамбылская область", "district": None, "type": "город", "aliases": ["тараз", "тараз қаласы", "джамбул"]},
    {"city": "Уральск", "province": "Западно-Казахстанская область", "district": None, "type": "город", "aliases": ["уральск", "орал", "орал қаласы"]},
    {"city": "Костанай", "province": "Костанайская область", "district": None, "type": "город", "aliases": ["костанай", "қостанай", "қостанай қаласы", "кустанай"]},
    {"city": "Рудный", "province": "Костанайская область", "district": None, "type": "город", "aliases": ["рудный", "рудный қаласы"]},
    {"city": "Кызылорда", "province": "Кызылординская область", "district": None, "type": "город", "aliases": ["кызылорда", "қызылорда", "қызылорда қаласы"]},
    {"city": "Петропавловск", "province": "Северо-Казахстанская область", "district": None, "type": "город", "aliases": ["петропавловск", "петропавл", "петропавл қаласы"]},
    {"city": "Кокшетау", "province": "Акмолинская область", "district": None, "type": "город", "aliases": ["кокшетау", "көкшетау", "көкшетау қаласы"]},
    {"city": "Косшы", "province": "Акмолинская область", "district": None, "type": "город", "aliases": ["косшы", "қосшы"]},
    {"city": "Талдыкорган", "province": "Жетысуская область", "district": None, "type": "город", "aliases": ["талдыкорган", "талдықорған", "талдықорған қаласы"]},
    {"city": "Жезказган", "province": "Улытауская область", "district": None, "type": "город", "aliases": ["жезказган", "жезқазған", "жезқазған қаласы"]},
    {"city": "Сатпаев", "province": "Улытауская область", "district": None, "type": "город", "aliases": ["сатпаев", "сәтбаев"]},
    {"city": "Туркестан", "province": "Туркестанская область", "district": None, "type": "город", "aliases": ["туркестан", "түркістан", "түркістан қаласы"]},
    {"city": "Конаев", "province": "Алматинская область", "district": None, "type": "город", "aliases": ["конаев", "қонаев", "капшагай", "капчагай"]},
    {"city": "Каскелен", "province": "Алматинская область", "district": "Карасайский", "type": "город", "aliases": ["каскелен", "қаскелең"]},
    {"city": "Талгар", "province": "Алматинская область", "district": "Талгарский", "type": "город", "aliases": ["талгар", "талғар"]},
    {"city": "Есик", "province": "Алматинская область", "district": "Енбекшиказахский", "type": "город", "aliases": ["есик", "есік", "иссык"]},
    # Пригороды и посёлки (КАТО)
    {"city": "Боралдай", "province": "Алматинская область", "district": "Илийский", "type": "поселок", "aliases": ["боралдай", "бурундай", "пос боралдай", "п боралдай"]},
    {"city": "Отеген батыра", "province": "Алматинская область", "district": "Илийский", "type": "поселок", "aliases": ["отеген батыра", "отеген батыр", "грэс"]},
    {"city": "Бесагаш", "province": "Алматинская область", "district": "Талгарский", "type": "село", "aliases": ["бесагаш", "бесағаш"]},
    {"city": "Иргели", "province": "Алматинская область", "district": "Карасайский", "type": "село", "aliases": ["иргели", "іргелі"]},
    {"city": "Абай", "province": "Алматинская область", "district": "Карасайский", "type": "село", "aliases": ["село абай", "пос абай"]},
]


# 2. Административные районы городов (КАТО + OSM boundary=administrative)
URBAN_DISTRICTS: List[Dict[str, Any]] = [
    # Алматы (8 районов)
    {"district": "Алатауский", "city": "Алматы", "province": "Алматы", "aliases": ["алатауский", "алатау", "алатау ауданы"]},
    {"district": "Алмалинский", "city": "Алматы", "province": "Алматы", "aliases": ["алмалинский", "алмалы", "алмалы ауданы"]},
    {"district": "Ауэзовский", "city": "Алматы", "province": "Алматы", "aliases": ["ауэзовский", "ауезовский", "әуезов", "әуезов ауданы"]},
    {"district": "Бостандыкский", "city": "Алматы", "province": "Алматы", "aliases": ["бостандыкский", "бостандық", "бостандық ауданы"]},
    {"district": "Жетысуский", "city": "Алматы", "province": "Алматы", "aliases": ["жетысуский", "жетісу", "жетісу ауданы"]},
    {"district": "Медеуский", "city": "Алматы", "province": "Алматы", "aliases": ["медеуский", "медеу", "медеу ауданы"]},
    {"district": "Наурызбайский", "city": "Алматы", "province": "Алматы", "aliases": ["наурызбайский", "наурызбай", "наурызбай ауданы"]},
    {"district": "Турксибский", "city": "Алматы", "province": "Алматы", "aliases": ["турксибский", "түрксіб", "түрксіб ауданы"]},
    # Астана (6 районов)
    {"district": "Алматы", "city": "Астана", "province": "Астана", "aliases": ["район алматы", "алматы ауданы", "алматинский"]},
    {"district": "Байконыр", "city": "Астана", "province": "Астана", "aliases": ["байконыр", "байконур", "байқоңыр", "байқоңыр ауданы"]},
    {"district": "Есиль", "city": "Астана", "province": "Астана", "aliases": ["есиль", "есильский", "есіл", "есіл ауданы"]},
    {"district": "Нура", "city": "Астана", "province": "Астана", "aliases": ["нура", "нуринский", "нұра", "нұра ауданы"]},
    {"district": "Сарыарка", "city": "Астана", "province": "Астана", "aliases": ["сарыарка", "сарыаркинский", "сарыарқа", "сарыарқа ауданы"]},
    {"district": "Сарайшык", "city": "Астана", "province": "Астана", "aliases": ["сарайшык", "сарайшық", "сарайшық ауданы"]},
    # Шымкент (5 районов)
    {"district": "Абайский", "city": "Шымкент", "province": "Шымкент", "aliases": ["абайский", "абай ауданы"]},
    {"district": "Аль-Фарабийский", "city": "Шымкент", "province": "Шымкент", "aliases": ["аль фарабийский", "аль-фарабийский", "әл фараби", "әл-фараби ауданы"]},
    {"district": "Енбекшинский", "city": "Шымкент", "province": "Шымкент", "aliases": ["енбекшинский", "еңбекші", "еңбекші ауданы"]},
    {"district": "Каратауский", "city": "Шымкент", "province": "Шымкент", "aliases": ["каратауский", "қаратау", "қаратау ауданы"]},
    {"district": "Туран", "city": "Шымкент", "province": "Шымкент", "aliases": ["район туран", "тұран ауданы"]},
    # Караганда
    {"district": "Казыбек би", "city": "Караганда", "province": "Карагандинская область", "aliases": ["казыбек би", "район имени казыбек би", "қазыбек би ауданы"]},
    {"district": "Алихана Бокейхана", "city": "Караганда", "province": "Карагандинская область", "aliases": ["алихана бокейхана", "октябрьский", "әлихан бөкейхан"]},
    # Актобе
    {"district": "Алматы", "city": "Актобе", "province": "Актюбинская область", "aliases": ["район алматы актобе"]},
    {"district": "Астана", "city": "Актобе", "province": "Актюбинская область", "aliases": ["район астана актобе"]},
    # Сельские районы пригородов
    {"district": "Илийский", "city": "Боралдай", "province": "Алматинская область", "aliases": ["илийский", "іле", "іле ауданы"]},
    {"district": "Карасайский", "city": "Каскелен", "province": "Алматинская область", "aliases": ["карасайский", "қарасай", "қарасай ауданы"]},
    {"district": "Талгарский", "city": "Талгар", "province": "Алматинская область", "aliases": ["талгарский", "талғар ауданы"]},
]


# 3. Улицы, проспекты, переулки, микрорайоны и кварталы (OSM + КАТО)
STREETS_AND_MICRODISTRICTS: List[Dict[str, Any]] = [
    # Микрорайоны и кварталы Алматы
    {"name": "Аксай 1", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Ауэзовский", "aliases": ["аксай 1", "аксай-1", "1 мкр аксай"]},
    {"name": "Аксай 2", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Ауэзовский", "aliases": ["аксай 2", "аксай-2"]},
    {"name": "Аксай 3", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Ауэзовский", "aliases": ["аксай 3", "аксай-3"]},
    {"name": "Аксай 3а", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Ауэзовский", "aliases": ["аксай 3а", "аксай-3а", "аксай 3 а"]},
    {"name": "Аксай 3б", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Ауэзовский", "aliases": ["аксай 3б", "аксай-3б"]},
    {"name": "Аксай 4", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Ауэзовский", "aliases": ["аксай 4", "аксай-4"]},
    {"name": "Аксай 5", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Ауэзовский", "aliases": ["аксай 5", "аксай-5"]},
    {"name": "Жетысу-1", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Ауэзовский", "aliases": ["жетысу 1", "жетысу-1", "жетісу 1"]},
    {"name": "Жетысу-2", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Ауэзовский", "aliases": ["жетысу 2", "жетысу-2", "жетісу 2"]},
    {"name": "Жетысу-3", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Ауэзовский", "aliases": ["жетысу 3", "жетысу-3", "жетісу 3"]},
    {"name": "Жетысу-4", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Ауэзовский", "aliases": ["жетысу 4", "жетысу-4"]},
    {"name": "Мамыр-1", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Ауэзовский", "aliases": ["мамыр 1", "мамыр-1"]},
    {"name": "Мамыр-4", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Ауэзовский", "aliases": ["мамыр 4", "мамыр-4"]},
    {"name": "Орбита-1", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Бостандыкский", "aliases": ["орбита 1", "орбита-1"]},
    {"name": "Орбита-2", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Бостандыкский", "aliases": ["орбита 2", "орбита-2"]},
    {"name": "Орбита-3", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Бостандыкский", "aliases": ["орбита 3", "орбита-3"]},
    {"name": "Орбита-4", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Бостандыкский", "aliases": ["орбита 4", "орбита-4"]},
    {"name": "Самал-1", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Медеуский", "aliases": ["самал 1", "самал-1"]},
    {"name": "Самал-2", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Медеуский", "aliases": ["самал 2", "самал-2"]},
    {"name": "Самал-3", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Медеуский", "aliases": ["самал 3", "самал-3"]},
    {"name": "Коктем-1", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Бостандыкский", "aliases": ["коктем 1", "коктем-1", "көктем 1"]},
    {"name": "Коктем-2", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Бостандыкский", "aliases": ["коктем 2", "коктем-2"]},
    {"name": "Коктем-3", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Бостандыкский", "aliases": ["коктем 3", "коктем-3"]},
    {"name": "Айнабулак-1", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Жетысуский", "aliases": ["айнабулак 1", "айнабулак-1"]},
    {"name": "Айнабулак-2", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Жетысуский", "aliases": ["айнабулак 2", "айнабулак-2"]},
    {"name": "Айнабулак-3", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Жетысуский", "aliases": ["айнабулак 3", "айнабулак-3"]},
    {"name": "Айнабулак-4", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Жетысуский", "aliases": ["айнабулак 4", "айнабулак-4"]},
    {"name": "Кулагер", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Жетысуский", "aliases": ["кулагер", "құлагер"]},
    {"name": "Жулдыз-1", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Турксибский", "aliases": ["жулдыз 1", "жулдыз-1", "жұлдыз 1"]},
    {"name": "Жулдыз-2", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Турксибский", "aliases": ["жулдыз 2", "жулдыз-2"]},
    {"name": "Акбулак", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Алатауский", "aliases": ["акбулак", "ақбұлақ"]},
    {"name": "Зердели", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Алатауский", "aliases": ["зердели", "зерделі", "алгабас 6"]},
    {"name": "Шугыла", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Наурызбайский", "aliases": ["шугыла", "шұғыла"]},
    {"name": "Калкаман-2", "street_type": "микрорайон", "city": "Алматы", "province": "Алматы", "district": "Наурызбайский", "aliases": ["калкаман 2", "калкаман-2", "қалқаман 2"]},

    # Улицы, проспекты и переулки Алматы
    {"name": "Курильская", "street_type": "улица", "city": "Алматы", "province": "Алматы", "district": "Жетысуский", "aliases": ["курильская"]},
    {"name": "Рыбинский", "street_type": "переулок", "city": "Алматы", "province": "Алматы", "district": "Турксибский", "aliases": ["рыбинский"]},
    {"name": "Жуалы", "street_type": "улица", "city": "Алматы", "province": "Алматы", "district": "Алатауский", "aliases": ["жуалы"]},
    {"name": "Казыбек би", "street_type": "улица", "city": "Алматы", "province": "Алматы", "district": "Алмалинский", "aliases": ["казыбек би", "казибек би", "қазыбек би"]},
    {"name": "Толе би", "street_type": "улица", "city": "Алматы", "province": "Алматы", "district": "Алмалинский", "aliases": ["толе би", "толеби", "төле би"]},
    {"name": "Айтеке би", "street_type": "улица", "city": "Алматы", "province": "Алматы", "district": "Алмалинский", "aliases": ["айтеке би", "әйтеке би"]},
    {"name": "Розыбакиева", "street_type": "улица", "city": "Алматы", "province": "Алматы", "district": "Бостандыкский", "aliases": ["розыбакиева", "розыбакиев"]},
    {"name": "Абая", "street_type": "проспект", "city": "Алматы", "province": "Алматы", "district": "Бостандыкский", "aliases": ["абая", "абай"]},
    {"name": "Аль-Фараби", "street_type": "проспект", "city": "Алматы", "province": "Алматы", "district": "Бостандыкский", "aliases": ["аль фараби", "аль-фараби", "әл-фараби"]},
    {"name": "Сатпаева", "street_type": "улица", "city": "Алматы", "province": "Алматы", "district": "Бостандыкский", "aliases": ["сатпаева", "сәтбаев"]},
    {"name": "Тимирязева", "street_type": "улица", "city": "Алматы", "province": "Алматы", "district": "Бостандыкский", "aliases": ["тимирязева"]},
    {"name": "Жандосова", "street_type": "улица", "city": "Алматы", "province": "Алматы", "district": "Бостандыкский", "aliases": ["жандосова"]},
    {"name": "Ауэзова", "street_type": "улица", "city": "Алматы", "province": "Алматы", "district": "Бостандыкский", "aliases": ["ауэзова", "ауезова"]},
    {"name": "Манаса", "street_type": "улица", "city": "Алматы", "province": "Алматы", "district": "Бостандыкский", "aliases": ["манаса"]},
    {"name": "Байтурсынова", "street_type": "улица", "city": "Алматы", "province": "Алматы", "district": "Алмалинский", "aliases": ["байтурсынова", "ахмета байтурсынова"]},
    {"name": "Сейфуллина", "street_type": "проспект", "city": "Алматы", "province": "Алматы", "district": "Алмалинский", "aliases": ["сейфуллина"]},
    {"name": "Назарбаева", "street_type": "проспект", "city": "Алматы", "province": "Алматы", "district": "Медеуский", "aliases": ["назарбаева", "фурманова"]},
    {"name": "Достык", "street_type": "проспект", "city": "Алматы", "province": "Алматы", "district": "Медеуский", "aliases": ["достык", "достық"]},
    {"name": "Кунаева", "street_type": "улица", "city": "Алматы", "province": "Алматы", "district": "Медеуский", "aliases": ["кунаева", "конаева", "қонаев"]},
    {"name": "Гоголя", "street_type": "улица", "city": "Алматы", "province": "Алматы", "district": "Алмалинский", "aliases": ["гоголя"]},
    {"name": "Макатаева", "street_type": "улица", "city": "Алматы", "province": "Алматы", "district": "Алмалинский", "aliases": ["макатаева", "мақатаев"]},
    {"name": "Райымбека", "street_type": "проспект", "city": "Алматы", "province": "Алматы", "district": "Алмалинский", "aliases": ["райымбека", "раимбека"]},
    {"name": "Саина", "street_type": "улица", "city": "Алматы", "province": "Алматы", "district": "Ауэзовский", "aliases": ["саина"]},
    {"name": "Момышулы", "street_type": "улица", "city": "Алматы", "province": "Алматы", "district": "Ауэзовский", "aliases": ["момышулы", "бауыржана момышулы"]},
    {"name": "Жубанова", "street_type": "улица", "city": "Алматы", "province": "Алматы", "district": "Ауэзовский", "aliases": ["жубанова"]},
    {"name": "Утеген батыра", "street_type": "улица", "city": "Алматы", "province": "Алматы", "district": "Ауэзовский", "aliases": ["утеген батыра", "отеген батыра"]},
    {"name": "Суюнбая", "street_type": "проспект", "city": "Алматы", "province": "Алматы", "district": "Турксибский", "aliases": ["суюнбая", "сүйінбай"]},
    {"name": "Майлина", "street_type": "улица", "city": "Алматы", "province": "Алматы", "district": "Турксибский", "aliases": ["майлина"]},

    # Астана
    {"name": "Туран", "street_type": "проспект", "city": "Астана", "province": "Астана", "district": "Нура", "aliases": ["туран", "тұран"]},
    {"name": "Кабанбай батыра", "street_type": "проспект", "city": "Астана", "province": "Астана", "district": "Есиль", "aliases": ["кабанбай батыра", "қабанбай батыр"]},
    {"name": "Мангилик Ел", "street_type": "проспект", "city": "Астана", "province": "Астана", "district": "Есиль", "aliases": ["мангилик ел", "мәңгілік ел"]},
    {"name": "Сыганак", "street_type": "улица", "city": "Астана", "province": "Астана", "district": "Есиль", "aliases": ["сыганак", "сығанақ"]},
    {"name": "Сауран", "street_type": "улица", "city": "Астана", "province": "Астана", "district": "Есиль", "aliases": ["сауран"]},
    {"name": "Сарайшык", "street_type": "улица", "city": "Астана", "province": "Астана", "district": "Есиль", "aliases": ["сарайшык", "сарайшық"]},
    {"name": "Достык", "street_type": "улица", "city": "Астана", "province": "Астана", "district": "Есиль", "aliases": ["достык астана"]},
    {"name": "Кунаева", "street_type": "улица", "city": "Астана", "province": "Астана", "district": "Есиль", "aliases": ["кунаева астана", "конаева астана"]},
    {"name": "Туркестан", "street_type": "улица", "city": "Астана", "province": "Астана", "district": "Есиль", "aliases": ["туркестан", "түркістан"]},
    {"name": "Акмешит", "street_type": "улица", "city": "Астана", "province": "Астана", "district": "Есиль", "aliases": ["акмешит", "ақмешіт"]},
    {"name": "Керей, Жанибек хандар", "street_type": "улица", "city": "Астана", "province": "Астана", "district": "Есиль", "aliases": ["керей жанибек хандар", "керей и жанибек ханов"]},
    {"name": "Алихана Бокейхана", "street_type": "улица", "city": "Астана", "province": "Астана", "district": "Есиль", "aliases": ["бокейхана", "алихана бокейхана"]},
    {"name": "Улы Дала", "street_type": "проспект", "city": "Астана", "province": "Астана", "district": "Есиль", "aliases": ["улы дала", "ұлы дала"]},
    {"name": "Тауелсиздик", "street_type": "проспект", "city": "Астана", "province": "Астана", "district": "Алматы", "aliases": ["тауелсиздик", "тәуелсіздік"]},
    {"name": "Бауыржана Момышулы", "street_type": "проспект", "city": "Астана", "province": "Астана", "district": "Алматы", "aliases": ["момышулы астана", "бауыржана момышулы"]},
    {"name": "Кошкарбаева", "street_type": "проспект", "city": "Астана", "province": "Астана", "district": "Алматы", "aliases": ["кошкарбаева", "рахимжана кошкарбаева"]},
    {"name": "Нажимеденова", "street_type": "улица", "city": "Астана", "province": "Астана", "district": "Сарайшык", "aliases": ["нажимеденова", "жумекена нажимеденова"]},
    {"name": "Байтурсынова", "street_type": "улица", "city": "Астана", "province": "Астана", "district": "Сарайшык", "aliases": ["байтурсынова астана"]},
    {"name": "Республики", "street_type": "проспект", "city": "Астана", "province": "Астана", "district": "Сарыарка", "aliases": ["республики", "республика"]},
    {"name": "Богенбай батыра", "street_type": "проспект", "city": "Астана", "province": "Астана", "district": "Сарыарка", "aliases": ["богенбай батыра", "бөгенбай батыр"]},
    {"name": "Сарыарка", "street_type": "проспект", "city": "Астана", "province": "Астана", "district": "Сарыарка", "aliases": ["сарыарка", "сарыарқа"]},
    {"name": "Кенесары", "street_type": "улица", "city": "Астана", "province": "Астана", "district": "Сарыарка", "aliases": ["кенесары"]},
    {"name": "Бейбитшилик", "street_type": "улица", "city": "Астана", "province": "Астана", "district": "Сарыарка", "aliases": ["бейбитшилик", "бейбітшілік"]},

    # Караганда
    {"name": "66", "street_type": "квартал", "city": "Караганда", "province": "Карагандинская область", "district": "Казыбек би", "aliases": ["66", "66 квартал", "66квартал", "квартал 66"]},
    {"name": "Бухар-Жырау", "street_type": "проспект", "city": "Караганда", "province": "Карагандинская область", "district": "Казыбек би", "aliases": ["бухар жырау", "бухар-жырау", "бұқар жырау"]},
    {"name": "Нуркена Абдирова", "street_type": "проспект", "city": "Караганда", "province": "Карагандинская область", "district": "Казыбек би", "aliases": ["абдирова", "нуркена абдирова"]},
    {"name": "Ерубаева", "street_type": "улица", "city": "Караганда", "province": "Карагандинская область", "district": "Казыбек би", "aliases": ["ерубаева"]},
    {"name": "Степной-1", "street_type": "микрорайон", "city": "Караганда", "province": "Карагандинская область", "district": "Казыбек би", "aliases": ["степной 1", "степной-1"]},
    {"name": "Степной-2", "street_type": "микрорайон", "city": "Караганда", "province": "Карагандинская область", "district": "Казыбек би", "aliases": ["степной 2", "степной-2"]},
    {"name": "Степной-3", "street_type": "микрорайон", "city": "Караганда", "province": "Карагандинская область", "district": "Казыбек би", "aliases": ["степной 3", "степной-3"]},
    {"name": "Степной-4", "street_type": "микрорайон", "city": "Караганда", "province": "Карагандинская область", "district": "Казыбек би", "aliases": ["степной 4", "степной-4"]},
    {"name": "Гульдер-1", "street_type": "микрорайон", "city": "Караганда", "province": "Карагандинская область", "district": "Казыбек би", "aliases": ["гульдер 1", "гульдер-1"]},
    {"name": "Орбита-1", "street_type": "микрорайон", "city": "Караганда", "province": "Карагандинская область", "district": "Казыбек би", "aliases": ["орбита 1 караганда"]},
    {"name": "Зелинского", "street_type": "улица", "city": "Караганда", "province": "Карагандинская область", "district": "Алихана Бокейхана", "aliases": ["зелинского"]},

    # Актобе
    {"name": "Нурсити 2", "street_type": "микрорайон", "city": "Актобе", "province": "Актюбинская область", "district": "Алматы", "aliases": ["нурсити 2", "нур сити 2", "нур актобе 2"]},
    {"name": "Нурсити", "street_type": "микрорайон", "city": "Актобе", "province": "Актюбинская область", "district": "Алматы", "aliases": ["нурсити", "нур актобе"]},
    {"name": "Батыс-2", "street_type": "микрорайон", "city": "Актобе", "province": "Актюбинская область", "district": "Астана", "aliases": ["батыс 2", "батыс-2"]},
    {"name": "Абулхаир хана", "street_type": "проспект", "city": "Актобе", "province": "Актюбинская область", "district": "Астана", "aliases": ["абулхаир хана", "әбілқайыр хан"]},
    {"name": "Алии Молдагуловой", "street_type": "проспект", "city": "Актобе", "province": "Актюбинская область", "district": "Астана", "aliases": ["молдагуловой", "алии молдагуловой"]},
    {"name": "Санкибай батыра", "street_type": "проспект", "city": "Актобе", "province": "Актюбинская область", "district": "Астана", "aliases": ["санкибай батыра"]},

    # Атырау
    {"name": "Кулманова", "street_type": "улица", "city": "Атырау", "province": "Атырауская область", "district": None, "aliases": ["кулманова", "жаскайрата кулманова"]},
    {"name": "Сатпаева", "street_type": "проспект", "city": "Атырау", "province": "Атырауская область", "district": None, "aliases": ["сатпаева атырау"]},
    {"name": "Азаттык", "street_type": "проспект", "city": "Атырау", "province": "Атырауская область", "district": None, "aliases": ["азаттык", "азаттық"]},
    {"name": "Нурсая", "street_type": "микрорайон", "city": "Атырау", "province": "Атырауская область", "district": None, "aliases": ["нурсая", "нұрсая"]},
    {"name": "Авангард-3", "street_type": "микрорайон", "city": "Атырау", "province": "Атырауская область", "district": None, "aliases": ["авангард 3", "авангард-3"]},

    # Шымкент
    {"name": "Тауке хана", "street_type": "проспект", "city": "Шымкент", "province": "Шымкент", "district": "Аль-Фарабийский", "aliases": ["тауке хана", "тәуке хан"]},
    {"name": "Нурсат", "street_type": "микрорайон", "city": "Шымкент", "province": "Шымкент", "district": "Каратауский", "aliases": ["нурсат", "нұрсәт"]},
    {"name": "Кунаева", "street_type": "проспект", "city": "Шымкент", "province": "Шымкент", "district": "Аль-Фарабийский", "aliases": ["кунаева шымкент", "конаева шымкент"]},
    {"name": "Байдибек би", "street_type": "проспект", "city": "Шымкент", "province": "Шымкент", "district": "Каратауский", "aliases": ["байдибек би", "бәйдібек би"]},
    {"name": "Республики", "street_type": "проспект", "city": "Шымкент", "province": "Шымкент", "district": "Абайский", "aliases": ["республики шымкент"]},

    # Боралдай (Алматинская область)
    {"name": "Абая", "street_type": "улица", "city": "Боралдай", "province": "Алматинская область", "district": "Илийский", "aliases": ["абая боралдай"]},

    # Числовые микрорайоны Алматы (1..12 -> Ауэзовский район) и Актау (1..35)
    *[
        {
            "name": str(m_num),
            "street_type": "микрорайон",
            "city": "Алматы",
            "province": "Алматы",
            "district": "Ауэзовский",
            "aliases": [str(m_num), f"{m_num} мкр", f"мкр {m_num}"],
        }
        for m_num in range(1, 13)
    ],
    *[
        {
            "name": str(m_num),
            "street_type": "микрорайон",
            "city": "Актау",
            "province": "Мангистауская область",
            "district": None,
            "aliases": [str(m_num), f"{m_num} мкр", f"мкр {m_num}"],
        }
        for m_num in range(1, 36)
    ],
]


# 4. Точечные привязки домов (когда длинный проспект/улица пересекает несколько районов)
BUILDING_DISTRICTS: List[Dict[str, str]] = [
    {"city": "Алматы", "street_norm": "аксай 3а", "house_norm": "59", "district": "Ауэзовский"},
    {"city": "Алматы", "street_norm": "аксай 4", "house_norm": "104", "district": "Ауэзовский"},
    {"city": "Алматы", "street_norm": "курильская", "house_norm": "9", "district": "Жетысуский"},
    {"city": "Алматы", "street_norm": "жуалы", "house_norm": "19", "district": "Алатауский"},
    {"city": "Алматы", "street_norm": "орбита 3", "house_norm": "12а", "district": "Бостандыкский"},
    {"city": "Алматы", "street_norm": "казыбек би", "house_norm": "117/1", "district": "Алмалинский"},
    {"city": "Алматы", "street_norm": "толе би", "house_norm": "286/4", "district": "Алмалинский"},
    {"city": "Алматы", "street_norm": "толе би", "house_norm": "55", "district": "Алмалинский"},
    {"city": "Алматы", "street_norm": "толе би", "house_norm": "15", "district": "Медеуский"},
    {"city": "Алматы", "street_norm": "толе би", "house_norm": "295", "district": "Ауэзовский"},
    {"city": "Алматы", "street_norm": "абая", "house_norm": "10", "district": "Медеуский"},
    {"city": "Алматы", "street_norm": "абая", "house_norm": "50", "district": "Алмалинский"},
    {"city": "Алматы", "street_norm": "абая", "house_norm": "150", "district": "Бостандыкский"},
    {"city": "Алматы", "street_norm": "райымбека", "house_norm": "50", "district": "Медеуский"},
    {"city": "Алматы", "street_norm": "райымбека", "house_norm": "165", "district": "Жетысуский"},
    {"city": "Алматы", "street_norm": "райымбека", "house_norm": "250", "district": "Алмалинский"},
    {"city": "Алматы", "street_norm": "райымбека", "house_norm": "400", "district": "Ауэзовский"},
    {"city": "Алматы", "street_norm": "райымбека", "house_norm": "505", "district": "Алатауский"},
    {"city": "Алматы", "street_norm": "розыбакиева", "house_norm": "77", "district": "Алмалинский"},
    {"city": "Алматы", "street_norm": "розыбакиева", "house_norm": "247а корпус 3", "district": "Бостандыкский"},
    {"city": "Алматы", "street_norm": "розыбакиева", "house_norm": "289", "district": "Бостандыкский"},
    {"city": "Алматы", "street_norm": "самал 2", "house_norm": "58", "district": "Медеуский"},
    {"city": "Алматы", "street_norm": "жетысу 2", "house_norm": "41", "district": "Ауэзовский"},
    {"city": "Астана", "street_norm": "туран", "house_norm": "18", "district": "Есиль"},
    {"city": "Астана", "street_norm": "туран", "house_norm": "37", "district": "Нура"},
    {"city": "Астана", "street_norm": "туран", "house_norm": "55/6", "district": "Нура"},
    {"city": "Астана", "street_norm": "кабанбай батыра", "house_norm": "6", "district": "Сарыарка"},
    {"city": "Астана", "street_norm": "кабанбай батыра", "house_norm": "15", "district": "Есиль"},
    {"city": "Астана", "street_norm": "кабанбай батыра", "house_norm": "53", "district": "Нура"},
    {"city": "Астана", "street_norm": "республики", "house_norm": "15", "district": "Сарыарка"},
    {"city": "Астана", "street_norm": "республики", "house_norm": "24", "district": "Байконыр"},
    {"city": "Астана", "street_norm": "сыганак", "house_norm": "18/3", "district": "Есиль"},
    {"city": "Астана", "street_norm": "сауран", "house_norm": "3/1", "district": "Есиль"},
    {"city": "Астана", "street_norm": "богенбай батыра", "house_norm": "54", "district": "Сарыарка"},
    {"city": "Караганда", "street_norm": "66", "house_norm": "12", "district": "Казыбек би"},
    {"city": "Актобе", "street_norm": "нурсити 2", "house_norm": "11", "district": "Алматы"},
    {"city": "Шымкент", "street_norm": "тауке хана", "house_norm": "43а", "district": "Аль-Фарабийский"},
    {"city": "Шымкент", "street_norm": "нурсат", "house_norm": "124", "district": "Каратауский"},
]


def build_sqlite_database(
    db_path: Path,
    kato_csv: Optional[Path] = None,
    osm_jsonl: Optional[Path] = None,
    kato_osm_cache: Optional[Path] = None,
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.executescript(
        """
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;

        CREATE TABLE settlements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL,
            province TEXT NOT NULL,
            district TEXT,
            settlement_type TEXT NOT NULL,
            alias_norm TEXT NOT NULL
        );
        CREATE INDEX idx_settlements_alias ON settlements(alias_norm);

        CREATE TABLE urban_districts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            district TEXT NOT NULL,
            city TEXT NOT NULL,
            province TEXT NOT NULL,
            alias_norm TEXT NOT NULL
        );
        CREATE INDEX idx_urban_districts_alias ON urban_districts(alias_norm);

        CREATE TABLE streets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_canonical TEXT NOT NULL,
            name_norm TEXT NOT NULL,
            street_type TEXT,
            city TEXT NOT NULL,
            province TEXT NOT NULL,
            default_district TEXT,
            source TEXT NOT NULL DEFAULT 'KATO+OSM'
        );
        CREATE INDEX idx_streets_name_norm ON streets(name_norm);
        CREATE INDEX idx_streets_city_name ON streets(city, name_norm);

        CREATE TABLE buildings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL,
            street_norm TEXT NOT NULL,
            house_norm TEXT NOT NULL,
            district TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'OSM'
        );
        CREATE INDEX idx_buildings_lookup ON buildings(city, street_norm, house_norm);
        """
    )

    seen_settlement_aliases = set()
    # 1. Заполняем приоритетные settlements
    for item in KATO_SETTLEMENTS:
        for alias in item["aliases"]:
            norm_a = normalize_lookup_key(alias)
            if not norm_a:
                continue
            seen_settlement_aliases.add((norm_a, item["province"]))
            cur.execute(
                """
                INSERT INTO settlements (city, province, district, settlement_type, alias_norm)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    item["city"],
                    item["province"],
                    item["district"],
                    item["type"],
                    norm_a,
                ),
            )

    seen_district_aliases = set()
    # 2. Заполняем приоритетные urban_districts
    for item in URBAN_DISTRICTS:
        for alias in item["aliases"]:
            norm_a = normalize_lookup_key(alias)
            if not norm_a:
                continue
            seen_district_aliases.add((norm_a, item["province"]))
            cur.execute(
                """
                INSERT INTO urban_districts (district, city, province, alias_norm)
                VALUES (?, ?, ?, ?)
                """,
                (
                    item["district"],
                    item["city"],
                    item["province"],
                    norm_a,
                ),
            )

    seen_city_streets = set()
    # 3. Заполняем приоритетные streets
    for item in STREETS_AND_MICRODISTRICTS:
        seen_norms = set()
        for alias in [item["name"], *item.get("aliases", [])]:
            norm = normalize_lookup_key(alias)
            if norm and norm not in seen_norms:
                seen_norms.add(norm)
                seen_city_streets.add((item["city"].lower(), norm))
                cur.execute(
                    """
                    INSERT INTO streets (name_canonical, name_norm, street_type, city, province, default_district, source)
                    VALUES (?, ?, ?, ?, ?, ?, 'KATO+OSM')
                    """,
                    (
                        item["name"],
                        norm,
                        item["street_type"],
                        item["city"],
                        item["province"],
                        item["district"],
                    ),
                )

    # 4. Заполняем buildings
    for b in BUILDING_DISTRICTS:
        cur.execute(
            """
            INSERT INTO buildings (city, street_norm, house_norm, district, source)
            VALUES (?, ?, ?, ?, 'OSM')
            """,
            (
                b["city"],
                normalize_lookup_key(b["street_norm"]),
                b["house_norm"].lower().strip(),
                b["district"],
            ),
        )

    # 5. Импорт полного кэша КАТО 2026 + OpenStreetMap (data/kato_osm_cache.json)
    if kato_osm_cache is None:
        default_cache = Path(__file__).resolve().parent.parent / "data" / "kato_osm_cache.json"
        if default_cache.exists():
            kato_osm_cache = default_cache

    if kato_osm_cache and kato_osm_cache.exists():
        with kato_osm_cache.open("r", encoding="utf-8") as f:
            cache_data = json.load(f)

        for s_item in cache_data.get("kato_settlements", []):
            c_name = s_item["name"]
            prov = s_item["province"]
            dist = s_item.get("district")
            for alias in s_item.get("aliases", [c_name]):
                norm_a = normalize_lookup_key(alias)
                if norm_a and (norm_a, prov) not in seen_settlement_aliases:
                    seen_settlement_aliases.add((norm_a, prov))
                    cur.execute(
                        """
                        INSERT INTO settlements (city, province, district, settlement_type, alias_norm)
                        VALUES (?, ?, ?, 'нп', ?)
                        """,
                        (c_name, prov, dist, norm_a),
                    )

        for d_item in cache_data.get("kato_districts", []):
            d_name = d_item["name"]
            prov = d_item["province"]
            c_name = d_item.get("city") or ""
            for alias in d_item.get("aliases", [d_name]):
                norm_a = normalize_lookup_key(alias)
                if norm_a and (norm_a, prov) not in seen_district_aliases:
                    seen_district_aliases.add((norm_a, prov))
                    cur.execute(
                        """
                        INSERT INTO urban_districts (district, city, province, alias_norm)
                        VALUES (?, ?, ?, ?)
                        """,
                        (d_name, c_name, prov, norm_a),
                    )

        for st_item in cache_data.get("osm_streets", []):
            st_name = st_item["name"]
            st_type = st_item.get("street_type")
            c_name = st_item["city"]
            prov = st_item["province"]
            dist = st_item.get("district")
            for alias in [st_name, *st_item.get("aliases", [])]:
                norm_st = normalize_lookup_key(alias)
                if norm_st and (c_name.lower(), norm_st) not in seen_city_streets:
                    seen_city_streets.add((c_name.lower(), norm_st))
                    cur.execute(
                        """
                        INSERT INTO streets (name_canonical, name_norm, street_type, city, province, default_district, source)
                        VALUES (?, ?, ?, ?, ?, ?, 'OSM_OVERPASS')
                        """,
                        (st_name, norm_st, st_type, c_name, prov, dist),
                    )

    # Опциональный доимпорт из внешнего CSV справочника КАТО
    if kato_csv and kato_csv.exists():
        with kato_csv.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                city = (row.get("city") or row.get("name_ru") or "").strip()
                province = (row.get("province") or "").strip()
                district = (row.get("district") or "").strip() or None
                if city and province:
                    cur.execute(
                        """
                        INSERT INTO settlements (city, province, district, settlement_type, alias_norm)
                        VALUES (?, ?, ?, 'нп', ?)
                        """,
                        (city, province, district, normalize_lookup_key(city)),
                    )

    # Опциональный доимпорт из выгрузки OSM JSONL
    if osm_jsonl and osm_jsonl.exists():
        with osm_jsonl.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec.get("kind") == "street":
                    cur.execute(
                        """
                        INSERT INTO streets (name_canonical, name_norm, street_type, city, province, default_district, source)
                        VALUES (?, ?, ?, ?, ?, ?, 'OSM_DUMP')
                        """,
                        (
                            rec["name"],
                            normalize_lookup_key(rec["name"]),
                            rec.get("street_type"),
                            rec["city"],
                            rec["province"],
                            rec.get("district"),
                        ),
                    )
                elif rec.get("kind") == "building" and rec.get("district"):
                    cur.execute(
                        """
                        INSERT INTO buildings (city, street_norm, house_norm, district, source)
                        VALUES (?, ?, ?, ?, 'OSM_DUMP')
                        """,
                        (
                            rec["city"],
                            normalize_lookup_key(rec["street"]),
                            str(rec["house"]).lower().strip(),
                            rec["district"],
                        ),
                    )

    conn.commit()
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Сборка гео-справочника kaz_geo.sqlite (КАТО 2026 + OSM)")
    parser.add_argument(
        "--output",
        default="backend/data/kaz_geo.sqlite",
        help="Путь к выходному файлу SQLite",
    )
    parser.add_argument("--kato-csv", type=Path, default=None, help="Опциональный CSV КАТО")
    parser.add_argument("--osm-jsonl", type=Path, default=None, help="Опциональный JSONL дампа OSM")
    parser.add_argument("--cache", type=Path, default=None, help="Путь к кэшу data/kato_osm_cache.json")
    args = parser.parse_args()

    out_path = Path(args.output)
    build_sqlite_database(out_path, args.kato_csv, args.osm_jsonl, args.cache)
    print(f"[OK] Гео-справочник успешно собран: {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
