#!/usr/bin/env python3
"""
Скрипт генерации датасета train.json на 1000 адресов строго на русском языке.
Включает все казахстанские города, улицы, микрорайоны, жилмассивы и сложности ТЗ
(слитное написание 66квартал/11дом/4подьезд/9этаж/69квартира/Назарбаева8, дроби 55/6,
литеры 12а, латиница flat/kv, ориентиры, перекрёстки).
"""

import json
import random
from pathlib import Path

random.seed(42)

CITIES_DATA_RU = [
    ("Алматы", "Алматы", ["Алмалинский", "Ауэзовский", "Бостандыкский", "Медеуский", "Турксибский", "Жетысуский", "Алатауский", "Наурызбайский"]),
    ("Астана", "Астана", ["Есиль", "Алматы", "Байконур", "Сарыарка", "Нура"]),
    ("Шымкент", "Шымкент", ["Абайский", "Аль-Фарабийский", "Енбекшинский", "Каратауский", "Туран"]),
    ("Караганда", "Карагандинская область", ["Казыбек би", "Алихана Бокейхана"]),
    ("Актобе", "Актюбинская область", ["Астана", "Алматы"]),
    ("Тараз", "Жамбылская область", []),
    ("Павлодар", "Павлодарская область", []),
    ("Усть-Каменогорск", "Восточно-Казахстанская область", []),
    ("Семей", "Абайская область", []),
    ("Атырау", "Атырауская область", []),
    ("Кызылорда", "Кызылординская область", []),
    ("Костанай", "Костанайская область", []),
    ("Уральск", "Западно-Казахстанская область", []),
    ("Петропавловск", "Северо-Казахстанская область", []),
    ("Актау", "Мангистауская область", []),
    ("Темиртау", "Карагандинская область", []),
    ("Туркестан", "Туркестанская область", []),
    ("Кокшетау", "Акмолинская область", []),
    ("Талдыкорган", "Жетысуская область", []),
    ("Экибастуз", "Павлодарская область", []),
    ("Рудный", "Костанайская область", []),
    ("Жанаозен", "Мангистауская область", []),
    ("Боралдай", "Алматинская область", ["Илийский"]),
    ("Каскелен", "Алматинская область", ["Карасайский"]),
    ("Талгар", "Алматинская область", ["Талгарский"]),
    ("Кульсары", "Атырауская область", ["Жылыойский"]),
    ("Косшы", "Акмолинская область", []),
    ("Отеген батыр", "Алматинская область", ["Илийский"]),
    ("Узынагаш", "Алматинская область", ["Жамбылский"]),
    ("Бейнеу", "Мангистауская область", ["Бейнеуский"]),
]

STREETS_RU = [
    "Абая", "Толе би", "Кабанбай батыра", "Сейфуллина", "Достык", "Гоголя",
    "Желтоксан", "Байтурсынова", "Кунаева", "Сатпаева", "Макатаева", "Шакарима",
    "Абылай хана", "Райымбека", "Туран", "Сыганак", "Сауран", "Мангилик Ел",
    "Богенбай батыра", "Кенесары", "Республики", "Победы", "Кулманова", "Азаттык",
    "Тауке хана", "Рыскулова", "Момышулы", "Курильская", "Рыбинский переулок",
    "Амангельды", "Жамбыла", "Калдаякова", "Алтынсарина", "Бухар жырау",
    "Сарайшык", "Байзакова", "Манаса", "Жандосова", "Шевченко", "Курмангазы",
    "Ташенова", "Валиханова", "Бараева", "Иманова", "Бейбитшилик"
]

