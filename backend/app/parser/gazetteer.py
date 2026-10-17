from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from rapidfuzz import fuzz, process
except ImportError:  # pragma: no cover
    fuzz = None
    process = None


_KZ_TO_RU_CHAR_MAP = str.maketrans(
    {
        "қ": "к",
        "ғ": "г",
        "ң": "н",
        "ә": "а",
        "ө": "о",
        "ұ": "у",
        "ү": "у",
        "і": "и",
        "һ": "х",
    }
)


def normalize_lookup_key(text: str) -> str:
    s = text.lower().strip().replace("ё", "е")
    s = re.sub(r"[^\w\sәіңғүұқөһ]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def kz_to_ru_lookup_variants(norm_key: str) -> List[str]:
    """
    Генерирует поисковые варианты для двуязычного (KZ <-> RU) сопоставления улиц и районов
    в справочнике kaz_geo.sqlite (НЕ изменяет извлечённый текст street_name в ответе).
    Пример: «қабанбай батыр» -> [«қабанбай батыр», «кабанбай батыр», «кабанбай батыра»].
    """
    if not norm_key:
        return []

    variants: List[str] = []

    def _add(v: str) -> None:
        v = v.strip()
        if v and v not in variants:
            variants.append(v)

    _add(norm_key)

    # Специальные частые транслитерации KZ -> RU
    special = norm_key
    special = re.sub(r"\bәл\b", "аль", special)
    special = re.sub(r"\bсәтбаев\b", "сатпаев", special)
    special = re.sub(r"\bқонаев\b", "кунаев", special)
    special = re.sub(r"\bәуезов\b", "ауэзов", special)
    special = re.sub(r"\bуәлиханов\b", "валиханов", special)
    special = re.sub(r"\bқұнанбайұлы\b", "кунанбаева", special)
    special = re.sub(r"\bбайтұрсынұлы\b", "байтурсынова", special)
    special = re.sub(r"\bбөкейхан\b", "бокейхана", special)

    folded = norm_key.translate(_KZ_TO_RU_CHAR_MAP)
    special_folded = special.translate(_KZ_TO_RU_CHAR_MAP)

    for base in (norm_key, folded, special_folded):
        _add(base)
        if base.endswith(" батыр"):
            _add(base + "а")
        elif base.endswith(" батыра"):
            _add(base[:-1])

        if base.endswith(" хан"):
            _add(base + "а")
        elif base.endswith(" хана"):
            _add(base[:-1])

        if base.endswith(("ов", "ев", "ин")):
            _add(base + "а")
        elif base.endswith(("ова", "ева", "ина")):
            _add(base[:-1])

        if base.endswith("ай"):
            _add(base[:-1] + "я")
        elif base.endswith("ая") and len(base) <= 6:
            _add(base[:-1] + "й")

        if base.endswith("им"):
            _add(base + "а")
        elif base.endswith("има"):
            _add(base[:-1])

        # Для двусловных «Имя Фамилия» («бауыржан момышулы», «каныш сатпаев») добавляем поиск по фамилии
        parts = base.split()
        if (
            len(parts) == 2
            and parts[1].isalpha()
            and len(parts[1]) >= 4
            and parts[1] not in ("би", "хан", "хана", "батыр", "батыра", "ел", "дала", "жырау")
        ):
            _add(parts[1])
            if parts[1].endswith(("ов", "ев", "ин")):
                _add(parts[1] + "а")

    return variants


def extract_house_int(house: Optional[str]) -> Optional[int]:
    if not house:
        return None
    m = re.match(r"^\s*(\d+)", house)
    return int(m.group(1)) if m else None


@dataclass
class StreetRecord:
    name_canonical: str
    name_norm: str
    street_type: Optional[str]
    city: str
    province: str
    default_district: Optional[str]


class GeoGazetteer:
    """
    Быстрый In-Memory + SQLite гео-справочник Казахстана (КАТО 2026 + OpenStreetMap).
    Используется для:
      1. Распознавания областей, городов, посёлков, сёл и районов в шапке строки.
      2. Сопоставления названий улиц, микрорайонов и кварталов (включая опечатки через RapidFuzz и KZ<->RU формы).
      3. Восстановления недостающих полей (district, street_type, city, province), когда их нет в строке.
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.settlements: Dict[str, List[Tuple[str, str, Optional[str]]]] = {}
        self.urban_districts: Dict[str, List[Tuple[str, str, str]]] = {}
        self.streets_by_norm: Dict[str, List[StreetRecord]] = {}
        self.streets_by_city: Dict[str, Dict[str, StreetRecord]] = {}
        self.buildings: Dict[Tuple[str, str, str], str] = {}
        self._load()

    def _load(self) -> None:
        if not self.db_path.exists():
            return
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()

        for city, province, district, alias_norm in cur.execute(
            "SELECT city, province, district, alias_norm FROM settlements ORDER BY id ASC"
        ):
            self.settlements.setdefault(alias_norm, []).append((city, province, district))

        for district, city, province, alias_norm in cur.execute(
            "SELECT district, city, province, alias_norm FROM urban_districts ORDER BY id ASC"
        ):
            self.urban_districts.setdefault(alias_norm, []).append((district, city, province))

        for name_canonical, name_norm, street_type, city, province, default_district in cur.execute(
            "SELECT name_canonical, name_norm, street_type, city, province, default_district FROM streets ORDER BY id ASC"
        ):
            rec = StreetRecord(
                name_canonical=name_canonical,
                name_norm=name_norm,
                street_type=street_type,
                city=city,
                province=province,
                default_district=default_district,
            )
            self.streets_by_norm.setdefault(name_norm, []).append(rec)
            city_dict = self.streets_by_city.setdefault(city.lower(), {})
            # Сохраняем первую (приоритетную эталонную) запись для каждого (city, name_norm)
            if name_norm not in city_dict:
                city_dict[name_norm] = rec

        for city, street_norm, house_norm, district in cur.execute(
            "SELECT city, street_norm, house_norm, district FROM buildings ORDER BY id ASC"
        ):
            key = (city.lower(), street_norm, house_norm.lower())
            if key not in self.buildings:
                self.buildings[key] = district

        conn.close()

    def lookup_street(
        self,
        street_name: str,
        city: Optional[str] = None,
        street_type_hint: Optional[str] = None,
        house: Optional[str] = None,
    ) -> Optional[StreetRecord]:
        norm = normalize_lookup_key(street_name)
        if not norm:
            return None

        variants = kz_to_ru_lookup_variants(norm)

        # 1. Точное (включая KZ<->RU варианты) и нечёткое совпадение в известном городе
        if city:
            city_map = self.streets_by_city.get(city.lower(), {})
            for v in variants:
                if v in city_map:
                    return city_map[v]
            # Нечёткий поиск по улицам этого города (для опечаток вроде «казибек би» -> «Казыбек би»)
            if process is not None and fuzz is not None and city_map:
                for q in variants[:2]:
                    match = process.extractOne(
                        q,
                        list(city_map.keys()),
                        scorer=fuzz.WRatio,
                        score_cutoff=86,
                    )
                    if match:
                        return city_map[match[0]]

        # 2. Точное совпадение по всем городам (когда город не указан в строке)
        for v in variants:
            candidates = self.streets_by_norm.get(v, [])
            if candidates:
                # Если известен номер дома, сначала проверяем точное совпадение (city, street, house) в таблице домов
                if house:
                    h_norm = house.lower().strip()
                    for c in candidates:
                        if (c.city.lower(), v, h_norm) in self.buildings:
                            return c
                if street_type_hint:
                    typed = [c for c in candidates if c.street_type == street_type_hint]
                    if typed:
                        return typed[0]
                return candidates[0]

        # 3. Нечёткий поиск по всем улицам (высокий порог >= 90)
        if process is not None and fuzz is not None and len(norm) >= 4 and self.streets_by_norm:
            for q in variants[:2]:
                match = process.extractOne(
                    q,
                    list(self.streets_by_norm.keys()),
                    scorer=fuzz.WRatio,
                    score_cutoff=90,
                )
                if match:
                    return self.streets_by_norm[match[0]][0]

        return None

    def lookup_building_district(
        self,
        city: str,
        street_name: str,
        house: Optional[str],
    ) -> Optional[str]:
        if not city or not street_name or not house:
            return None
        c_low = city.lower().strip()
        s_norm = normalize_lookup_key(street_name)
        s_variants = kz_to_ru_lookup_variants(s_norm)
        h_norm = house.lower().strip()

        # 1. Точное совпадение в таблице buildings (kaz_geo.sqlite) с учётом KZ<->RU форм
        for sv in s_variants:
            exact = self.buildings.get((c_low, sv, h_norm))
            if exact:
                return exact

        # Также пробуем базовый номер дома без корпуса/дроби («247а корпус 3» -> «247а» / «247»)
        base_house = h_norm.split()[0]
        if base_house != h_norm:
            for sv in s_variants:
                if (c_low, sv, base_house) in self.buildings:
                    return self.buildings[(c_low, sv, base_house)]

        h_int = extract_house_int(h_norm)
        if h_int is None:
            return None

        s_set = set(s_variants)

        # 2. Диапазонный маппинг для длинных магистралей, пересекающих несколько районов
        if c_low == "алматы":
            if s_set & {"толе би", "төле би"}:
                if h_int <= 49:
                    return "Медеуский"
                if h_int <= 289:
                    return "Алмалинский"
                return "Ауэзовский"
            if s_set & {"абая", "абай", "абай кунанбаева", "абай құнанбайұлы"}:
                if h_int <= 17:
                    return "Медеуский"
                if h_int <= 109:
                    return "Алмалинский"
                if h_int <= 159:
                    return "Бостандыкский"
                return "Ауэзовский"
            if s_set & {"райымбека", "райымбек", "райымбек батыра", "райымбек батыр"}:
                if h_int <= 100:
                    return "Медеуский"
                if h_int <= 240:
                    return "Жетысуский"
                if h_int <= 340:
                    return "Алмалинский"
                if h_int <= 480:
                    return "Ауэзовский"
                return "Алатауский"
            if s_set & {"розыбакиева", "розыбакиев"}:
                return "Алмалинский" if h_int <= 120 else "Бостандыкский"
            if s_set & {"сейфуллина", "сейфуллин", "сакен сейфуллин", "сәкен сейфуллин"}:
                if h_int <= 280:
                    return "Турксибский"
                if h_int <= 455:
                    return "Жетысуский"
                if h_int <= 560:
                    return "Алмалинский"
                return "Бостандыкский"
            if s_set & {"аль фараби", "әл фараби"}:
                return "Медеуский" if h_int <= 36 else "Бостандыкский"
            if s_set & {"сатпаева", "сатпаев", "сәтбаев", "каныш сатпаев", "қаныш сәтбаев"}:
                return "Бостандыкский" if h_int <= 90 else "Ауэзовский"
            if s_set & {"жандосова", "жандосов", "ораз жандосов"}:
                if h_int <= 98:
                    return "Бостандыкский"
                if h_int <= 200:
                    return "Ауэзовский"
                return "Наурызбайский"

        if c_low == "астана":
            if s_set & {"туран", "тұран"}:
                return "Есиль" if h_int <= 35 else "Нура"
            if s_set & {"кабанбай батыра", "кабанбай батыр", "қабанбай батыр"}:
                if h_int <= 9:
                    return "Сарыарка"
                if h_int <= 48:
                    return "Есиль"
                return "Нура"
            if s_set & {"республики", "республика"}:
                return "Сарыарка" if h_int % 2 == 1 else "Байконыр"
            if s_set & {"богенбай батыра", "богенбай батыр", "бөгенбай батыр"}:
                return "Сарыарка" if h_int <= 60 else "Байконыр"
            if s_set & {"мангилик ел", "мәңгілік ел"}:
                return "Есиль"

        return None
