from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple

from app.parser.gazetteer import GeoGazetteer, normalize_lookup_key
from app.parser.preprocessor import SpanString, preprocess_with_spans
from app.schemas import ParsedAddressItem, RawAddressItem


STREET_TYPE_CANONICAL = {
    "ул": "улица",
    "улица": "улица",
    "көшесі": "улица",
    "кошеси": "улица",
    "көше": "улица",
    "к-сі": "улица",
    "пр": "проспект",
    "просп": "проспект",
    "проспект": "проспект",
    "пр-т": "проспект",
    "даңғылы": "проспект",
    "дангылы": "проспект",
    "д-лы": "проспект",
    "мкр": "микрорайон",
    "мкрн": "микрорайон",
    "микрорайон": "микрорайон",
    "шағын ауданы": "микрорайон",
    "шағын аудан": "микрорайон",
    "ш/а": "микрорайон",
    "ш.а": "микрорайон",
    "ықшам ауданы": "микрорайон",
    "ықшам аудан": "микрорайон",
    "ы/а": "микрорайон",
    "пер": "переулок",
    "переулок": "переулок",
    "орамы": "переулок",
    "кв-л": "квартал",
    "квартал": "квартал",
    "б-р": "бульвар",
    "бульвар": "бульвар",
    "ш": "шоссе",
    "шоссе": "шоссе",
    "проезд": "проезд",
    "пр-д": "проезд",
    "тупик": "тупик",
    "туп": "тупик",
    "наб": "набережная",
    "набережная": "набережная",
}