MICRODISTRICTS_RU = [
    "мкр Аксай 1", "мкр Аксай 2", "мкр Аксай 3а", "мкр Аксай 4", "мкр Аксай 5",
    "мкр Самал-1", "мкр Самал-2", "мкр Самал-3", "мкр Орбита-1", "мкр Орбита-2",
    "мкр Орбита-3", "мкр Орбита-4", "мкр Мамыр-1", "мкр Мамыр-4", "мкр Мамыр-7",
    "мкр Шанырак-1", "мкр Шанырак-2", "мкр Алмагуль", "мкр Жетысу-1", "мкр Жетысу-2",
    "мкр Жетысу-3", "мкр Жетысу-4", "мкр Кулагер", "мкр Коктем-1", "мкр Коктем-2",
    "мкр Нурсат", "мкр Восток-1", "мкр Восток-2", "мкр Юго-Восток", "мкр Нурсити 2",
    "12 мкр", "14 мкр", "15 мкр", "17 мкр", "28 мкр", "мкр Гульдер", "мкр Астана",
    "66 квартал", "11 квартал", "12 квартал", "мкр Водник", "мкр Кайрат", "мкр Алтын Бесик"
]

LANDMARKS_RU = [
    "магазин Береке", "ТЦ Азия Парк", "ТРЦ Хан Шатыр", "ТРЦ Mega Park",
    "ТРЦ Достык Плаза", "БЦ Нурлы Тау", "БЦ Алма-Ата", "ЖК Триумф Астаны",
    "ЖК Хайвил", "ЖК Ак Дидар", "ЖК Времена Года", "ЖК Северное Сияние",
    "возле Магнума", "рядом с Small", "напротив школы №15", "возле поликлиники",
    "уг. ул. Абая", "угол Сейфуллина", "вход со двора", "код домофона 45К",
    "позвонить заранее за 15 минут", "оставить у консьержа", "Qazpost Солнечный",
    "аптека Еврофарма", "за базаром", "ЖК Комфорт", "БЦ Москва"
]

def generate_house_num():
    r = random.random()
    if r < 0.50:
        return str(random.randint(1, 195))
    elif r < 0.75:
        return f"{random.randint(1, 150)}/{random.randint(1, 9)}"
    elif r < 0.90:
        litera = random.choice(["а", "б", "в", "г", "А", "Б"])
        return f"{random.randint(1, 120)}{litera}"
    else:
        return f"{random.randint(1, 100)} корпус {random.randint(1, 4)}"

def generate_apartment():
    return random.randint(1, 380)

def generate_entrance():
    return random.randint(1, 12)

def generate_floor():
    return random.randint(1, 25)

