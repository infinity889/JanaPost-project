#!/usr/bin/env python3
"""
Скрипт сбора полного справочника КАТО 2026 + OpenStreetMap РК
и сохранения локального кэша data/kato_osm_cache.json для автономной сборки kaz_geo.sqlite.

Источники:
1. Таблица КАТО 2026 с https://nalogikz.kz/docs/kato-klassifikator-administrativno-territorialnyh-obektov-2026-g.html
2. Официальный документ НК РК 11-2021 (КАТО) из /home/nurbol/Загрузки/Изм_1_КАТО_ред1_рус.docx (6905 строк)
3. OpenStreetMap (Overpass API) — все города, районы, сёла, микрорайоны и улицы основных городов РК (RU + KK)
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT_DIR / "data" / "kato_osm_cache.json"
LOCAL_DOCX_PATH = Path("/home/nurbol/Загрузки/Изм_1_КАТО_ред1_рус.docx")
NALOGIKZ_URL = "https://nalogikz.kz/docs/kato-klassifikator-administrativno-territorialnyh-obektov-2026-g.html"

# Эталонная таблица 20 регионов РК по КАТО 2026 (прямой порядок со словом «область» по ТЗ)
KATO_PROVINCE_BY_PREFIX: Dict[str, str] = {
    "10": "Абайская область",
    "11": "Акмолинская область",
    "15": "Актюбинская область",
    "19": "Алматинская область",
    "23": "Атырауская область",
    "27": "Западно-Казахстанская область",
    "31": "Жамбылская область",
    "33": "Жетысуская область",
    "35": "Карагандинская область",
    "39": "Костанайская область",
    "43": "Кызылординская область",
    "47": "Мангистауская область",
    "51": "Туркестанская область",  # исторический код ЮКО -> Туркестанская область
    "55": "Павлодарская область",
    "59": "Северо-Казахстанская область",
    "61": "Туркестанская область",
    "62": "Улытауская область",
    "63": "Восточно-Казахстанская область",
    "71": "Астана",
    "75": "Алматы",
    "79": "Шымкент",
}


def clean_kato_settlement_name(raw_name: str) -> Tuple[Optional[str], str]:
    """
    Очищает название объекта КАТО от служебных префиксов/суффиксов («г.», «с.», «п.», «Г.А.», «с.о.», «район»).
    Возвращает (clean_name, kind), где kind in {'city', 'district', 'rural_district', 'region', 'skip'}.
    """
    s = re.sub(r"\s+", " ", raw_name).strip()
    if not s:
        return None, "skip"

    # Пропускаем сельские и поселковые округа / администрации («Бесбидаикский с.о.», «Аксуская с.а.», «п.а.»)
    if re.search(r"\b(?:с\.о\.|с\.а\.|п\.а\.|п\.о\.|сельский\s+округ|ауылдық\s+округ)\b", s, re.I):
        return None, "rural_district"

    # Районы области или города («Ауэзовский район», «Жанасемейский район», «район Алматы»)
    if re.search(r"\bрайон\b", s, re.I):
        clean_d = re.sub(r"\bрайон[а-я]*\b", "", s, flags=re.I).strip(" ,.-")
        return (clean_d if clean_d else None), "district"

    # Городские администрации («Семей Г.А.», «Конаев Г.А.»)
    if re.search(r"\bГ\.А\.", s, re.I):
        clean_c = re.sub(r"\bГ\.А\.?", "", s, flags=re.I).strip(" ,.-")
        clean_c = re.sub(r"^(?:г\.|город)\s*", "", clean_c, flags=re.I).strip(" ,.-")
        return (clean_c if clean_c else None), "city"

    # Населённые пункты («г.Конаев», «с.Степное», «п.Боралдай», «аул Косшы», «ст.Чемолган»)
    m_settle = re.match(
        r"^(?:г\.|город|п\.|пос\.|поселок|посёлок|с\.|село|аул|а\.|ст\.|станция|разъезд|рзд\.|уч\.)\s*(.+)$",
        s,
        flags=re.I,
    )
    if m_settle:
        clean_c = m_settle.group(1).strip(" ,.-")
        # Пропускаем номерные уч./рзд. вроде «рзд.19»
        if re.fullmatch(r"\d+[а-яa-z]?", clean_c, flags=re.I):
            return None, "skip"
        return clean_c, "city"

    return None, "skip"


def parse_nalogikz_page() -> Dict[str, str]:
    """Парсит страницу nalogikz.kz для верификации кодов КАТО 2026."""
    found_regions: Dict[str, str] = {}
    try:
        req = urllib.request.Request(NALOGIKZ_URL, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", errors="ignore")
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.S | re.I)
        for r in rows:
            cells = [
                re.sub(r"<[^>]+>", "", c).replace("&#8212;", "-").strip()
                for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, flags=re.S | re.I)
            ]
            cells = [c for c in cells if c]
            if len(cells) >= 2:
                # Проверяем 9-значный код (110000000) или 2-значный код (10, 11, 15...)
                for c in cells:
                    m9 = re.fullmatch(r"(\d{2})0000000", c)
                    if m9 and m9.group(1) in KATO_PROVINCE_BY_PREFIX:
                        found_regions[m9.group(1)] = KATO_PROVINCE_BY_PREFIX[m9.group(1)]
                    elif c in KATO_PROVINCE_BY_PREFIX:
                        found_regions[c] = KATO_PROVINCE_BY_PREFIX[c]
        print(f"[КАТО 2026 Web] Подтверждено регионов со страницы nalogikz.kz: {len(found_regions)}")
    except Exception as exc:
        print(f"[КАТО 2026 Web] Предупреждение: не удалось загрузить страницу ({exc}), используем встроенную таблицу.")
    return found_regions


def parse_local_kato_docx() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Извлекает иерархию районов и населённых пунктов РК из локального файла НК РК 11-2021 (КАТО).
    """
    if not LOCAL_DOCX_PATH.exists():
        print(f"[КАТО DOCX] Файл {LOCAL_DOCX_PATH} не найден, пропускаем.")
        return [], []

    with zipfile.ZipFile(LOCAL_DOCX_PATH) as z:
        xml_content = z.read("word/document.xml")
    tree = ET.fromstring(xml_content)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

    # Сначала собираем коды районов (AB CD 00000), чтобы привязать к ним сёла и посёлки
    district_by_abcd: Dict[str, Tuple[str, str]] = {}
    raw_entries: List[Tuple[str, str, str]] = []

    for tr in tree.findall(".//w:tr", ns):
        cells = [
            "".join(t.text for t in tc.findall(".//w:t", ns) if t.text).strip()
            for tc in tr.findall("./w:tc", ns)
        ]
        if len(cells) < 3:
            continue
        directive = cells[0].strip()
        if directive not in ("В", "И", "А"):
            continue
        code_match = re.search(r"(\d{9})", cells[1])
        if not code_match:
            continue
        code9 = code_match.group(1)
        raw_name = cells[2].strip()
        raw_entries.append((directive, code9, raw_name))

        ab = code9[:2]
        cd = code9[2:4]
        rest = code9[4:]
        province = KATO_PROVINCE_BY_PREFIX.get(ab)
        if not province:
            continue

        clean_name, kind = clean_kato_settlement_name(raw_name)
        if kind == "district" and clean_name and rest == "00000":
            # Приоритет у директив В и И
            if directive in ("В", "И") or (ab + cd) not in district_by_abcd:
                district_by_abcd[ab + cd] = (clean_name, province)

    settlements: Dict[Tuple[str, str], Dict[str, Any]] = {}
    districts: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for d_name, prov in district_by_abcd.values():
        districts[(d_name.lower(), prov)] = {
            "name": d_name,
            "city": None,
            "province": prov,
            "aliases": [d_name.lower()],
        }

    # Обрабатываем населённые пункты (сначала В и И, чтобы актуальные области 2026 перезаписывали старые А)
    priority_order = {"В": 0, "И": 1, "А": 2}
    raw_entries.sort(key=lambda x: priority_order.get(x[0], 9))

    for directive, code9, raw_name in raw_entries:
        ab = code9[:2]
        cd = code9[2:4]
        province = KATO_PROVINCE_BY_PREFIX.get(ab)
        if not province:
            continue
        clean_name, kind = clean_kato_settlement_name(raw_name)
        if kind != "city" or not clean_name or len(clean_name) < 2:
            continue

        parent_dist = district_by_abcd.get(ab + cd, (None, province))[0]
        key = (clean_name.lower(), province)
        # Если этот населённый пункт уже добавлен из директивы В/И (например, в новую Абайскую или Жетысускую область),
        # не перезаписываем его старой записью из директивы А
        if directive == "А" and any(k[0] == clean_name.lower() for k in settlements):
            continue

        if key not in settlements:
            settlements[key] = {
                "name": clean_name,
                "province": province,
                "district": parent_dist,
                "aliases": [clean_name.lower()],
            }

    print(
        f"[КАТО DOCX] Извлечено из НК РК 11-2021: "
        f"районов={len(districts)}, населённых пунктов={len(settlements)}"
    )
    return list(settlements.values()), list(districts.values())


OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
]


def query_overpass(query: str, timeout: int = 60) -> Dict[str, Any]:
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            req = urllib.request.Request(
                endpoint,
                data=data,
                headers={"User-Agent": "JanaAddressGazetteerBuilder/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            print(f"  [Overpass Retry] {endpoint}: {exc}")
            time.sleep(1)
    return {"elements": []}


def infer_street_type_and_clean_name(raw_name: str, highway_or_place: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Извлекает канонический street_type и чистое название улицы/микрорайона из OSM-тега name.
    Например: «улица Абая» -> («улица», «Абая»), «проспект Туран» -> («проспект», «Туран»),
    «микрорайон Аксай-3а» -> («микрорайон», «Аксай-3а»).
    """
    s = re.sub(r"\s+", " ", raw_name).strip(" ,.-")
    if not s or len(s) < 2:
        return None, None

    patterns = [
        (r"^(?:улица|ул\.?)\s+(.+)$", "улица"),
        (r"^(.+?)\s+(?:улица|ул\.?|көшесі|кошеси)$", "улица"),
        (r"^(?:проспект|пр-т|пр\.?)\s+(.+)$", "проспект"),
        (r"^(.+?)\s+(?:проспект|даңғылы|дангылы)$", "проспект"),
        (r"^(?:микрорайон|мкр\.?|мкрн\.?)\s+(.+)$", "микрорайон"),
        (r"^(.+?)\s+(?:микрорайон|мкр\.?|шағын\s+ауданы|ықшам\s+ауданы)$", "микрорайон"),
        (r"^(?:переулок|пер\.?)\s+(.+)$", "переулок"),
        (r"^(.+?)\s+(?:переулок|пер\.?|орамы)$", "переулок"),
        (r"^(?:бульвар|б-р)\s+(.+)$", "бульвар"),
        (r"^(.+?)\s+(?:бульвар|бульвары)$", "бульвар"),
        (r"^(?:квартал|кв-л)\s+(.+)$", "квартал"),
        (r"^(.+?)\s+(?:квартал|кв-л)$", "квартал"),
        (r"^(?:шоссе|ш\.?)\s+(.+)$", "шоссе"),
        (r"^(.+?)\s+(?:шоссе|тас\s+жолы)$", "шоссе"),
        (r"^(?:проезд|пр-д)\s+(.+)$", "проезд"),
        (r"^(.+?)\s+(?:проезд)$", "проезд"),
        (r"^(?:тупик|туп\.?)\s+(.+)$", "тупик"),
        (r"^(.+?)\s+(?:тупик|тұйығы)$", "тупик"),
        (r"^(?:набережная|наб\.?)\s+(.+)$", "набережная"),
        (r"^(?:жилой\s+массив|жилмассив|ж/м)\s+(.+)$", "микрорайон"),
    ]
    for pat, st_type in patterns:
        m = re.match(pat, s, flags=re.I)
        if m:
            clean = m.group(1).strip(" ,.-")
            if clean and (len(clean) >= 2 or (st_type == "микрорайон" and clean.isdigit())):
                return st_type, clean

    if highway_or_place in ("suburb", "quarter", "neighbourhood"):
        return "микрорайон", s
    return "улица", s


def fetch_osm_streets_for_cities() -> List[Dict[str, Any]]:
    """
    Выгружает реальные улицы и микрорайоны из OpenStreetMap для всех 20 областных центров Казахстана
    с координатной привязкой к городским районам (district).
    Использует инкрементальное кэширование, чтобы не скачивать повторно уже загруженные города.
    """
    city_configs = [
        {"city": "Алматы", "province": "Алматы", "bbox": (43.12, 76.74, 43.40, 77.12)},
        {"city": "Астана", "province": "Астана", "bbox": (51.02, 71.22, 51.28, 71.62)},
        {"city": "Шымкент", "province": "Шымкент", "bbox": (42.22, 69.45, 42.45, 69.75)},
        {"city": "Караганда", "province": "Карагандинская область", "bbox": (49.72, 72.95, 50.02, 73.30)},
        {"city": "Актобе", "province": "Актюбинская область", "bbox": (50.20, 57.05, 50.36, 57.32)},
        {"city": "Атырау", "province": "Атырауская область", "bbox": (47.02, 51.80, 47.20, 52.05)},
        {"city": "Тараз", "province": "Жамбылская область", "bbox": (42.83, 71.28, 42.96, 71.46)},
        {"city": "Павлодар", "province": "Павлодарская область", "bbox": (52.20, 76.85, 52.38, 77.10)},
        {"city": "Семей", "province": "Абайская область", "bbox": (50.34, 80.12, 50.48, 80.38)},
        {"city": "Усть-Каменогорск", "province": "Восточно-Казахстанская область", "bbox": (49.88, 82.50, 50.05, 82.75)},
        {"city": "Костанай", "province": "Костанайская область", "bbox": (53.14, 63.52, 53.29, 63.72)},
        {"city": "Кызылорда", "province": "Кызылординская область", "bbox": (44.76, 65.42, 44.92, 65.62)},
        {"city": "Уральск", "province": "Западно-Казахстанская область", "bbox": (51.14, 51.26, 51.30, 51.48)},
        {"city": "Актау", "province": "Мангистауская область", "bbox": (43.60, 51.10, 43.72, 51.25)},
        {"city": "Петропавловск", "province": "Северо-Казахстанская область", "bbox": (54.81, 69.06, 54.94, 69.25)},
        {"city": "Талдыкорган", "province": "Жетысуская область", "bbox": (44.96, 78.29, 45.07, 78.45)},
        {"city": "Туркестан", "province": "Туркестанская область", "bbox": (43.24, 68.18, 43.36, 68.35)},
        {"city": "Кокшетау", "province": "Акмолинская область", "bbox": (53.23, 69.30, 53.34, 69.47)},
        {"city": "Жезказган", "province": "Улытауская область", "bbox": (47.74, 67.64, 47.84, 67.79)},
        {"city": "Конаев", "province": "Алматинская область", "bbox": (43.82, 77.01, 43.91, 77.12)},
    ]

    all_streets: Dict[Tuple[str, str], Dict[str, Any]] = {}
    cached_cities: set[str] = set()
    if CACHE_PATH.exists():
        try:
            with CACHE_PATH.open("r", encoding="utf-8") as f:
                existing = json.load(f)
            for item in existing.get("osm_streets", []):
                c_name = item["city"]
                st_name = item["name"]
                all_streets[(c_name, st_name.lower())] = item
                cached_cities.add(c_name)
        except Exception:
            pass

    for cfg in city_configs:
        city = cfg["city"]
        province = cfg["province"]
        if city in cached_cities:
            print(f"[OSM Overpass] Город {city} уже есть в локальном кэше, пропускаем сетевой запрос.")
            continue
        s, w, n, e = cfg["bbox"]
        print(f"[OSM Overpass] Загрузка районов, микрорайонов и улиц для г. {city}...")

        query = f"""
        [out:json][timeout:45];
        (
          node["place"~"^(suburb|quarter|neighbourhood)$"]({s},{w},{n},{e});
          way["place"~"^(suburb|quarter|neighbourhood)$"]({s},{w},{n},{e});
          way["highway"~"^(primary|secondary|tertiary|residential|living_street|pedestrian|unclassified)$"]["name"]({s},{w},{n},{e});
        );
        out tags center;
        """
        data = query_overpass(query, timeout=50)
        elements = data.get("elements", [])
        print(f"  -> получено {len(elements)} объектов OSM для г. {city}")

        for el in elements:
            tags = el.get("tags", {})
            raw_ru = tags.get("name:ru") or tags.get("name")
            raw_kk = tags.get("name:kk")
            if not raw_ru:
                continue

            kind_tag = tags.get("place") or tags.get("highway") or "residential"
            st_type, clean_name = infer_street_type_and_clean_name(raw_ru, kind_tag)
            if not clean_name or len(clean_name) < 2:
                continue

            # Вычисляем координаты центра для приближённой привязки к району города
            lat = el.get("lat") or (el.get("center", {}) or {}).get("lat")
            lon = el.get("lon") or (el.get("center", {}) or {}).get("lon")
            district = infer_city_district_by_coords(city, lat, lon)

            key = (city, clean_name.lower())
            aliases = {clean_name.lower()}
            if raw_kk:
                _, clean_kk = infer_street_type_and_clean_name(raw_kk, kind_tag)
                if clean_kk and len(clean_kk) >= 2:
                    aliases.add(clean_kk.lower())

            if key not in all_streets:
                all_streets[key] = {
                    "name": clean_name,
                    "street_type": st_type,
                    "city": city,
                    "province": province,
                    "district": district,
                    "aliases": sorted(aliases),
                }
            else:
                existing_aliases = set(all_streets[key]["aliases"]) | aliases
                all_streets[key]["aliases"] = sorted(existing_aliases)
                if not all_streets[key].get("district") and district:
                    all_streets[key]["district"] = district

    print(f"[OSM Overpass] Всего уникальных улиц и микрорайонов из OSM: {len(all_streets)}")
    return list(all_streets.values())


def infer_city_district_by_coords(city: str, lat: Optional[float], lon: Optional[float]) -> Optional[str]:
    """Определяет административный район города по координатам объекта OSM."""
    if lat is None or lon is None:
        return None

    if city == "Алматы":
        # 8 районов Алматы по географическим секторам
        if lat > 43.285:
            return "Жетысуский" if lon < 76.935 else "Турксибский"
        if lon < 76.825:
            return "Наурызбайский" if lat < 43.235 else "Алатауский"
        if lon < 76.885:
            return "Алатауский" if lat > 43.255 else "Ауэзовский"
        if lon > 76.945:
            return "Медеуский"
        return "Алмалинский" if lat > 43.238 else "Бостандыкский"

    if city == "Астана":
        # 6 районов Астаны (Есиль, Нура, Сарыарка, Байконыр, Алматы, Сарайшык)
        if lat < 51.145:
            return "Нура" if lon < 71.405 else "Есиль"
        if lon < 71.425:
            return "Сарыарка"
        if lon < 71.465:
            return "Байконыр"
        return "Сарайшык" if lat < 51.155 else "Алматы"

    if city == "Шымкент":
        if lat > 42.355:
            return "Каратауский" if lon > 69.60 else "Абайский"
        if lon < 69.57:
            return "Туран"
        if lon > 69.62:
            return "Енбекшинский"
        return "Аль-Фарабийский"

    if city == "Караганда":
        return "Алихана Бокейхана" if lat > 49.845 else "Казыбек би"

    if city == "Актобе":
        return "Алматы" if lon > 57.185 else "Астана"

    return None


def main() -> int:
    regions = parse_nalogikz_page()
    kato_settlements, kato_districts = parse_local_kato_docx()
    osm_streets = fetch_osm_streets_for_cities()

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "KATO 2026 (nalogikz.kz + НК РК 11-2021) + OpenStreetMap Overpass API",
        "regions": regions or KATO_PROVINCE_BY_PREFIX,
        "kato_settlements": kato_settlements,
        "kato_districts": kato_districts,
        "osm_streets": osm_streets,
    }
    with CACHE_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(
        f"[OK] Кэш КАТО 2026 + OSM сохранён в {CACHE_PATH} "
        f"({CACHE_PATH.stat().st_size / 1024:.1f} KB)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