# Прямое отображение всех 17 областей РК (RU/KK, прямой и инверсный порядок) в формат ТЗ
PROVINCE_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(?:область\s+абай(?:ская)?|абайская\s+область|абай\s+облысы)(?:\s*/\s*абай\s+облысы)?\b", re.I), "Абайская область"),
    (re.compile(r"\b(?:область\s+жет[ыі]су(?:ская)?|жет[ыі]суская\s+область|жетісу\s+облысы)(?:\s*/\s*жетісу\s+облысы)?\b", re.I), "Жетысуская область"),
    (re.compile(r"\b(?:область\s+[уұ]лытау(?:ская)?|[уұ]лытауская\s+область|ұлытау\s+облысы)(?:\s*/\s*ұлытау\s+облысы)?\b", re.I), "Улытауская область"),
    (re.compile(r"\b(?:область\s+актюбинская|актюбинская\s+(?:обл\.?|область)|ақтөбе\s+облысы)(?:\s*/\s*ақтөбе\s+облысы)?\b", re.I), "Актюбинская область"),
    (re.compile(r"\b(?:область\s+акмолинская|акмолинская\s+(?:обл\.?|область)|ақмола\s+облысы)(?:\s*/\s*ақмола\s+облысы)?\b", re.I), "Акмолинская область"),
    (re.compile(r"\b(?:область\s+алматинская|алматинская\s+(?:обл\.?|область)|алматы\s+облысы)(?:\s*/\s*алматы\s+облысы)?\b", re.I), "Алматинская область"),
    (re.compile(r"\b(?:область\s+атырауская|атырауская\s+(?:обл\.?|область)|атырау\s+облысы)(?:\s*/\s*атырау\s+облысы)?\b", re.I), "Атырауская область"),
    (re.compile(r"\b(?:восточно[-\s]*казахстанская\s+(?:обл\.?|область)|вко|шығыс\s+қазақстан\s+облысы)\b", re.I), "Восточно-Казахстанская область"),
    (re.compile(r"\b(?:область\s+жамбылская|жамбылская\s+(?:обл\.?|область)|жамбыл\s+облысы)(?:\s*/\s*жамбыл\s+облысы)?\b", re.I), "Жамбылская область"),
    (re.compile(r"\b(?:западно[-\s]*казахстанская\s+(?:обл\.?|область)|зко|батыс\s+қазақстан\s+облысы)\b", re.I), "Западно-Казахстанская область"),
    (re.compile(r"\b(?:область\s+карагандинская|карагандинская\s+(?:обл\.?|область)|қарағанды\s+облысы)(?:\s*/\s*қарағанды\s+облысы)?\b", re.I), "Карагандинская область"),
    (re.compile(r"\b(?:область\s+костанайская|костанайская\s+(?:обл\.?|область)|қостанай\s+облысы)(?:\s*/\s*қостанай\s+облысы)?\b", re.I), "Костанайская область"),
    (re.compile(r"\b(?:область\s+кызылординская|кызылординская\s+(?:обл\.?|область)|қызылорда\s+облысы)(?:\s*/\s*қызылорда\s+облысы)?\b", re.I), "Кызылординская область"),
    (re.compile(r"\b(?:область\s+мангистауская|мангистауская\s+(?:обл\.?|область)|маңғыстау\s+облысы)(?:\s*/\s*маңғыстау\s+облысы)?\b", re.I), "Мангистауская область"),
    (re.compile(r"\b(?:область\s+павлодарская|павлодарская\s+(?:обл\.?|область)|павлодар\s+облысы)(?:\s*/\s*павлодар\s+облысы)?\b", re.I), "Павлодарская область"),
    (re.compile(r"\b(?:северо[-\s]*казахстанская\s+(?:обл\.?|область)|ско|солтүстік\s+қазақстан\s+облысы)\b", re.I), "Северо-Казахстанская область"),
    (re.compile(r"\b(?:область\s+туркестанская|туркестанская\s+(?:обл\.?|область)|южно[-\s]*казахстанская\s+(?:обл\.?|область)|юко|түркістан\s+облысы)\b", re.I), "Туркестанская область"),
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

        # 2.2 Основные города РК и двуязычные дубли через слэш
        city_patterns = [
            (
                re.compile(
                    r"\b(?:(?:город|г\.?)\s+)?алматы(?:\s*/\s*алматы\s+қаласы|\s+қаласы)?\b",
                    re.IGNORECASE,
                ),
                "Алматы",
                "Алматы",
                None,
            ),
            (
                re.compile(
                    r"\b(?:(?:город|г\.?)\s+)?(?:астана|нур-султан)(?:\s*/\s*астана\s+қаласы|\s+қаласы)?\b",
                    re.IGNORECASE,
                ),
                "Астана",
                "Астана",
                None,
            ),
            (
                re.compile(
                    r"\b(?:(?:город|г\.?)\s+)?шымкент(?:\s*/\s*шымкент\s+қаласы|\s+қаласы)?\b",
                    re.IGNORECASE,
                ),
                "Шымкент",
                "Шымкент",
                None,
            ),
            (
                re.compile(
                    r"\b(?:(?:город|г\.?)\s+)?(?:караганда|қарағанды)(?:\s*/\s*қарағанды\s+қаласы|\s+қаласы)?\b",
                    re.IGNORECASE,
                ),
                "Караганда",
                "Карагандинская область",
                None,
            ),
            (
                re.compile(
                    r"\b(?:(?:город|г\.?)\s+)?(?:актобе|ақтөбе)(?:\s*/\s*ақтөбе\s+қаласы|\s+қаласы)?\b",
                    re.IGNORECASE,
                ),
                "Актобе",
                "Актюбинская область",
                None,
            ),
            (
                re.compile(
                    r"\b(?:(?:город|г\.?)\s+)?атырау(?:\s*/\s*атырау\s+қаласы|\s+қаласы)?\b",
                    re.IGNORECASE,
                ),
                "Атырау",
                "Атырауская область",
                None,
            ),
            (
                re.compile(
                    r"\b(?:(?:пос\.?|поселок|посёлок|п\.?)\s+)?боралдай\b",
                    re.IGNORECASE,
                ),
                "Боралдай",
                "Алматинская область",
                "Илийский",
            ),
        ]

        for pat, c_name, p_name, def_dist in city_patterns:
            for m in pat.finditer(work):
                if is_free(m.start(), m.end()):
                    if not city:
                        city = c_name
                        if not province:
                            province = p_name
                        city_in_text = True
                        if def_dist and not district:
                            district = def_dist
                    mark_occupied(m.start(), m.end())

        # 2.3 Явные города/сёла/посёлки по префиксу/суффиксу («г. Тараз», «Тараз қаласы», «с. Каскелен», «Қосшы қаласы»)
        if not city:
            explicit_settle_patterns = [
                re.compile(
                    r"\b(?:город|г\.|пос\.|поселок|посёлок|п\.|село|с\.|аул|а\.)\s*([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+(?:\s+[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+)?)(?=\s*,|\s+ул|\s+пр|\s+мкр|\b)",
                    re.IGNORECASE,
                ),
                re.compile(
                    r"\b([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+)\s+(?:қаласы|ауылы|кенті)\b",
                    re.IGNORECASE,
                ),
            ]
            for s_pat in explicit_settle_patterns:
                m_s = s_pat.search(work)
                if m_s and is_free(m_s.start(), m_s.end()):
                    cand_city = span_str.raw_slice(m_s.start(1), m_s.end(1)).strip(" ,.")
                    c_norm = normalize_lookup_key(cand_city)
                    s_matches = self.gazetteer.settlements.get(c_norm, [])
                    if s_matches:
                        canon_c, canon_p, canon_d = s_matches[0]
                        city = canon_c
                        if not province:
                            province = canon_p
                        if not district and canon_d:
                            district = canon_d
                    else:
                        city = cand_city
                    city_in_text = True
                    mark_occupied(m_s.start(), m_s.end())
                    break

        # 2.4 Первый сегмент до запятой — проверка по справочнику КАТО (напр., «Тараз, ...», «Семей, ...», «Павлодар, ...»)
        if not city and "," in work:
            first_comma = work.find(",")
            first_seg = work[:first_comma].strip()
            if first_seg and is_free(0, first_comma):
                c_norm = normalize_lookup_key(first_seg)
                s_matches = self.gazetteer.settlements.get(c_norm, [])
                if s_matches:
                    canon_c, canon_p, canon_d = s_matches[0]
                    city = canon_c
                    if not province:
                        province = canon_p
                    if not district and canon_d:
                        district = canon_d
                    city_in_text = True
                    mark_occupied(0, first_comma + 1)

        # 2.5 Явный район в строке («Турксибский район», «Есиль район», «Илийский р-н», «Сарыарқа ауданы»)
        # Важно: не путать с «шағын ауданы» / «ықшам ауданы» (это микрорайон!)
        district_patterns = [
            re.compile(
                r"(?<!шағын\s)(?<!ықшам\s)\b([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+)\s+(?:район|р-н|ауданы|аудан)\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(?:район|р-н)\s+([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+)\b",
                re.IGNORECASE,
            ),
        ]
        for d_pat in district_patterns:
            for m_dist in d_pat.finditer(work):
                cand_d = span_str.raw_slice(m_dist.start(1), m_dist.end(1)).strip(" ,.")
                if cand_d.lower() in ("шағын", "ықшам", "шагын", "ыкшам", "жилой"):
                    continue
                if is_free(m_dist.start(), m_dist.end()):
                    district = cand_d
                    mark_occupied(m_dist.start(), m_dist.end())
                    # Если город не был указан, но район однозначно принадлежит городу (напр., «Турксибский»)
                    if not city:
                        d_norm = normalize_lookup_key(cand_d)
                        u_matches = self.gazetteer.urban_districts.get(d_norm, [])
                        if len(u_matches) == 1 and u_matches[0][1]:
                            _, city, province = u_matches[0]
                    break
            if district:
                break

        # =====================================================================
        # ШАГ 3. Детерминированный разбор «Хвоста» (apartment, entrance, floor)
        # =====================================================================
        entrance_patterns = [
            re.compile(r"\b(\d+)\s*(?:подъезд|подьезд|п-д|под\.?|кіреберіс|киреберис)\b", re.IGNORECASE),
            re.compile(r"\b(?:подъезд|подьезд|п-д|под\.?|кіреберіс|киреберис)\s*№?\s*(\d+)\b", re.IGNORECASE),
        ]
        for pat in entrance_patterns:
            m = pat.search(work)
            if m and is_free(m.start(), m.end()):
                entrance = m.group(1)
                mark_occupied(m.start(), m.end())
                break

        floor_patterns = [
            re.compile(r"\b(\d+)\s*(?:этаж|эт\.?|қабат|кабат)(?=\b|\s|,|$)", re.IGNORECASE),
            re.compile(r"\b(?:этаж|эт\.?|қабат|кабат)\s*№?\s*(\d+)\b", re.IGNORECASE),
        ]
        for pat in floor_patterns:
            m = pat.search(work)
            if m and is_free(m.start(), m.end()):
                floor = m.group(1)
                mark_occupied(m.start(), m.end())
                break

        apt_patterns = [
            re.compile(r"\b(?:кв\.?|квартира|пәтер|патер|flat|kv|офис|оф\.?|каб\.?)\s*№?\s*(\d+[а-яa-z]?)\b", re.IGNORECASE),
            re.compile(r"\b(\d+[а-яa-z]?)\s*(?:кв\.?|квартира|пәтер|патер|flat|kv)(?=\b|\s|,|$)", re.IGNORECASE),
        ]
        for pat in apt_patterns:
            m = pat.search(work)
            if m and is_free(m.start(), m.end()):
                apartment = m.group(1)
                mark_occupied(m.start(), m.end())
                break

        # =====================================================================
        # ШАГ 4. Разбор «Ядра» (landmark, living_area, street_type, street_name, house)
        # =====================================================================

        # 4.1 Ориентир (landmark), включая перекрёстки («уг. ул. ...», «угол ...»), ЖК, БЦ, ТЦ и курьерские пометки
        landmark_patterns = [
            re.compile(
                r"\b((?:уг\.?\s*(?:ул\.?|пр\.?)?|угол(?:\s+улицы)?|пересечение\s+с|магазин|возле|напротив|рядом|за\s+магазином|ориентир|домофон|код\s+домофона|вход\s+со\s+двора|позвонить|оставить|Qazpost|ТЦ|ТД|ТРЦ|БЦ|ЖК)\s+[^,]+)",
                re.IGNORECASE,
            ),
        ]
        for pat in landmark_patterns:
            m_lm = pat.search(work)
            if m_lm:
                # Отрезаем случайный захват подъезда/этажа/квартиры в ориентире, если не было запятой
                lm_text = m_lm.group(1)
                cut_tail = re.search(
                    r"\s+\d+\s*(?:подъезд|подьезд|кіреберіс|этаж|эт|қабат|кв|квартира|пәтер|flat|kv)\b",
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

        # 4.2 Развилка: есть И микрорайон/жм, И отдельная улица («пос. Боралдай, мкр Водник, ул Абая 1/2»)
        dual_mkr_street_re = re.compile(
            r"\b(?:микрорайон|мкрн\.?|мкр\.?|шағын\s+аудан(?:ы)?|ш/а|ықшам\s+аудан(?:ы)?|ы/а|ж/м|жилмассив|жилой\s+массив)(?=\s|\.)\s*\.?\s*([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ0-9-]+(?:\s+\d+[а-яa-z]?)?)\s*,\s*"
            r"(?:(улица|ул\.?|проспект|пр\.?|переулок|пер\.?)(?=\s|\.)\s*\.?\s*)"
            r"([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ0-9-]+(?:\s+(?:батыра|хана|би|жырау|ел|дала|марта|победы|лет\s+[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ]+))?)",
            re.IGNORECASE,
        )
        m_dual = dual_mkr_street_re.search(work)
        if m_dual and is_free(m_dual.start(), m_dual.end()):
            living_area = span_str.raw_slice(m_dual.start(1), m_dual.end(1)).strip(" ,.")
            raw_type_tok = m_dual.group(2).lower().rstrip(".")
            street_type = STREET_TYPE_CANONICAL.get(raw_type_tok, "улица")
            street_name = span_str.raw_slice(m_dual.start(3), m_dual.end(3)).strip(" ,.")
            mark_occupied(m_dual.start(), m_dual.end())

        # 4.3 Квартал с числовым названием («66 квартал 12 дом»)
        if not street_name:
            quarter_patterns = [
                re.compile(r"\b(\d+)\s*(квартал|кв-л)\b", re.IGNORECASE),
                re.compile(r"\b(квартал|кв-л)\s*(\d+)\b", re.IGNORECASE),
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

        # 4.4 Явный тип микрорайона перед буквенным названием («Мкр Аксай 3а, 59», «мкр Орбита-3, д 12а», «ш/а Жетысу-2, 41»)
        if not street_name:
            prefix_mkr_re = re.compile(
                r"\b(микрорайон|мкрн\.?|мкр\.?|шағын\s+ауданы|шағын\s+аудан|ш/а|ш\.а\.?|ықшам\s+ауданы|ықшам\s+аудан|ы/а)(?=\s|\.)\s*\.?\s*"
                r"([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z][А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z0-9-]*(?:\s+\d+[а-яa-z]?)?)",
                re.IGNORECASE,
            )
            m_mkr = prefix_mkr_re.search(work)
            if m_mkr and is_free(m_mkr.start(), m_mkr.end()):
                street_type = "микрорайон"
                street_name = span_str.raw_slice(m_mkr.start(2), m_mkr.end(2)).strip(" ,.")
                mark_occupied(m_mkr.start(), m_mkr.end())

        # 4.5 Явный тип улицы/проспекта/переулка перед названием:
        # поддерживает улицы с цифрами («ул. 8 Марта», «пр. 30 лет Победы»), инициалами («ул. Ш. Калдаякова») и двусловные («ул. Кабанбай батыра», «ул казибек би»)
        if not street_name:
            prefix_street_re = re.compile(
                r"\b(улица|ул\.?|проспект|просп\.?|пр-т|пр\.?|переулок|пер\.?|бульвар|б-р|шоссе)(?=\s|\.)\s*\.?\s*"
                r"((?:\d+(?:-?я|\s+лет)?\s+[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z-]+(?:\s+[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z-]+)?)"
                r"|(?:[А-ЯЁӘІҢҒҮҰҚӨҺ]\.\s*[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+)"
                r"|(?:[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z][А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z0-9-]*(?:\s+(?:батыра|батыр|хана|хан|би|жырау|ел|дала|момышулы|кунанбаева|молдагуловой|бокейхана|ташенова|ауэзова|калдаякова|уалиханова|рыскулова|маметовой|байтурсынова|дулатова|аскарова))?))",
                re.IGNORECASE,
            )
            m_pref = prefix_street_re.search(work)
            if m_pref and is_free(m_pref.start(), m_pref.end()):
                t_key = m_pref.group(1).lower().rstrip(".")
                street_type = STREET_TYPE_CANONICAL.get(t_key, "улица")
                street_name = span_str.raw_slice(m_pref.start(2), m_pref.end(2)).strip(" ,.")
                mark_occupied(m_pref.start(), m_pref.end())

        # 4.6 Инверсный порядок типа улицы/микрорайона с буквенным названием (RU + KK: «Нурсити 2 микрорайон», «Рыбинский переулок», «Абай даңғылы», «Жуалы көшесі»)
        if not street_name:
            suffix_street_re = re.compile(
                r"\b([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z][А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z0-9-]*(?:\s+(?:батыра|батыр|хана|хан|би|жырау|ел|дала|\d+[а-яa-z]?))?)\s+"
                r"(микрорайон|шағын\s+ауданы|шағын\s+аудан|ықшам\s+ауданы|ықшам\s+аудан|переулок|орамы|проспект|даңғылы|дангылы|улица|көшесі|кошеси|бульвар)\b",
                re.IGNORECASE,
            )
            m_suf = suffix_street_re.search(work)
            if m_suf and is_free(m_suf.start(), m_suf.end()):
                street_name = span_str.raw_slice(m_suf.start(1), m_suf.end(1)).strip(" ,.")
                t_key = re.sub(r"\s+", " ", m_suf.group(2).lower().rstrip("."))
                street_type = STREET_TYPE_CANONICAL.get(t_key, "улица")
                mark_occupied(m_suf.start(), m_suf.end())

        # 4.6b Числовые микрорайоны («Актау, 12 мкр, 34 дом», «Алматы, мкр 8, д 14», «12 шағын аудан»)
        if not street_name:
            num_mkr_patterns = [
                (
                    re.compile(
                        r"\b(\d+[а-яa-z]?)\s*(?:микрорайон|мкрн\.?|мкр\.?|шағын\s+ауданы|шағын\s+аудан|ш/а|ықшам\s+ауданы|ықшам\s+аудан|ы/а)\b",
                        re.IGNORECASE,
                    ),
                    1,
                ),
                (
                    re.compile(
                        r"\b(?:микрорайон|мкрн\.?|мкр\.?|шағын\s+ауданы|шағын\s+аудан|ш/а|ықшам\s+ауданы|ықшам\s+аудан|ы/а)\s*№?\s*(\d+[а-яa-z]?)(?!\s*(?:дом|үй|кв|квартира|пәтер|подъезд|подьезд|кіреберіс|этаж|қабат)\b)\b",
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

        # 4.7 Беспрефиксная улица + номер дома («Туран 55/6», «Кулманова 133», «жуалы 19», «Астана, Сауран 3/1», «Толе би 286/4», «Розыбакиева 247а корпус 3», «8 Марта 15»)
        if not street_name:
            bare_street_house_re = re.compile(
                r"(?:^|,\s*)"
                r"((?:\d+\s+(?:марта|мая|лет\s+[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ]+))|(?:[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z-]+(?:\s+(?:батыра|батыр|хана|хан|би|жырау|ел|дала))?))\s*,?\s+"
                r"(?:(?:дом|д\.?|үй)\s*№?\s*)?"
                r"(\d+(?:/\d+)?[а-яa-z]?(?:\s+(?:корпус|корп\.?|блок)\s+[0-9а-яa-z]+)?)\b",
                re.IGNORECASE,
            )
            for m_bare in bare_street_house_re.finditer(work):
                if is_free(m_bare.start(1), m_bare.end(2)):
                    cand_street = span_str.raw_slice(
                        m_bare.start(1), m_bare.end(1)
                    ).strip(" ,.")
                    # Отсекаем случайные слова-триггеры
                    if cand_street.lower() not in (
                        "город",
                        "алматы",
                        "астана",
                        "шымкент",
                        "дом",
                        "үй",
                        "кв",
                        "квартира",
                        "пәтер",
                        "подъезд",
                        "подьезд",
                        "кіреберіс",
                        "этаж",
                        "қабат",
                    ):
                        street_name = cand_street
                        house = span_str.raw_slice(
                            m_bare.start(2), m_bare.end(2)
                        ).strip(" ,.")
                        mark_occupied(m_bare.start(1), m_bare.end(2))
                        break

        # 4.8 Выделение номера дома (если улица уже найдена, а дом ещё нет), включая казахский маркер «үй» и корпуса
        if street_name and not house:
            house_patterns = [
                re.compile(
                    r"\b(?:дом|д\.?|үй|уч\.?|участок)\s*№?\s*(\d+(?:/\d+)?[а-яa-z]?(?:\s+(?:корпус|корп\.?|блок|стр\.?)\s+[0-9а-яa-z]+)?)\b",
                    re.IGNORECASE,
                ),
                re.compile(
                    r"\b(\d+(?:/\d+)?[а-яa-z]?(?:\s+(?:корпус|корп\.?|блок)\s+[0-9а-яa-z]+)?)\s*(?:дом|үй)\b",
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