def build_single_address_ru(idx):
    city_ru, prov_ru, districts = random.choice(CITIES_DATA_RU)
    
    # 1. Шапка (город / область / район на русском)
    has_city = random.random() > 0.08  # в 8% случаев город опущен для теста гео-обогащения
    city_str = ""
    if has_city:
        cap_style = random.choice(["prefix", "plain", "prefix_dot"])
        if cap_style == "prefix":
            city_str = f"город {city_ru}" if city_ru not in ("Боралдай", "Отеген батыр", "Узынагаш", "Бейнеу") else f"поселок {city_ru}"
        elif cap_style == "prefix_dot":
            city_str = f"г. {city_ru}" if city_ru not in ("Боралдай", "Отеген батыр", "Узынагаш", "Бейнеу") else f"пос. {city_ru}"
        else:
            city_str = city_ru
            
        # Иногда добавляем область
        if random.random() < 0.20 and prov_ru != city_ru:
            city_str = f"{prov_ru}, {city_str}"
                
        # Иногда добавляем район
        if districts and random.random() < 0.25:
            d = random.choice(districts)
            d_str = f"{d} район" if not d.endswith("би") else f"район {d}"
            city_str = f"{city_str}, {d_str}"

    # 2. Ядро адреса (улица vs микрорайон vs жилмассив)
    core_type = random.choices(["street", "mkr_only", "mkr_plus_street", "bare_street"], weights=[0.45, 0.25, 0.15, 0.15])[0]
    
    core_str = ""
    house_val = generate_house_num()
    
    # Формат номера дома (русские маркеры + ТЗ сложность «11дом»)
    h_style = random.choice([
        f"дом {house_val}", f"д. {house_val}", f"д {house_val}", f"{house_val} дом", f"{house_val}дом", house_val
    ])
    
    if core_type == "street":
        st = random.choice(STREETS_RU)
        pref = random.choice(["ул. ", "улица ", "пр. ", "проспект ", "пер. ", "бульвар ", ""])
        # Слитное написание «Назарбаева8» (ловушка ТЗ)
        if random.random() < 0.06 and "/" not in house_val and not house_val[-1].isalpha():
            core_str = f"{pref}{st}{house_val}"
        else:
            core_str = f"{pref}{st}, {h_style}"
            
    elif core_type == "mkr_only":
        mkr = random.choice(MICRODISTRICTS_RU)
        # Слитное написание «66квартал 12дом» (ловушка ТЗ)
        if "66 квартал" in mkr and random.random() < 0.6:
            mkr = "66квартал"
        core_str = f"{mkr}, {h_style}"
        
    elif core_type == "mkr_plus_street":
        # Двойной адрес: мкр Водник, ул Абая 1/2
        mkr = random.choice(MICRODISTRICTS_RU)
        st = random.choice(STREETS_RU)
        core_str = f"{mkr}, ул. {st}, {h_style}"
        
    elif core_type == "bare_street":
        # Беспрефиксная улица («Туран 55/6», «Сауран 3/1», «Толе би 286/4»)
        st = random.choice(STREETS_RU)
        core_str = f"{st} {house_val}"

    # 3. Хвост адреса (квартира, подъезд, этаж на русском + flat/kv)
    tail_parts = []
    has_apt = random.random() < 0.85
    has_ent = random.random() < 0.40
    has_fl = random.random() < 0.35
    
    if has_ent:
        ent_val = generate_entrance()
        tail_parts.append(random.choice([
            f"{ent_val} подъезд", f"{ent_val} подьезд", f"подъезд {ent_val}", f"п-д {ent_val}", f"{ent_val}подьезд"
        ]))
            
    if has_fl:
        fl_val = generate_floor()
        tail_parts.append(random.choice([
            f"{fl_val} этаж", f"{fl_val} эт", f"этаж {fl_val}", f"{fl_val}этаж"
        ]))
            
    if has_apt:
        apt_val = generate_apartment()
        # Русские маркеры, латиница flat/kv и слитное 69квартира из ТЗ
        tail_parts.append(random.choice([
            f"кв {apt_val}", f"кв. {apt_val}", f"квартира {apt_val}", f"{apt_val} кв",
            f"{apt_val}квартира", f"flat {apt_val}", f"kv {apt_val}", f"офис {apt_val}"
        ]))
            
    # Иногда меняем порядок хвоста
    if len(tail_parts) > 1 and random.random() < 0.3:
        random.shuffle(tail_parts)

    # 4. Ориентир (русский)
    lm_str = ""
    if random.random() < 0.35:
        lm_str = random.choice(LANDMARKS_RU)

    # Собираем адрес
    segments = []
    if city_str:
        segments.append(city_str)
    segments.append(core_str)
    if tail_parts:
        segments.extend(tail_parts)
    if lm_str:
        segments.append(lm_str)

    sep = random.choice([", ", " ", ", "])
    raw = sep.join(segments)
    
    # Шум пунктуации («Ул .Курильская», двойные запятые)
    if random.random() < 0.05:
        raw = raw.replace("ул. ", "Ул .").replace(", ,", ",")
        
    return {
        "id": f"rec_{idx + 1:05d}",
        "raw_address": raw.strip(" ,")
    }

def main():
    records = [build_single_address_ru(i) for i in range(1000)]
    
    # Записываем в корень train.json и в data/train.json
    for p in [Path("train.json"), Path("data/train.json")]:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
            
    print(f"Успешно сгенерировано 1000 русскоязычных адресов в train.json и data/train.json")

if __name__ == "__main__":
    main()
