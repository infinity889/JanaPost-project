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


def normalize_lookup_key(text: str) -> str:
    s = text.lower().strip().replace("ё", "е")
    s = re.sub(r"[^\w\sәіңғүұқөһ]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


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
      2. Сопоставления названий улиц, микрорайонов и кварталов (включая опечатки через RapidFuzz).
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

        # 1. Точное и нечёткое совпадение в известном городе
        if city:
            city_map = self.streets_by_city.get(city.lower(), {})
            if norm in city_map:
                return city_map[norm]
            # Нечёткий поиск по улицам этого города (для опечаток вроде «казибек би» -> «Казыбек би»)
            if process is not None and fuzz is not None and city_map:
                match = process.extractOne(
                    norm,
                    list(city_map.keys()),
                    scorer=fuzz.WRatio,
                    score_cutoff=86,
                )
                if match:
                    return city_map[match[0]]

        # 2. Точное совпадение по всем городам (когда город не указан в строке)
        candidates = self.streets_by_norm.get(norm, [])
        if candidates:
            # Если известен номер дома, сначала проверяем точное совпадение (city, street, house) в таблице домов
            if house:
                h_norm = house.lower().strip()
                for c in candidates:
                    if (c.city.lower(), norm, h_norm) in self.buildings:
                        return c
            if street_type_hint:
                typed = [c for c in candidates if c.street_type == street_type_hint]
                if typed:
                    return typed[0]
            return candidates[0]

        # 3. Нечёткий поиск по всем улицам (высокий порог >= 90)
        if process is not None and fuzz is not None and len(norm) >= 4 and self.streets_by_norm:
            match = process.extractOne(
                norm,
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
        h_norm = house.lower().strip()

        # 1. Точное совпадение в таблице buildings (kaz_geo.sqlite)
        exact = self.buildings.get((c_low, s_norm, h_norm))
        if exact:
            return exact

        # Также пробуем базовый номер дома без корпуса/дроби («247а корпус 3» -> «247а» / «247»)
        base_house = h_norm.split()[0]
        if base_house != h_norm and (c_low, s_norm, base_house) in self.buildings:
            return self.buildings[(c_low, s_norm, base_house)]

        h_int = extract_house_int(h_norm)
        if h_int is None:
            return None

        # 2. Диапазонный маппинг для длинных магистралей, пересекающих несколько районов
        if c_low == "алматы":
            if s_norm in ("толе би", "төле би"):
                if h_int <= 49:
                    return "Медеуский"
                if h_int <= 289:
                    return "Алмалинский"
                return "Ауэзовский"
            if s_norm in ("абая", "абай"):
                if h_int <= 17:
                    return "Медеуский"
                if h_int <= 109:
                    return "Алмалинский"
                if h_int <= 159:
                    return "Бостандыкский"
                return "Ауэзовский"
            if s_norm in ("райымбека", "райымбек"):
                if h_int <= 100:
                    return "Медеуский"
                if h_int <= 240:
                    return "Жетысуский"
                if h_int <= 340:
                    return "Алмалинский"
                if h_int <= 480:
                    return "Ауэзовский"
                return "Алатауский"
            if s_norm in ("розыбакиева", "розыбакиев"):
                return "Алмалинский" if h_int <= 120 else "Бостандыкский"
            if s_norm in ("сейфуллина", "сейфуллин"):
                if h_int <= 280:
                    return "Турксибский"
                if h_int <= 455:
                    return "Жетысуский"
                if h_int <= 560:
                    return "Алмалинский"
                return "Бостандыкский"
            if s_norm in ("аль фараби", "әл фараби"):
                return "Медеуский" if h_int <= 36 else "Бостандыкский"
            if s_norm in ("сатпаева", "сәтбаев"):
                return "Бостандыкский" if h_int <= 90 else "Ауэзовский"
            if s_norm in ("жандосова", "жандосов"):
                if h_int <= 98:
                    return "Бостандыкский"
                if h_int <= 200:
                    return "Ауэзовский"
                return "Наурызбайский"

        if c_low == "астана":
            if s_norm in ("туран", "тұран"):
                return "Есиль" if h_int <= 35 else "Нура"
            if s_norm in ("кабанбай батыра", "кабанбай батыр", "қабанбай батыр"):
                if h_int <= 9:
                    return "Сарыарка"
                if h_int <= 48:
                    return "Есиль"
                return "Нура"
            if s_norm in ("республики", "республика"):
                return "Сарыарка" if h_int % 2 == 1 else "Байконыр"
            if s_norm in ("богенбай батыра", "бөгенбай батыр"):
                return "Сарыарка" if h_int <= 60 else "Байконыр"
            if s_norm in ("мангилик ел", "мәңгілік ел"):
                return "Есиль"

        return None
