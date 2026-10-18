from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple

from app.parser.gazetteer import GeoGazetteer, kz_to_ru_lookup_variants, normalize_lookup_key
from app.parser.preprocessor import SpanString, preprocess_with_spans
from app.schemas import ParsedAddressItem, RawAddressItem


STREET_TYPE_CANONICAL = {
    "ул": "улица",
    "улица": "улица",
    "көшесі": "улица",
    "кошеси": "улица",
    "көше": "улица",
    "коше": "улица",
    "к-сі": "улица",
    "к-си": "улица",
    "көш": "улица",
    "кош": "улица",
    "пр": "проспект",
    "просп": "проспект",
    "проспект": "проспект",
    "пр-т": "проспект",
    "даңғылы": "проспект",
    "дангылы": "проспект",
    "даңғыл": "проспект",
    "дангыл": "проспект",
    "д-лы": "проспект",
    "даңғ": "проспект",
    "данг": "проспект",
    "мкр": "микрорайон",
    "мкрн": "микрорайон",
    "микрорайон": "микрорайон",
    "микрорайоны": "микрорайон",
    "шағын ауданы": "микрорайон",
    "шағын аудан": "микрорайон",
    "шағын ауд": "микрорайон",
    "шағынауданы": "микрорайон",
    "шағынаудан": "микрорайон",
    "шагын ауданы": "микрорайон",
    "шагын аудан": "микрорайон",
    "шагынауданы": "микрорайон",
    "шагынаудан": "микрорайон",
    "ш/а": "микрорайон",
    "ш.а": "микрорайон",
    "ықшам ауданы": "микрорайон",
    "ықшам аудан": "микрорайон",
    "ықшам ауд": "микрорайон",
    "ықшамауданы": "микрорайон",
    "ықшамаудан": "микрорайон",
    "ыкшам ауданы": "микрорайон",
    "ыкшам аудан": "микрорайон",
    "ыкшамауданы": "микрорайон",
    "ыкшамаудан": "микрорайон",
    "ы/а": "микрорайон",
    "ы.а": "микрорайон",
    "мөлтек ауданы": "микрорайон",
    "мөлтек аудан": "микрорайон",
    "мөлтекауданы": "микрорайон",
    "мөлтекаудан": "микрорайон",
    "м/а": "микрорайон",
    "пер": "переулок",
    "переулок": "переулок",
    "орамы": "переулок",
    "орам": "переулок",
    "тығырығы": "переулок",
    "кв-л": "квартал",
    "квартал": "квартал",
    "кварталы": "квартал",
    "б-р": "бульвар",
    "бульвар": "бульвар",
    "бульвары": "бульвар",
    "желекжолы": "бульвар",
    "желекжол": "бульвар",
    "ш": "шоссе",
    "шоссе": "шоссе",
    "шоссесі": "шоссе",
    "тас жолы": "шоссе",
    "тасжолы": "шоссе",
    "тас жол": "шоссе",
    "проезд": "проезд",
    "пр-д": "проезд",
    "өткелі": "проезд",
    "өткел": "проезд",
    "тупик": "тупик",
    "туп": "тупик",
    "тұйық көшесі": "тупик",
    "тұйық көше": "тупик",
    "тұйық": "тупик",
    "наб": "набережная",
    "набережная": "набережная",
    "жағалауы": "набережная",
}

# Служебные слова, которые не могут быть частью названия улицы или второго слова в 2-словных названиях
_STREET_STOPWORDS = {
    "дом",
    "д",
    "үй",
    "уй",
    "уч",
    "участок",
    "корпус",
    "корп",
    "блок",
    "стр",
    "кв",
    "квартира",
    "пәтер",
    "патер",
    "пәт",
    "flat",
    "kv",
    "офис",
    "оф",
    "каб",
    "кеңсе",
    "подъезд",
    "подьезд",
    "п-д",
    "под",
    "кіреберіс",
    "киреберис",
    "кір",
    "этаж",
    "эт",
    "қабат",
    "кабат",
    "қаб",
    "уг",
    "угол",
    "қиылысы",
    "бұрышы",
    "возле",
    "напротив",
    "рядом",
    "жанында",
    "қасында",
    "маңында",
    "қарсысында",
    "магазин",
    "дүкен",
    "дүкені",
    "жк",
    "түк",
    "тц",
    "трц",
    "бц",
    "соо",
    "город",
    "қаласы",
    "қала",
    "қ-сы",
    "облысы",
    "область",
    "район",
    "р-н",
    "ауданы",
    "аудан",
    "кенті",
    "кент",
    "ауылы",
    "ауыл",
    "село",
    "поселок",
    "посёлок",
    "улица",
    "ул",
    "көшесі",
    "кошеси",
    "көше",
    "к-сі",
    "проспект",
    "просп",
    "пр",
    "пр-т",
    "даңғылы",
    "дангылы",
    "даңғыл",
    "д-лы",
    "микрорайон",
    "мкр",
    "мкрн",
    "шағын",
    "шагын",
    "ықшам",
    "ыкшам",
    "мөлтек",
    "тұрғын",
    "переулок",
    "пер",
    "орамы",
    "квартал",
    "кв-л",
    "бульвар",
    "шоссе",
}

