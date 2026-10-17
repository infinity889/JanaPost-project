from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple


INVISIBLE_CHARS = {"\u200b", "\u200c", "\u200d", "\ufeff", "\u2060", "\xad"}

GLUED_KEYWORD_AFTER_DIGIT_RE = re.compile(
    r"^(\d+)("
    r"квартал|кв-л|микрорайон|мкрн|мкр|шағын|ықшам|"
    r"дом|үй|квартира|кв|пәтер|flat|kv|"
    r"подъезд|подьезд|п-д|кіреберіс|этаж|эт|қабат|"
    r"корпус|корп|блок"
    r")\b",
    flags=re.IGNORECASE,
)

# Кириллическое название улицы (>= 4 букв) слитно с номером дома: «Назарбаева8» -> «Назарбаева 8»
GLUED_STREET_AND_HOUSE_RE = re.compile(
    r"^([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ]{4,})(\d+(?:/\d+)?[а-яa-z]?)\b"
)


@dataclass
class SpanString:
    raw: str
    text: str
    norm_to_raw: List[int]

    def raw_slice(self, norm_start: int, norm_end: int) -> str:
        """Возвращает точную подстроку из исходного raw_address по индексам в нормализованной строке."""
        if not self.norm_to_raw or norm_start >= norm_end:
            return ""
        n = len(self.norm_to_raw)
        s_idx = max(0, min(norm_start, n - 1))
        e_idx = max(0, min(norm_end - 1, n - 1))
        raw_start = self.norm_to_raw[s_idx]
        raw_end = self.norm_to_raw[e_idx] + 1
        return self.raw[raw_start:raw_end]


def preprocess_with_spans(raw_address: str) -> SpanString:
    """
    Очищает невидимые символы и безопасно разделяет слитные конструкции
    («66квартал», «11дом», «4подьезд», «9этаж», «69квартира», «Назарбаева8»),
    сохраняя точное посимвольное отображение индексов к исходному raw_address.
    Короткие литеры и дроби («3а», «12а», «55/6», «1/2») НЕ разделяются.
    """
    chars: List[str] = []
    mapping: List[int] = []

    i = 0
    length = len(raw_address)
    while i < length:
        ch = raw_address[i]
        if ch in INVISIBLE_CHARS or (ord(ch) < 32 and ch not in ("\t", "\n", "\r")):
            i += 1
            continue
        if ch in ("\xa0", "\t", "\r", "\n"):
            chars.append(" ")
            mapping.append(i)
            i += 1
            continue

        # Проверяем слитную конструкцию <Цифры><КлючевоеСлово> с позиции i
        tail = raw_address[i:]
        m_digit_kw = GLUED_KEYWORD_AFTER_DIGIT_RE.match(tail)
        if m_digit_kw and (i == 0 or not raw_address[i - 1].isalnum()):
            num_part, kw_part = m_digit_kw.group(1), m_digit_kw.group(2)
            for offset, c in enumerate(num_part):
                chars.append(c)
                mapping.append(i + offset)
            # Вставляем виртуальный разделительный пробел с привязкой к границе
            chars.append(" ")
            mapping.append(i + len(num_part))
            for offset, c in enumerate(kw_part):
                chars.append(c)
                mapping.append(i + len(num_part) + offset)
            i += len(num_part) + len(kw_part)
            continue

        # Проверяем слитную конструкцию <СловоУлицы>=4букв><НомерДома> («Назарбаева8»)
        m_word_num = GLUED_STREET_AND_HOUSE_RE.match(tail)
        if m_word_num and (i == 0 or not raw_address[i - 1].isalnum()):
            word_part, num_part = m_word_num.group(1), m_word_num.group(2)
            # Не разбиваем, если само слово — это служебный маркер («квартал66» обрабатывается отдельно)
            for offset, c in enumerate(word_part):
                chars.append(c)
                mapping.append(i + offset)
            chars.append(" ")
            mapping.append(i + len(word_part))
            for offset, c in enumerate(num_part):
                chars.append(c)
                mapping.append(i + len(word_part) + offset)
            i += len(word_part) + len(num_part)
            continue

        chars.append(ch)
        mapping.append(i)
        i += 1

    return SpanString(raw=raw_address, text="".join(chars), norm_to_raw=mapping)