# Прямое отображение всех 17 областей РК (RU/KK, прямой и инверсный порядок) в формат ТЗ
PROVINCE_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(?:область\s+абай(?:ская)?|абайская\s+(?:обл\.?|область)|абай\s+обл(?:ысы|\.?)|облысы\s+абай)(?:\s*/\s*абай\s+облысы)?\b", re.I), "Абайская область"),
    (re.compile(r"\b(?:область\s+жет[ыі]су(?:ская)?|жет[ыі]суская\s+(?:обл\.?|область)|жет[іы]су\s+обл(?:ысы|\.?)|облысы\s+жет[іы]су)(?:\s*/\s*жетісу\s+облысы)?\b", re.I), "Жетысуская область"),
    (re.compile(r"\b(?:область\s+[уұ]лытау(?:ская)?|[уұ]лытауская\s+(?:обл\.?|область)|[ұу]лытау\s+обл(?:ысы|\.?)|облысы\s+[ұу]лытау)(?:\s*/\s*ұлытау\s+облысы)?\b", re.I), "Улытауская область"),
    (re.compile(r"\b(?:область\s+актюбинская|актюбинская\s+(?:обл\.?|область)|ақтөбе\s+обл(?:ысы|\.?)|облысы\s+ақтөбе)(?:\s*/\s*ақтөбе\s+облысы)?\b", re.I), "Актюбинская область"),
    (re.compile(r"\b(?:область\s+акмолинская|акмолинская\s+(?:обл\.?|область)|ақмола\s+обл(?:ысы|\.?)|облысы\s+ақмола)(?:\s*/\s*ақмола\s+облысы)?\b", re.I), "Акмолинская область"),
    (re.compile(r"\b(?:область\s+алматинская|алматинская\s+(?:обл\.?|область)|алматы\s+обл(?:ысы|\.?)|облысы\s+алматы)(?:\s*/\s*алматы\s+облысы)?\b", re.I), "Алматинская область"),
    (re.compile(r"\b(?:область\s+атырауская|атырауская\s+(?:обл\.?|область)|атырау\s+обл(?:ысы|\.?)|облысы\s+атырау)(?:\s*/\s*атырау\s+облысы)?\b", re.I), "Атырауская область"),
    (re.compile(r"\b(?:восточно[-\s]*казахстанская\s+(?:обл\.?|область)|вко|шқо|шығыс\s+қазақстан\s+обл(?:ысы|\.?))\b", re.I), "Восточно-Казахстанская область"),
    (re.compile(r"\b(?:область\s+жамбылская|жамбылская\s+(?:обл\.?|область)|жамбыл\s+обл(?:ысы|\.?)|облысы\s+жамбыл)(?:\s*/\s*жамбыл\s+облысы)?\b", re.I), "Жамбылская область"),
    (re.compile(r"\b(?:западно[-\s]*казахстанская\s+(?:обл\.?|область)|зко|бқо|батыс\s+қазақстан\s+обл(?:ысы|\.?))\b", re.I), "Западно-Казахстанская область"),
    (re.compile(r"\b(?:область\s+карагандинская|карагандинская\s+(?:обл\.?|область)|қарағанды\s+обл(?:ысы|\.?)|облысы\s+қарағанды)(?:\s*/\s*қарағанды\s+облысы)?\b", re.I), "Карагандинская область"),
    (re.compile(r"\b(?:область\s+костанайская|костанайская\s+(?:обл\.?|область)|қостанай\s+обл(?:ысы|\.?)|облысы\s+қостанай)(?:\s*/\s*қостанай\s+облысы)?\b", re.I), "Костанайская область"),
    (re.compile(r"\b(?:область\s+кызылординская|кызылординская\s+(?:обл\.?|область)|қызылорда\s+обл(?:ысы|\.?)|облысы\s+қызылорда)(?:\s*/\s*қызылорда\s+облысы)?\b", re.I), "Кызылординская область"),
    (re.compile(r"\b(?:область\s+мангистауская|мангистауская\s+(?:обл\.?|область)|маңғыстау\s+обл(?:ысы|\.?)|облысы\s+маңғыстау)(?:\s*/\s*маңғыстау\s+облысы)?\b", re.I), "Мангистауская область"),
    (re.compile(r"\b(?:область\s+павлодарская|павлодарская\s+(?:обл\.?|область)|павлодар\s+обл(?:ысы|\.?)|облысы\s+павлодар)(?:\s*/\s*павлодар\s+облысы)?\b", re.I), "Павлодарская область"),
    (re.compile(r"\b(?:северо[-\s]*казахстанская\s+(?:обл\.?|область)|ско|сқо|солтүстік\s+қазақстан\s+обл(?:ысы|\.?))\b", re.I), "Северо-Казахстанская область"),
    (re.compile(r"\b(?:область\s+туркестанская|туркестанская\s+(?:обл\.?|область)|южно[-\s]*казахстанская\s+(?:обл\.?|область)|юко|оқо|түркістан\s+обл(?:ысы|\.?)|оңтүстік\s+қазақстан\s+обл(?:ысы|\.?))\b", re.I), "Туркестанская область"),
]


class AddressParserPipeline:
    """
    6-ступенчатый Span-парсер и модуль гео-обогащения адресов РК (КАТО 2026 + OpenStreetMap).
    Все текстовые поля (street_name, living_area, landmark) извлекаются строго
    по индексам из исходной строки raw_address без исправления опечаток и падежей.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            db_path = Path(__file__).resolve().parents[2] / "data" / "kaz_geo.sqlite"
        self.gazetteer = GeoGazetteer(Path(db_path))

    def parse_batch(self, items: List[RawAddressItem | dict]) -> List[ParsedAddressItem]:
        results: List[ParsedAddressItem] = []
        for raw_item in items:
            item = (
                raw_item
                if isinstance(raw_item, RawAddressItem)
                else RawAddressItem(**raw_item)
            )
            try:
                results.append(self.parse_one(item))
            except Exception:
                # Железное правило ТЗ: пропускать записи нельзя
                results.append(
                    ParsedAddressItem(
                        id=str(item.id),
                        raw_address=item.raw_address,
                        confidence=0.0,
                    )
                )
        return results

    def _lookup_settlement_candidates(
        self, name_str: str
    ) -> List[Tuple[str, str, Optional[str]]]:
        c_norm = normalize_lookup_key(name_str)
        word_count = len(c_norm.split())
        for v in kz_to_ru_lookup_variants(c_norm):
            if len(v.split()) != word_count:
                continue
            matches = self.gazetteer.settlements.get(v, [])
            if matches:
                return matches
        return []

    def parse_one(self, item: RawAddressItem) -> ParsedAddressItem:
        raw = item.raw_address
        if not raw or not raw.strip():
            return ParsedAddressItem(id=str(item.id), raw_address=raw, confidence=0.0)

        span_str = preprocess_with_spans(raw)
        work = span_str.text
        occupied = [False] * len(work)

        def mark_occupied(start: int, end: int) -> None:
            for idx in range(max(0, start), min(len(occupied), end)):
                occupied[idx] = True

        def is_free(start: int, end: int) -> bool:
            return not any(occupied[max(0, start) : min(len(occupied), end)])

        province: Optional[str] = None
        city: Optional[str] = None
        district: Optional[str] = None
        living_area: Optional[str] = None
        street_type: Optional[str] = None
        street_name: Optional[str] = None
        house: Optional[str] = None
        apartment: Optional[str] = None
        entrance: Optional[str] = None
        floor: Optional[str] = None
        landmark: Optional[str] = None

        city_in_text = False

        # =====================================================================
        # ШАГ 2. Итеративный разбор «Шапки» (область, город, посёлок, район)
        # =====================================================================
        # 2.1 Явное указание области в тексте
        for p_pat, p_canon in PROVINCE_PATTERNS:
            for m_p in p_pat.finditer(work):
                if is_free(m_p.start(), m_p.end()):
                    if not province:
                        province = p_canon
                    mark_occupied(m_p.start(), m_p.end())

        # 2.2 Основные города РК и двуязычные дубли через слэш (включая «қ.», «қ-сы», «қаласы»)
        city_patterns = [
            (
                re.compile(
                    r"\b(?:(?:город|г\.?|қаласы|қала|қ-сы|қ\.?)\s+)?алматы(?:\s*/\s*алматы\s+(?:қаласы|қ\.?)|\s+(?:қаласы|қала|қ-сы|қ\.?))?(?=\b|\s|,|$)",
                    re.IGNORECASE,
                ),
                "Алматы",
                "Алматы",
                None,
            ),
            (
                re.compile(
                    r"\b(?:(?:город|г\.?|қаласы|қала|қ-сы|қ\.?)\s+)?(?:астана|нур-султан|нұр-сұлтан)(?:\s*/\s*астана\s+(?:қаласы|қ\.?)|\s+(?:қаласы|қала|қ-сы|қ\.?))?(?=\b|\s|,|$)",
                    re.IGNORECASE,
                ),
                "Астана",
                "Астана",
                None,
            ),
            (
                re.compile(
                    r"\b(?:(?:город|г\.?|қаласы|қала|қ-сы|қ\.?)\s+)?шымкент(?:\s*/\s*шымкент\s+(?:қаласы|қ\.?)|\s+(?:қаласы|қала|қ-сы|қ\.?))?(?=\b|\s|,|$)",
                    re.IGNORECASE,
                ),
                "Шымкент",
                "Шымкент",
                None,
            ),
            (
                re.compile(
                    r"\b(?:(?:город|г\.?|қаласы|қала|қ-сы|қ\.?)\s+)?(?:караганда|қарағанды)(?:\s*/\s*қарағанды\s+(?:қаласы|қ\.?)|\s+(?:қаласы|қала|қ-сы|қ\.?))?(?=\b|\s|,|$)",
                    re.IGNORECASE,
                ),
                "Караганда",
                "Карагандинская область",
                None,
            ),
            (
                re.compile(
                    r"\b(?:(?:город|г\.?|қаласы|қала|қ-сы|қ\.?)\s+)?(?:актобе|ақтөбе)(?:\s*/\s*ақтөбе\s+(?:қаласы|қ\.?)|\s+(?:қаласы|қала|қ-сы|қ\.?))?(?=\b|\s|,|$)",
                    re.IGNORECASE,
                ),
                "Актобе",
                "Актюбинская область",
                None,
            ),
            (
                re.compile(
                    r"\b(?:(?:город|г\.?|қаласы|қала|қ-сы|қ\.?)\s+)?атырау(?:\s*/\s*атырау\s+(?:қаласы|қ\.?)|\s+(?:қаласы|қала|қ-сы|қ\.?))?(?=\b|\s|,|$)",
                    re.IGNORECASE,
                ),
                "Атырау",
                "Атырауская область",
                None,
            ),
            (
                re.compile(
                    r"\b(?:(?:пос\.?|поселок|посёлок|п\.?|кенті|кент|к\.?)\s+)?боралдай(?:\s+(?:кенті|кент|к\.?))?(?=\b|\s|,|$)",
                    re.IGNORECASE,
                ),
                "Боралдай",
                "Алматинская область",
                "Илийский",
            ),
        ]

        for pat, c_name, p_name, def_dist in city_patterns:
            for m in pat.finditer(work):
                # Не захватываем «Алматы»/«Астана» внутри «Алматы ауданы», «район Астана», «мкр Астана», «Астана көшесі»
                before_m = work[: m.start()].rstrip()
                after_m = work[m.end() :].lstrip()
                if re.search(
                    r"\b(?:район|р-н|ауданы|аудан|ауд\.?|мкр\.?|мкрн\.?|микрорайон|шағын\s+аудан(?:ы)?|шағынаудан(?:ы)?|ш/а|ықшам\s+аудан(?:ы)?|ул\.?|улица|пр\.?|проспект|жк|түк|бц|тц|трц)$",
                    before_m,
                    re.I,
                ):
                    continue
                if re.match(
                    r"^(?:район|р-н|ауданы|аудан|ауд\.?|микрорайон(?:ы)?|мкр\b|шағын|ықшам|көшесі|даңғылы|улица|проспект)\b",
                    after_m,
                    re.I,
                ):
                    continue
                if is_free(m.start(), m.end()):
                    if not city:
                        city = c_name
                        if not province:
                            province = p_name
                        city_in_text = True
                        if def_dist and not district:
                            district = def_dist
                    mark_occupied(m.start(), m.end())

        # 2.3 Явные города/сёла/посёлки по префиксу/суффиксу (RU + KZ: «г. Тараз», «Тараз қаласы», «Талдықорған қ.», «Қосшы қаласы», «Ұзынағаш ауылы», «Өтеген батыр кенті»)
        if not city:
            explicit_settle_patterns = [
                re.compile(
                    r"\b(?:(?:город|қаласы|қала|қ-сы|поселок|посёлок|кенті|кент|село|ауылы|ауыл|аул|станциясы|станция)\s+|(?:г\.|қ\.|пос\.|п\.|к\.|с\.|а\.|ст\.)\s*)([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+(?:\s+[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+)?)(?=\s*,|\s+ул|\s+пр|\s+мкр|\s+көш|\s+даң|\s+шағ|\s+ықш|\b)",
                    re.IGNORECASE,
                ),
                re.compile(
                    r"\b([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+(?:\s+(?:батыра|батыр|хана|хан|би|жырау|Қайсенов|Кайсенов))?)\s+(?:қаласы|қала|қ-сы|қ\.|ауылы|ауыл|а\.|кенті|кент|к\.|станциясы)(?=\b|\s|,|$)",
                    re.IGNORECASE,
                ),
            ]
            for s_pat in explicit_settle_patterns:
                for m_s in s_pat.finditer(work):
                    if is_free(m_s.start(), m_s.end()):
                        cand_city = span_str.raw_slice(m_s.start(1), m_s.end(1)).strip(" ,.")
                        if cand_city.lower() in _STREET_STOPWORDS:
                            continue
                        city_end = m_s.end()
                        s_matches = self._lookup_settlement_candidates(cand_city)
                        # Двусловный захват («Рудный Жамбыла», «Талдыкорган ул») — если его нет в КАТО,
                        # берём только первое слово, чтобы не «съесть» улицу
                        cand_words = work[m_s.start(1) : m_s.end(1)].split()
                        if len(cand_words) == 2 and not s_matches:
                            first_end = m_s.start(1) + len(cand_words[0])
                            first_raw = span_str.raw_slice(m_s.start(1), first_end).strip(" ,.")
                            first_matches = self._lookup_settlement_candidates(first_raw)
                            if first_matches or s_pat is explicit_settle_patterns[0]:
                                cand_city, s_matches, city_end = first_raw, first_matches, first_end
                        if s_matches:
                            chosen = s_matches[0]
                            if province:
                                for cand in s_matches:
                                    if cand[1] == province:
                                        chosen = cand
                                        break
                            canon_c, canon_p, canon_d = chosen
                            city = canon_c
                            if not province:
                                province = canon_p
                            if not district and canon_d:
                                district = canon_d
                        else:
                            city = cand_city
                        city_in_text = True
                        mark_occupied(m_s.start(), city_end)
                        break
                if city:
                    break

        # 2.4 Населённый пункт из справочника КАТО в начале свободной части строки
        # а) Сегмент до запятой («Тараз, ...», «Семей, ...», «Абайская область, Семей, ...»)
        if not city:
            free_start = next(
                (i for i, ch in enumerate(work) if not occupied[i] and ch.isalnum()),
                None,
            )
            if free_start is not None:
                next_comma = work.find(",", free_start)
                if next_comma != -1 and is_free(free_start, next_comma):
                    first_seg = work[free_start:next_comma].strip()
                    after_comma = work[next_comma + 1 :].strip()
                    # Защита: если сразу после запятой идёт номер дома («Толе би, 286/4»), то это улица, а не село
                    next_is_house = bool(
                        re.match(r"^(?:дом\b|д\.?\b|үй\b|уй\b|\d+\b)", after_comma, re.I)
                    )
                    if first_seg and not any(ch.isdigit() for ch in first_seg):
                        c_norm = normalize_lookup_key(first_seg)
                        s_matches = self._lookup_settlement_candidates(first_seg)
                        is_known_street = any(
                            v in self.gazetteer.streets_by_norm
                            for v in kz_to_ru_lookup_variants(c_norm)
                        )
                        if s_matches and not (next_is_house and is_known_street):
                            chosen = s_matches[0]
                            if province:
                                for cand in s_matches:
                                    if cand[1] == province:
                                        chosen = cand
                                        break
                            canon_c, canon_p, canon_d = chosen
                            city = canon_c
                            if not province:
                                province = canon_p
                            if not district and canon_d:
                                district = canon_d
                            city_in_text = True
                            mark_occupied(free_start, next_comma + 1)

                # б) Город/село КАТО в начале свободной части без запятой после него
                # («Усть-Каменогорск Азаттык 38/2», «Отеген батыр Макатаева, д 6», «Абайская область, Семей Бухар жырау 174»)
                if not city:
                    tail_free = work[free_start:]
                    for n_words in (2, 1):
                        m_w = re.match(
                            r"^([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+"
                            + (r"\s+[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+" if n_words == 2 else r"")
                            + r")(?=\s)",
                            tail_free,
                        )
                        if not m_w:
                            continue
                        cand_c = m_w.group(1)
                        cand_end = free_start + m_w.end(1)
                        if not is_free(free_start, cand_end):
                            continue
                        s_matches = self._lookup_settlement_candidates(cand_c)
                        if not s_matches:
                            continue
                        rest = tail_free[m_w.end(1) :].lstrip()
                        # После города не должно сразу идти номер дома (без улицы/мкр)
                        # или вторая часть двусловного названия улицы («Абая 15», «Толе би 10»)
                        if re.match(
                            r"^(?:,?\s*(?:дом|д\.?|үй|уй)\s*№?\s*\d)",
                            rest,
                            re.I,
                        ):
                            continue
                        if re.match(
                            r"^\s*\d+(?:/\d+)?[а-яa-z]?(?!\s*(?:-\s*(?:ші|шы)\s*)?(?:квартал|кв-л|микрорайон|мкр|мкрн|шағын|ықшам|аудан))\b",
                            rest,
                            re.I,
                        ):
                            continue
                        if re.match(
                            r"^\s*(?:батыра|батыр|хана|хан|би|жырау|ел|дала|область|обл|облысы)\b",
                            rest,
                            re.I,
                        ):
                            continue
                        # После города обязательно должно быть хотя бы одно буквенное слово (улица/мкр/ориентир)
                        if not re.search(r"[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ]{3,}", rest):
                            continue
                        chosen = s_matches[0]
                        if province:
                            for cand in s_matches:
                                if cand[1] == province:
                                    chosen = cand
                                    break
                        canon_c, canon_p, canon_d = chosen
                        city = canon_c
                        if not province:
                            province = canon_p
                        if not district and canon_d:
                            district = canon_d
                        city_in_text = True
                        mark_occupied(free_start, cand_end)
                        break

        # 2.5 Явный район в строке («Турксибский район», «Есиль район», «Илийский р-н», «Сарыарқа ауданы», «Бостандық ауд.», «Қазыбек би ауданы»)
        # Важно: не путать с «шағын ауданы» / «ықшам ауданы» / «мөлтек ауданы» (это микрорайон!)
        district_patterns = [
            re.compile(
                r"(?<!шағын\s)(?<!шагын\s)(?<!ықшам\s)(?<!ыкшам\s)(?<!мөлтек\s)\b([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+(?:\s+(?:би|хан|хана|батыр|батыра|сал|ақын|жырау|Бөкейхан|Бокейхана|Рысқұлов|Рыскулова))?)\s+(?:район(?:ы)?|р-н|ауданы|аудан|ауд\.?|а-ны)(?=\b|\s|,|$)",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:район|р-н|ауданы|аудан)\s+([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+(?:\s+(?:би|хан|хана|батыр|батыра|Бөкейхан|Бокейхана))?)\b",
                re.IGNORECASE,
            ),
        ]
        for d_pat in district_patterns:
            for m_dist in d_pat.finditer(work):
                cand_d = span_str.raw_slice(m_dist.start(1), m_dist.end(1)).strip(" ,.")
                if cand_d.lower() in ("шағын", "ықшам", "шагын", "ыкшам", "мөлтек", "жилой", "тұрғын"):
                    continue
                if is_free(m_dist.start(), m_dist.end()):
                    district = cand_d
                    mark_occupied(m_dist.start(), m_dist.end())
                    # Если город не был указан, но район однозначно принадлежит городу (напр., «Турксибский», «Медеу», «Бостандық»)
                    if not city:
                        d_norm = normalize_lookup_key(cand_d)
                        for dv in kz_to_ru_lookup_variants(d_norm):
                            u_matches = self.gazetteer.urban_districts.get(dv, [])
                            if len(u_matches) == 1 and u_matches[0][1]:
                                _, city, province = u_matches[0]
                                break
                    break
            if district:
                break

        # =====================================================================
        # ШАГ 3. Детерминированный разбор «Хвоста» (apartment, entrance, floor)
        # =====================================================================
        _prev_prefix_marker_re = re.compile(
            r"(?:дом|д\.?|үй|уй|уч\.?|участок|корпус|корп\.?|блок|стр\.?|"
            r"кв\.?|квартира|пәтер|патер|пәт\.?|flat|kv|офис|оф\.?|каб\.?|кеңсе|"
            r"подъезд|подьезд|п-д|под\.?|кіреберіс|киреберис|кір\.?|"
            r"этаж|эт\.?|қабат|кабат|қаб\.?)\s*№?\s*$",
            re.IGNORECASE,
        )
        _following_own_num_re = re.compile(
            r"^\s*№?\s*(\d+[а-яa-z]?)\b"
            r"(?!\s*(?:-\s*(?:ші|шы|ши|й|ой|ый)\s*)?"
            r"(?:(?:подъезд|подьезд|п-д|под\.?|кіреберіс|киреберис|кір\.?|"
            r"этаж|эт\.?|қабат|кабат|қаб\.?|"
            r"кв\.?|квартира|пәтер|патер|пәт\.?|flat|kv|офис|оф\.?|каб\.?|кеңсе)\b"
            r"(?!\s*№?\s*\d)))",
            re.IGNORECASE,
        )

        def _valid_tail_match(m: re.Match, is_suffix_num_before_kw: bool) -> bool:
            """Проверяет, что число не вырвано из дроби (38/2) и не украдено у соседнего маркера."""
            if not is_free(m.start(), m.end()):
                return False
            num_s, num_e = m.start(1), m.end(1)
            # Число не должно быть частью дроби («38/2», «8/2»)
            if (num_s > 0 and work[num_s - 1] == "/") or (
                num_e < len(work) and work[num_e : num_e + 1] == "/"
            ):
                return False
            if is_suffix_num_before_kw:
                # Перед числом не должен стоять префиксный маркер («д. 101 этаж 12», «кв 207 этаж 22», «корпус 1 подъезд 11»)
                if _prev_prefix_marker_re.search(work[:num_s]):
                    return False
                # После самого ключевого слова не должно идти его собственное число («185 подъезд 9», «85 п-д 12»)
                if _following_own_num_re.match(work[m.end() :]):
                    return False
            return True

        entrance_patterns = [
            (
                re.compile(
                    r"\b(\d+)(?:\s*-\s*(?:ші|шы|ши|й|ой|ый)?)?\s*(?:подъезд|подьезд|п-д|под\.?|кіреберіс|киреберис|кір\.?)(?=\b|\s|,|$)",
                    re.IGNORECASE,
                ),
                True,
            ),
            (
                re.compile(
                    r"\b(?:подъезд|подьезд|п-д|под\.?|кіреберіс|киреберис|кір\.?)\s*№?\s*(\d+)\b",
                    re.IGNORECASE,
                ),
                False,
            ),
        ]
        for pat, is_suf in entrance_patterns:
            for m in pat.finditer(work):
                if _valid_tail_match(m, is_suf):
                    entrance = m.group(1)
                    mark_occupied(m.start(), m.end())
                    break
            if entrance:
                break

        floor_patterns = [
            (
                re.compile(
                    r"\b(\d+)(?:\s*-\s*(?:ші|шы|ши|й|ой|ый)?)?\s*(?:этаж|эт\.?|қабат|кабат|қаб\.?)(?=\b|\s|,|$)",
                    re.IGNORECASE,
                ),
                True,
            ),
            (
                re.compile(
                    r"\b(?:этаж|эт\.?|қабат|кабат|қаб\.?)\s*№?\s*(\d+)\b",
                    re.IGNORECASE,
                ),
                False,
            ),
        ]
        for pat, is_suf in floor_patterns:
            for m in pat.finditer(work):
                if _valid_tail_match(m, is_suf):
                    floor = m.group(1)
                    mark_occupied(m.start(), m.end())
                    break
            if floor:
                break

        apt_patterns = [
            (
                re.compile(
                    r"\b(?:кв\.?|квартира|пәтер|патер|пәт\.?|flat|kv|офис|оф\.?|каб\.?|кеңсе)\s*№?\s*(\d+[а-яa-z]?)\b",
                    re.IGNORECASE,
                ),
                False,
            ),
            (
                re.compile(
                    r"\b(\d+[а-яa-z]?)(?:\s*-\s*(?:ші|шы|ши)?)?\s*(?:кв\.?|квартира|пәтер|патер|пәт\.?|flat|kv|кеңсе)(?=\b|\s|,|$)",
                    re.IGNORECASE,
                ),
                True,
            ),
        ]
        for pat, is_suf in apt_patterns:
            for m in pat.finditer(work):
                if _valid_tail_match(m, is_suf):
                    apartment = m.group(1)
                    mark_occupied(m.start(), m.end())
                    break
            if apartment:
                break

        # =====================================================================
        # ШАГ 4. Разбор «Ядра» (landmark, living_area, street_type, street_name, house)
        # =====================================================================

        # 4.1 Ориентир (landmark), включая перекрёстки (RU + KZ: «уг. ул. ...», «... қиылысы»), ЖК/ТҮК, БЦ, ТЦ/СОО и курьерские пометки
        landmark_patterns = [
            # Казахские послеложные ориентиры после запятой («..., Мега СОО жанында», «..., Еврофарма дәріханасының қарсысында», «..., Панфилов көшесінің қиылысы»)
            re.compile(
                r",\s*([^,\d]+\b(?:қарсысында|жанында|қасында|маңында|артында|алдында|қиылысы|қиылысында|бұрышы|бұрышында|дүкені|дәріханасы)\b[^,]*)",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b((?:уг\.?\s*(?:ул\.?|пр\.?)?|угол(?:\s+улицы)?|пересечение\s+с|магазин|дүкен|дүкені|возле|напротив|рядом|за\s+магазином|ориентир|бағдар|домофон|код\s+домофона|вход\s+со\s+двора|ауладан\s+кіру|позвонить|алдын\s+ала\s+хабарласу|қоңырау\s+шалу|оставить|Qazpost|ТЦ|ТД|ТРЦ|СОО|БЦ|ЖК|ТҮК)\s+[^,]+)",
                re.IGNORECASE,
            ),
        ]
        for pat in landmark_patterns:
            m_lm = pat.search(work)
            if m_lm:
                lm_text = m_lm.group(1)
                cut_tail = re.search(
                    r"\s+\d+(?:\s*-\s*(?:ші|шы|ши)?)?\s*(?:подъезд|подьезд|кіреберіс|киреберис|этаж|эт|қабат|кабат|кв|квартира|пәтер|патер|flat|kv)\b",
                    lm_text,
                    re.IGNORECASE,
                )
                end_pos = m_lm.start(1) + cut_tail.start() if cut_tail else m_lm.end(1)
                if is_free(m_lm.start(1), end_pos):
                    raw_lm = span_str.raw_slice(m_lm.start(1), end_pos).strip(" ,.")
                    if raw_lm:
                        landmark = raw_lm
                        mark_occupied(m_lm.start(1), end_pos)
                    break

        # 4.2 Развилка: есть И микрорайон/жм, И отдельная улица
        # Поддерживает RU и KZ прямой/обратный порядок:
        # - «пос. Боралдай, мкр Водник, ул Абая 1/2»
        # - «Боралдай кенті, Водник шағын ауданы, Абай көшесі 1/2»
        # - «Астана қ., Көктал тұрғын алабы, Наурыз көшесі, 15 үй»
        _mkr_or_la_kw = (
            r"(?:микрорайон(?:ы)?|мкрн\.?|мкр\.?|шағын\s+аудан(?:ы)?|шағынаудан(?:ы)?|шагын\s+аудан(?:ы)?|"
            r"ш/а|ш\.а\.?|ықшам\s+аудан(?:ы)?|ықшамаудан(?:ы)?|ыкшам\s+аудан(?:ы)?|ы/а|ы\.а\.?|"
            r"мөлтек\s+аудан(?:ы)?|мөлтекаудан(?:ы)?|м/а|ж/м|жилмассив|жилой\s+массив|"
            r"тұрғын\s+алабы|тұрғын\s+үй\s+массиві|тұрғын\s+массиві|т/а|елді\s+мекені)"
        )
        _st_type_kw = (
            r"(?:улица|ул\.?|көшесі|кошеси|көше|коше|к-сі|к-си|көш\.?|проспект|просп\.?|пр-т|пр\.?|"
            r"даңғылы|дангылы|даңғыл|дангыл|д-лы|даңғ\.?|переулок|пер\.?|орамы|орам)"
        )
        _st_name_pat = (
            r"([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ0-9-]+(?:\s+(?:батыра|батыр|хана|хан|би|жырау|ел|дала|марта|победы|лет\s+[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ]+))?)"
        )
        dual_patterns = [
            # Префиксный мкр/жм + префиксная улица («мкр Водник, ул Абая»)
            (
                re.compile(
                    rf"\b{_mkr_or_la_kw}(?=\s|\.)\s*\.?\s*([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ0-9-]+(?:\s+\d+[а-яa-z]?)?)\s*,\s*(?:({_st_type_kw})(?=\s|\.)\s*\.?\s*){_st_name_pat}",
                    re.I,
                ),
                1,
                2,
                3,
            ),
            # Префиксный мкр/жм + постфиксная улица («ш/а Водник, Абай көшесі»)
            (
                re.compile(
                    rf"\b{_mkr_or_la_kw}(?=\s|\.)\s*\.?\s*([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ0-9-]+(?:\s+\d+[а-яa-z]?)?)\s*,\s*{_st_name_pat}\s+({_st_type_kw})\b",
                    re.I,
                ),
                1,
                3,
                2,
            ),
            # Постфиксный мкр/жм + постфиксная улица («Водник шағын ауданы, Абай көшесі», «Көктал тұрғын алабы, Наурыз көшесі»)
            (
                re.compile(
                    rf"\b([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ0-9-]+(?:\s+\d+[а-яa-z]?)?)\s+{_mkr_or_la_kw}\s*,\s*{_st_name_pat}\s+({_st_type_kw})\b",
                    re.I,
                ),
                1,
                3,
                2,
            ),
            # Постфиксный мкр/жм + префиксная улица («Көктал тұрғын алабы, көшесі Наурыз»)
            (
                re.compile(
                    rf"\b([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ0-9-]+(?:\s+\d+[а-яa-z]?)?)\s+{_mkr_or_la_kw}\s*,\s*(?:({_st_type_kw})(?=\s|\.)\s*\.?\s*){_st_name_pat}",
                    re.I,
                ),
                1,
                2,
                3,
            ),
            # Числовой квартал/мкр + префиксная улица («66 квартал, ул. Манаса»)
            (
                re.compile(
                    rf"\b(\d+[а-яa-z]?\s+(?:квартал(?:ы)?|кв-л|микрорайон|мкр\.?|шағын\s+аудан(?:ы)?))\s*,\s*(?:({_st_type_kw})(?=\s|\.)\s*\.?\s*){_st_name_pat}",
                    re.I,
                ),
                1,
                2,
                3,
            ),
        ]
        for d_re, la_grp, type_grp, st_grp in dual_patterns:
            m_dual = d_re.search(work)
            if m_dual and is_free(m_dual.start(), m_dual.end()):
                living_area = span_str.raw_slice(m_dual.start(la_grp), m_dual.end(la_grp)).strip(" ,.")
                raw_type_tok = re.sub(r"\s+", " ", m_dual.group(type_grp).lower().rstrip("."))
                street_type = STREET_TYPE_CANONICAL.get(raw_type_tok, "улица")
                street_name = span_str.raw_slice(m_dual.start(st_grp), m_dual.end(st_grp)).strip(" ,.")
                mark_occupied(m_dual.start(), m_dual.end())
                break

        # 4.3 Квартал с числовым названием («66 квартал 12 дом», «66-квартал»)
        if not street_name:
            quarter_patterns = [
                re.compile(r"\b(\d+)(?:\s*-\s*(?:ші|шы|ши)?)?\s*(квартал|кварталы|кв-л)\b", re.IGNORECASE),
                re.compile(r"\b(квартал|кварталы|кв-л)\s*№?\s*(\d+)\b", re.IGNORECASE),
            ]
            for idx_p, q_pat in enumerate(quarter_patterns):
                m_q = q_pat.search(work)
                if m_q and is_free(m_q.start(), m_q.end()):
                    num_group = 1 if idx_p == 0 else 2
                    street_type = "квартал"
                    street_name = span_str.raw_slice(
                        m_q.start(num_group), m_q.end(num_group)
                    ).strip(" ,.")
                    mark_occupied(m_q.start(), m_q.end())
                    break

        # 4.4 Явный тип микрорайона перед буквенным названием («Мкр Аксай 3а, 59», «мкр Орбита-3, д 12а», «ш/а Жетысу-2, 41», «шағын ауданы Ақсай 3а»)
        if not street_name:
            prefix_mkr_re = re.compile(
                r"\b(микрорайон|мкрн\.?|мкр\.?|шағын\s+ауданы|шағын\s+аудан|шағын\s+ауд\.?|шағынауданы|шағынаудан|шагын\s+ауданы|шагын\s+аудан|ш/а|ш\.а\.?|ықшам\s+ауданы|ықшам\s+аудан|ықшам\s+ауд\.?|ықшамауданы|ықшамаудан|ыкшам\s+ауданы|ыкшам\s+аудан|ы/а|ы\.а\.?|мөлтек\s+ауданы|мөлтек\s+аудан|мөлтекауданы|мөлтекаудан|м/а)(?=\s|\.)\s*\.?\s*"
                r"([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z][А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z0-9-]*(?:\s+\d+[а-яa-z]?)?)",
                re.IGNORECASE,
            )
            m_mkr = prefix_mkr_re.search(work)
            if m_mkr and is_free(m_mkr.start(), m_mkr.end()):
                street_type = "микрорайон"
                street_name = span_str.raw_slice(m_mkr.start(2), m_mkr.end(2)).strip(" ,.")
                mark_occupied(m_mkr.start(), m_mkr.end())

        # 4.5 Явный тип улицы/проспекта/переулка ПЕРЕД названием (RU + KZ):
        # поддерживает «ул. 30 лет Победы», «ул. Ш. Калдаякова», «ул. Кабанбай батыра», «ул казибек би»,
        # «даңғылы Қабанбай батыр», «көшесі Абай», «көшесі Бауыржан Момышұлы», «к-сі Сәтбаев»
        if not street_name:
            prefix_street_re = re.compile(
                r"\b(улица|ул\.?|көшесі|кошеси|көше|коше|к-сі|к-си|көш\.?|кош\.?|"
                r"проспект|просп\.?|пр-т|пр\.?|даңғылы|дангылы|даңғыл|дангыл|д-лы|даңғ\.?|данг\.?|"
                r"переулок|пер\.?|орамы|орам|тығырығы|тупик|туп\.?|тұйық\s+көшесі|тұйық\s+көше|"
                r"бульвар|б-р|бульвары|желекжолы|желекжол|шоссе|шоссесі|тас\s+жолы|тасжолы|проезд|пр-д|өткелі|набережная|наб\.?|жағалауы)(?=\s|\.)\s*\.?\s*"
                r"((?:\d+\s+(?:марта|мая|лет\s+[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z-]+|жылдық\s+[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z-]+))"
                r"|(?:[А-ЯЁӘІҢҒҮҰҚӨҺ]\.\s*[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+)"
                r"|(?:(?!дом\b|үй\b|уй\b)[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z][А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z0-9-]*(?:\s+(?!(?:дом|д|үй|уй|уч|участок|корпус|корп|блок|кв|квартира|пәтер|патер|пәт|подъезд|подьезд|кіреберіс|киреберис|этаж|эт|қабат|кабат|уг|угол|қиылысы|бұрышы|возле|напротив|рядом|жанында|қасында|қарсысында|магазин|дүкен|жк|түк|тц|трц|бц|улица|ул|көшесі|проспект|пр|даңғылы|микрорайон|мкр|шағын|ықшам)\b)[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z]{2,})?))",
                re.IGNORECASE,
            )
            for m_pref in prefix_street_re.finditer(work):
                if not is_free(m_pref.start(), m_pref.end()):
                    continue
                # Проверяем, что перед типом улицы в текущем сегменте нет свободного слова (иначе тип улицы — постфиксный, напр. «Абай даңғылы ...»)
                seg_start = work.rfind(",", 0, m_pref.start())
                seg_start = 0 if seg_start == -1 else seg_start + 1
                before_type = work[seg_start : m_pref.start()]
                if any(
                    not occupied[seg_start + idx] and ch.isalpha()
                    for idx, ch in enumerate(before_type)
                ):
                    continue
                t_key = re.sub(r"\s+", " ", m_pref.group(1).lower().rstrip("."))
                street_type = STREET_TYPE_CANONICAL.get(t_key, "улица")
                street_name = span_str.raw_slice(m_pref.start(2), m_pref.end(2)).strip(" ,.")
                mark_occupied(m_pref.start(), m_pref.end())
                break

        # 4.6 Инверсный (постфиксный) порядок типа улицы/микрорайона (основной порядок в казахском языке и частый в русском):
        # «Қабанбай батыр даңғылы», «Бауыржан Момышұлы даңғылы», «Ш. Қалдаяқов көшесі», «Абай көшесі»,
        # «Нурсити 2 микрорайон», «Ақсай 3а шағын ауданы», «Рыбинский переулок», «Алаш тас жолы»
        if not street_name:
            _suf_types = (
                r"(микрорайон(?:ы)?|мкрн\.?|мкр\.?|шағын\s+ауданы|шағын\s+аудан|шағын\s+ауд\.?|шағынауданы|шағынаудан|"
                r"шагын\s+ауданы|шагын\s+аудан|ш/а|ш\.а\.?|ықшам\s+ауданы|ықшам\s+аудан|ықшам\s+ауд\.?|ықшамауданы|ықшамаудан|"
                r"ыкшам\s+ауданы|ыкшам\s+аудан|ы/а|ы\.а\.?|мөлтек\s+ауданы|мөлтек\s+аудан|мөлтекауданы|мөлтекаудан|м/а|"
                r"переулок|пер\.?|орамы|орам|тығырығы|тупик|тұйық\s+көшесі|тұйық\s+көше|"
                r"проспект|просп\.?|пр-т|пр\.?|даңғылы|дангылы|даңғыл|дангыл|д-лы|даңғ\.?|данг\.?|"
                r"улица|ул\.?|көшесі|кошеси|көше|коше|к-сі|к-си|көш\.?|кош\.?|"
                r"бульвар|б-р|бульвары|желекжолы|желекжол|тас\s+жолы|тасжолы|шоссе|шоссесі|жағалауы)"
            )
            # Сначала проверяем двусловные/инициальные/числовые названия («Бауыржан Момышұлы даңғылы», «Қабанбай батыр даңғылы», «Нурсити 2 микрорайон», «Ш. Қалдаяқов көшесі»)
            suffix_multi_re = re.compile(
                rf"\b((?:[А-ЯЁӘІҢҒҮҰҚӨҺ]\.\s*[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+)"
                rf"|(?:\d+(?:-?я|-?ші|-?шы|\s+лет|\s+жылдық)?\s+[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z-]+)"
                rf"|(?:[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z][А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z0-9-]*\s+(?:[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z]{{2,}}|\d+[а-яa-z]?)))\s+"
                rf"{_suf_types}(?=\b|\s|,|$)",
                re.IGNORECASE,
            )
            for m_suf in suffix_multi_re.finditer(work):
                if is_free(m_suf.start(), m_suf.end()):
                    cand_st = span_str.raw_slice(m_suf.start(1), m_suf.end(1)).strip(" ,.")
                    first_w = cand_st.split()[0].lower().rstrip(".")
                    if first_w in _STREET_STOPWORDS:
                        continue
                    street_name = cand_st
                    t_key = re.sub(r"\s+", " ", m_suf.group(2).lower().rstrip("."))
                    street_type = STREET_TYPE_CANONICAL.get(t_key, "улица")
                    mark_occupied(m_suf.start(), m_suf.end())
                    break

            # Если двусловное не нашлось (или первое слово было занято городом), берём однословное («Абай көшесі», «Шакарима даңғылы», «Рыбинский переулок»)
            if not street_name:
                suffix_single_re = re.compile(
                    rf"\b([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z][А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z0-9-]*)\s+{_suf_types}(?=\b|\s|,|$)",
                    re.IGNORECASE,
                )
                for m_suf in suffix_single_re.finditer(work):
                    if is_free(m_suf.start(), m_suf.end()):
                        cand_st = span_str.raw_slice(m_suf.start(1), m_suf.end(1)).strip(" ,.")
                        if cand_st.lower() in _STREET_STOPWORDS:
                            continue
                        street_name = cand_st
                        t_key = re.sub(r"\s+", " ", m_suf.group(2).lower().rstrip("."))
                        street_type = STREET_TYPE_CANONICAL.get(t_key, "улица")
                        mark_occupied(m_suf.start(), m_suf.end())
                        break

        # 4.6b Числовые микрорайоны («Актау, 12 мкр, 34 дом», «Алматы, мкр 8, д 14», «12 шағын аудан», «12-ші ш/а»)
        if not street_name:
            num_mkr_patterns = [
                (
                    re.compile(
                        r"\b(\d+[а-яa-z]?)(?:\s*-\s*(?:ші|шы|ши)?)?\s*(?:микрорайон|мкрн\.?|мкр\.?|шағын\s+ауданы|шағын\s+аудан|шағынауданы|шағынаудан|шагын\s+ауданы|шагын\s+аудан|ш/а|ш\.а\.?|ықшам\s+ауданы|ықшам\s+аудан|ықшамауданы|ықшамаудан|ыкшам\s+ауданы|ыкшам\s+аудан|ы/а|ы\.а\.?|мөлтек\s+ауданы|мөлтек\s+аудан|м/а)(?=\b|\s|,|$)",
                        re.IGNORECASE,
                    ),
                    1,
                ),
                (
                    re.compile(
                        r"\b(?:микрорайон|мкрн\.?|мкр\.?|шағын\s+ауданы|шағын\s+аудан|шағынауданы|шағынаудан|шагын\s+ауданы|шагын\s+аудан|ш/а|ш\.а\.?|ықшам\s+ауданы|ықшам\s+аудан|ықшамауданы|ықшамаудан|ыкшам\s+ауданы|ыкшам\s+аудан|ы/а|ы\.а\.?|мөлтек\s+ауданы|мөлтек\s+аудан|м/а)\s*№?\s*(\d+[а-яa-z]?)(?!\s*(?:дом|үй|уй|кв|квартира|пәтер|патер|подъезд|подьезд|кіреберіс|киреберис|этаж|қабат|кабат)\b)\b",
                        re.IGNORECASE,
                    ),
                    1,
                ),
            ]
            for nm_pat, grp_idx in num_mkr_patterns:
                m_nm = nm_pat.search(work)
                if m_nm and is_free(m_nm.start(), m_nm.end()):
                    street_type = "микрорайон"
                    street_name = span_str.raw_slice(
                        m_nm.start(grp_idx), m_nm.end(grp_idx)
                    ).strip(" ,.")
                    mark_occupied(m_nm.start(), m_nm.end())
                    break

        # 4.7 Беспрефиксная улица + номер дома («Туран 55/6», «Кулманова 133», «жуалы 19», «Астана, Сауран 3/1», «Толе би 286/4», «Бауыржан Момышұлы, 12 үй», «8 Марта 15»)
        if not street_name:
            bare_street_house_re = re.compile(
                r"(?:^|,\s*|(?<=\s))"
                r"((?:\d+\s+(?:марта|мая|лет\s+[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ]+|жылдық\s+[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ]+))"
                r"|(?:[А-ЯЁӘІҢҒҮҰҚӨҺ]\.\s*[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+)"
                r"|(?:[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z-]+(?:\s+(?!(?:дом|д|үй|уй|кв|квартира|пәтер|патер|подъезд|подьезд|кіреберіс|этаж|қабат)\b)[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z]{2,})?))\s*,?\s+"
                r"(?:(?:дом|д\.?|үй|уй)\s*№?\s*)?"
                r"(\d+(?:/\d+)?[а-яa-z]?(?:\s+(?:корпус|корп\.?|блок)\s+[0-9а-яa-z]+)?)(?:\s*-\s*(?:ші|шы|ши)?)?(?:\s*(?:дом|үй|уй))?\b",
                re.IGNORECASE,
            )

            def _segment_prefix_parsed(pos: int) -> bool:
                """Всё, что стоит перед pos в текущем сегменте (до запятой), уже разобрано (город, область)."""
                seg_start = work.rfind(",", 0, pos) + 1
                return all(
                    occupied[i] or not work[i].isalnum() for i in range(seg_start, pos)
                )

            search_pos = 0
            while search_pos < len(work):
                m_bare = bare_street_house_re.search(work, search_pos)
                if not m_bare:
                    break
                search_pos = m_bare.start(1) + 1
                if not is_free(m_bare.start(1), m_bare.end()):
                    continue
                if not _segment_prefix_parsed(m_bare.start(1)):
                    continue
                cand_street = span_str.raw_slice(
                    m_bare.start(1), m_bare.end(1)
                ).strip(" ,.")
                words_low = [w.lower().rstrip(".") for w in cand_street.split()]
                if any(w in _STREET_STOPWORDS or w in ("алматы", "астана", "шымкент") for w in words_low):
                    continue
                street_name = cand_street
                house = span_str.raw_slice(
                    m_bare.start(2), m_bare.end(2)
                ).strip(" ,.")
                mark_occupied(m_bare.start(1), m_bare.end())
                break

        # 4.8 Выделение номера дома (если улица уже найдена, а дом ещё нет), включая казахский маркер «үй» («15 үй», «15-үй», «15-ші үй», «үй 15») и корпуса
        if street_name and not house:
            house_patterns = [
                re.compile(
                    r"\b(?:дом|д\.?|үй|уй|уч\.?|участок)\s*№?\s*(\d+(?:/\d+)?[а-яa-z]?(?:\s+(?:корпус|корп\.?|блок|стр\.?)\s+[0-9а-яa-z]+)?)\b",
                    re.IGNORECASE,
                ),
                re.compile(
                    r"\b(\d+(?:/\d+)?[а-яa-z]?(?:\s+(?:корпус|корп\.?|блок)\s+[0-9а-яa-z]+)?)(?:\s*-\s*(?:ші|шы|ши)?)?\s*(?:дом|үй|уй)\b",
                    re.IGNORECASE,
                ),
                re.compile(
                    r"\b(\d+(?:/\d+)?[а-яa-z]?(?:\s+(?:корпус|корп\.?|блок)\s+[0-9а-яa-z]+)?)\b",
                    re.IGNORECASE,
                ),
            ]
            for h_pat in house_patterns:
                for m_h in h_pat.finditer(work):
                    if is_free(m_h.start(1), m_h.end(1)):
                        house = span_str.raw_slice(m_h.start(1), m_h.end(1)).strip(" ,.")
                        mark_occupied(m_h.start(), m_h.end())
                        break
                if house:
                    break

        # 4.9 Контекстное правило «голого хвоста» после номера дома («Улица Курильская, 9, 2» -> house="9", apartment="2")
        if street_name and house and not apartment:
            bare_apt_re = re.compile(r",\s*(\d+[а-яa-z]?)\s*$")
            m_bapt = bare_apt_re.search(work)
            if m_bapt and is_free(m_bapt.start(1), m_bapt.end(1)):
                apartment = span_str.raw_slice(m_bapt.start(1), m_bapt.end(1)).strip(" ,.")
                mark_occupied(m_bapt.start(), m_bapt.end())

        # Правило ТЗ: если нет отдельной улицы, living_area = None, а мкр в street_name
        if not street_name and living_area:
            street_name = living_area
            street_type = "микрорайон"
            living_area = None

        # =====================================================================
        # ШАГ 5. Гео-обогащение по справочнику kaz_geo.sqlite (ТОЛЬКО для None полей!)
        # =====================================================================
        matched_street_rec = None
        if street_name:
            matched_street_rec = self.gazetteer.lookup_street(
                street_name=street_name,
                city=city,
                street_type_hint=street_type,
                house=house,
            )
            if matched_street_rec:
                if not city:
                    city = matched_street_rec.city
                if not province:
                    province = matched_street_rec.province
                if not street_type and matched_street_rec.street_type:
                    street_type = matched_street_rec.street_type

        if not district and city and street_name:
            b_dist = self.gazetteer.lookup_building_district(city, street_name, house)
            if b_dist:
                district = b_dist
            elif matched_street_rec and matched_street_rec.default_district:
                district = matched_street_rec.default_district

        # =====================================================================
        # ШАГ 6. Расчёт откалиброванного confidence (0.0 .. 1.0)
        # =====================================================================
        if not street_name and not house and not city:
            landmark = None
            confidence = 0.12
        else:
            score = 0.30
            if street_name:
                score += 0.25
            if house:
                score += 0.20
            if city:
                score += 0.12 if city_in_text else 0.06
            if district:
                score += 0.06
            if matched_street_rec:
                score += 0.05
            if apartment or entrance or floor:
                score += 0.03

            # Снижаем уверенность на коротких строках без города в тексте
            if not city_in_text:
                if not district:
                    score = min(score, 0.68)
                elif len(raw.strip().split()) <= 2:
                    score = min(score, 0.64)
                elif street_type == "квартал":
                    score = min(score, 0.66)

            confidence = round(min(0.98, max(0.10, score)), 2)

        return ParsedAddressItem(
            id=str(item.id),
            raw_address=raw,
            province=province,
            city=city,
            district=district,
            living_area=living_area,
            street_type=street_type,
            street_name=street_name,
            house=house,
            apartment=apartment,
            entrance=entrance,
            floor=floor,
            landmark=landmark,
            confidence=confidence,
        )
