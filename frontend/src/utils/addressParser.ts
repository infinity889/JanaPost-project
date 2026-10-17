import { DEMO_PARSED_DATASET } from '../data/demoDataset';
import { REFERENCE_DICTIONARY } from '../data/referenceDictionary';
import {
  AddressRecordUI,
  BatchParseMetrics,
  ParsedAddressItem,
  RawAddressItem,
} from '../types/address';

/**
 * Приводит любое строковое значение к string | null.
 * Запрет ТЗ №3: НЕЛЬЗЯ возвращать пустые строки "" вместо null.
 */
export function normalizeNullableString(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  const trimmed = String(value).trim();
  return trimmed.length === 0 ? null : trimmed;
}

/**
 * Строгая очистка записи для экспорта в JSON и отображения чистого JSON объекта.
 * Запрет ТЗ №2: НЕЛЬЗЯ изменять raw_address.
 * Запрет ТЗ №3: НЕЛЬЗЯ возвращать "" вместо null.
 * Запрет ТЗ №4: НЕЛЬЗЯ экспортировать внутренние поля фронтенда (isEdited и др.).
 */
export function toStrictExportItem(record: AddressRecordUI): ParsedAddressItem {
  const conf =
    typeof record.confidence === 'number' && !Number.isNaN(record.confidence)
      ? Math.max(0, Math.min(1, Number(record.confidence.toFixed(2))))
      : 0;

  return {
    id: String(record.id),
    raw_address: record.raw_address, // Строго без малейших изменений
    province: normalizeNullableString(record.province),
    city: normalizeNullableString(record.city),
    district: normalizeNullableString(record.district),
    living_area: normalizeNullableString(record.living_area),
    street_type: normalizeNullableString(record.street_type),
    street_name: normalizeNullableString(record.street_name),
    house: normalizeNullableString(record.house),
    apartment: normalizeNullableString(record.apartment),
    entrance: normalizeNullableString(record.entrance),
    floor: normalizeNullableString(record.floor),
    landmark: normalizeNullableString(record.landmark),
    confidence: conf,
  };
}

/**
 * Проверяет, восстановлено ли поле (district или street_type) из справочника (БД),
 * то есть не входит как подстрока в raw_address (без учета регистра).
 */
export function isFieldFromDb(
  rawAddress: string,
  fieldValue: string | null
): boolean {
  const cleanVal = normalizeNullableString(fieldValue);
  if (!cleanVal) return false;
  return !rawAddress.toLowerCase().includes(cleanVal.toLowerCase());
}

/**
 * Проверяет, обогащена ли запись из справочника (получила district или street_type из БД,
 * хотя их не было как подстроки в тексте raw_address).
 */
export function isRecordEnrichedFromDb(record: ParsedAddressItem): boolean {
  return (
    isFieldFromDb(record.raw_address, record.district) ||
    isFieldFromDb(record.raw_address, record.street_type)
  );
}

/**
 * Проверяет, входит ли введенный street_name как подстрока в raw_address (без учета регистра).
 */
export function isStreetNameSubstringOfRaw(
  rawAddress: string,
  streetName: string | null
): boolean {
  const cleanStreet = normalizeNullableString(streetName);
  if (!cleanStreet) return true;
  return rawAddress.toLowerCase().includes(cleanStreet.toLowerCase());
}

export interface FieldValidationWarnings {
  streetNameNotSubstring: boolean;
  livingAreaWithoutStreet: boolean;
  cityHasServiceWords: boolean;
  districtHasServiceWords: boolean;
  detailsHaveServiceWords: boolean;
}

export function validateAddressRecord(
  record: ParsedAddressItem
): FieldValidationWarnings {
  const streetNameNotSubstring = !isStreetNameSubstringOfRaw(
    record.raw_address,
    record.street_name
  );

  const livingAreaWithoutStreet =
    normalizeNullableString(record.living_area) !== null &&
    normalizeNullableString(record.street_name) === null;

  const cityHasServiceWords = record.city
    ? /(^|\s)(город|г\.|пос\.|поселок|қаласы|ауылы)(\s|$)|[/]/i.test(record.city)
    : false;

  const districtHasServiceWords = record.district
    ? /(^|\s)(район|р-н|ауданы)(\s|$)/i.test(record.district)
    : false;

  const detailsHaveServiceWords = [
    record.apartment,
    record.entrance,
    record.floor,
  ].some((val) =>
    val
      ? /(кв|квартира|flat|подъезд|подьезд|п-д|этаж|эт)(\.|\s|$|[0-9])/i.test(val)
      : false
  );

  return {
    streetNameNotSubstring,
    livingAreaWithoutStreet,
    cityHasServiceWords,
    districtHasServiceWords,
    detailsHaveServiceWords,
  };
}

/**
 * Встроенный детерминированный парсер и модуль гео-обогащения для автономного режима
 * (работает мгновенно в браузере, если бэкенд POST /api/parse недоступен).
 */
export function parseRawAddressLocal(item: RawAddressItem): ParsedAddressItem {
  const raw = item.raw_address;
  const exactDemoMatch = DEMO_PARSED_DATASET.find(
    (d) => d.raw_address.trim().toLowerCase() === raw.trim().toLowerCase()
  );

  if (exactDemoMatch) {
    return toStrictExportItem({
      ...exactDemoMatch,
      id: item.id,
      raw_address: item.raw_address,
    });
  }

  let province: string | null = null;
  let city: string | null = null;
  let district: string | null = null;
  let living_area: string | null = null;
  let street_type: string | null = null;
  let street_name: string | null = null;
  let house: string | null = null;
  let apartment: string | null = null;
  let entrance: string | null = null;
  let floor: string | null = null;
  let landmark: string | null = null;

  // 1. Определение города из текста (без служебных слов "город", "пос." и дубля через слэш)
  const cityPatterns: Array<{ regex: RegExp; city: string; province: string }> = [
    { regex: /(?:город\s+|г\.?\s*)?алматы(?:\s*\/\s*алматы\s+қаласы|\s+қаласы)?/i, city: 'Алматы', province: 'Алматы' },
    { regex: /(?:город\s+|г\.?\s*)?астана(?:\s*\/\s*астана\s+қаласы|\s+қаласы)?/i, city: 'Астана', province: 'Астана' },
    { regex: /(?:город\s+|г\.?\s*)?шымкент(?:\s*\/\s*шымкент\s+қаласы|\s+қаласы)?/i, city: 'Шымкент', province: 'Шымкент' },
    { regex: /(?:город\s+|г\.?\s*)?караганда(?:\s+қаласы)?/i, city: 'Караганда', province: 'Карагандинская область' },
    { regex: /(?:город\s+|г\.?\s*)?актобе(?:\s+қаласы)?/i, city: 'Актобе', province: 'Актюбинская область' },
    { regex: /(?:город\s+|г\.?\s*)?атырау(?:\s+қаласы)?/i, city: 'Атырау', province: 'Атырауская область' },
    { regex: /(?:пос\.?\s+|поселок\s+|п\.?\s*)?боралдай/i, city: 'Боралдай', province: 'Алматинская область' },
  ];

  for (const cp of cityPatterns) {
    if (cp.regex.test(raw)) {
      city = cp.city;
      province = cp.province;
      break;
    }
  }

  // 2. Определение района из текста (без слова "район")
  const districtMatch = raw.match(
    /([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+)\s+(?:район|р-н|ауданы)/i
  );
  if (districtMatch) {
    district = districtMatch[1].trim();
  }

  // 3. Детали курьера: подъезд, этаж, квартира (только номер без служебных слов)
  const entranceMatch =
    raw.match(/(\d+)\s*(?:подъезд|подьезд|п-д)/i) ||
    raw.match(/(?:подъезд|подьезд|п-д)\s*№?\s*(\d+)/i);
  if (entranceMatch) {
    entrance = entranceMatch[1];
  }

  const floorMatch =
    raw.match(/(\d+)\s*(?:этаж|эт\.?)(?:\s|,|$)/i) ||
    raw.match(/(?:этаж|эт\.?)\s*№?\s*(\d+)/i);
  if (floorMatch) {
    floor = floorMatch[1];
  }

  const aptMatch =
    raw.match(/(?:кв\.?|квартира|flat)\s*№?\s*(\d+[а-яa-z]?)/i) ||
    raw.match(/(\d+[а-яa-z]?)\s*(?:кв\.?|квартира|flat)(?:\s|,|$)/i);
  if (aptMatch) {
    apartment = aptMatch[1];
  }

  // 4. Ориентир (landmark)
  const landmarkMatch = raw.match(
    /((?:магазин|возле|напротив|ЖК|ТЦ|домофон|вход\s+со\s+двора)[^,0-9]*[^\s,])/i
  );
  if (landmarkMatch) {
    landmark = landmarkMatch[1]
      .replace(/\s+\d+\s*(?:подъезд|подьезд|этаж|кв).*$/i, '')
      .trim();
  }

  // 5. Квартал (например, "66квартал 12дом 69квартира")
  const quarterMatch =
    raw.match(/(\d+)\s*квартал/i) || raw.match(/квартал\s*(\d+)/i);
  if (quarterMatch) {
    street_type = 'квартал';
    street_name = quarterMatch[1];
  }

  // 6. Поиск по справочнику REFERENCE_DICTIONARY для гео-обогащения и точного выделения улицы/мкр
  const lowerRaw = raw.toLowerCase();
  for (const ref of REFERENCE_DICTIONARY) {
    const matchedAlias = ref.aliases.find((alias) => lowerRaw.includes(alias));
    if (matchedAlias) {
      if (!city) city = ref.city;
      if (!province) province = ref.province;
      if (!district && ref.district) district = ref.district;
      if (!street_type && ref.street_type) street_type = ref.street_type;

      // Вырезаем название ровно как в исходной строке (без изменения регистра и опечаток)
      const nameRegex = new RegExp(
        ref.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
        'i'
      );
      const exactInRaw = raw.match(nameRegex);
      if (exactInRaw) {
        street_name = exactInRaw[0];
      } else {
        // Проверяем алиасы (например, "казибек би")
        for (const al of ref.aliases) {
          const cleanAlias = al
            .replace(/^(ул\.?\s*|пр\.?\s*|мкр\.?\s*|пер\.?\s*)/i, '')
            .trim();
          const aliasRegex = new RegExp(
            cleanAlias.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
            'i'
          );
          const m = raw.match(aliasRegex);
          if (m && cleanAlias.length > 1) {
            street_name = m[0];
            break;
          }
        }
      }
      break;
    }
  }

  // 7. Если тип улицы явно указан в строке, уточняем его и имя улицы
  if (!street_name) {
    const explicitStreetMatch = raw.match(
      /(?:(ул\.?|улица|пр\.?|проспект|мкр\.?|микрорайон|пер\.?|переулок)\s*\.?\s*)([А-Яа-яЁёA-Za-z0-9-]+(?:\s+[0-9а-яА-Яa-zA-Z]+)?)/i
    );
    if (explicitStreetMatch) {
      const rawType = explicitStreetMatch[1].toLowerCase();
      if (rawType.startsWith('ул')) street_type = 'улица';
      else if (rawType.startsWith('пр')) street_type = 'проспект';
      else if (rawType.startsWith('мкр') || rawType.startsWith('микр'))
        street_type = 'микрорайон';
      else if (rawType.startsWith('пер')) street_type = 'переулок';
      street_name = explicitStreetMatch[2].trim();
    } else {
      // Например: "Нурсити 2 микрорайон" или "Рыбинский переулок"
      const reverseStreetMatch = raw.match(
        /([А-Яа-яЁёA-Za-z]+(?:\s+\d+[а-яa-z]?)?)\s+(микрорайон|переулок|проспект|улица)/i
      );
      if (reverseStreetMatch) {
        street_name = reverseStreetMatch[1].trim();
        street_type = reverseStreetMatch[2].toLowerCase();
      }
    }
  }

  // 8. Выделение номера дома (сохраняя дроби и литеры: "55/6", "12а", "1/2")
  const explicitHouseMatch =
    raw.match(/(?:дом|д\.?)\s*№?\s*(\d+(?:\/\d+)?[а-яa-z]?(?:\s*корпус\s*\d+)?)/i) ||
    raw.match(/(\d+(?:\/\d+)?[а-яa-z]?)\s*дом/i);

  if (explicitHouseMatch) {
    house = explicitHouseMatch[1].trim();
  } else if (street_name) {
    const escapedStreet = street_name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const afterStreetRegex = new RegExp(
      `${escapedStreet}(?:\\s+(?:микрорайон|переулок|улица|проспект))?\\s*,?\\s*(?:дом\\s*|д\\.?\\s*)?(\\d+(?:\\/\\d+)?[а-яa-z]?(?:\\s*корпус\\s*\\d+)?)`,
      'i'
    );
    const afterMatch = raw.match(afterStreetRegex);
    if (afterMatch) {
      house = afterMatch[1].trim();
    }
  }

  // Правило ТЗ №8: Если нет отдельной улицы, living_area строго равен null
  if (!street_name && living_area) {
    street_name = living_area;
    street_type = 'микрорайон';
    living_area = null;
  }

  // Вычисление confidence
  let score = 0.25;
  if (city) score += 0.2;
  if (street_name) score += 0.22;
  if (house) score += 0.18;
  if (district) score += 0.06;
  if (apartment || landmark) score += 0.04;
  if (!raw.toLowerCase().includes((city || '').toLowerCase()) && city) {
    // Если город восстановлен только по короткой строке вида "жуалы 19"
    if (raw.trim().split(/\s+/).length <= 2) {
      score = Math.min(score, 0.68);
    }
  }
  if (!street_name && !house) {
    score = 0.2;
  }

  return toStrictExportItem({
    id: item.id,
    raw_address: raw,
    province,
    city,
    district,
    living_area,
    street_type,
    street_name,
    house,
    apartment,
    entrance,
    floor,
    landmark,
    confidence: Number(Math.min(0.98, score).toFixed(2)),
  });
}

/**
 * Пакетный разбор адресов: сначала пытается обратиться к POST /api/parse (или указанному URL),
 * а если бэкенд не запущен — мгновенно разбирает встроенным детерминированным движком.
 */
export async function parseAddressBatch(
  items: Array<RawAddressItem | Partial<ParsedAddressItem>>,
  apiUrl: string,
  preferBackend = true
): Promise<{
  records: AddressRecordUI[];
  metrics: BatchParseMetrics;
  apiOnline: boolean;
}> {
  const startTime = performance.now();

  // Если загружен уже готовый sample_output.json со всеми полями и мы не требуем принудительного переразбора:
  const isAlreadyParsed =
    items.length > 0 &&
    items.every(
      (it) =>
        'confidence' in it &&
        typeof it.confidence === 'number' &&
        ('street_name' in it || 'city' in it)
    );

  if (isAlreadyParsed && !preferBackend) {
    const normalized = items.map((it, idx) =>
      toStrictExportItem({
        id: it.id || `rec_${String(idx + 1).padStart(5, '0')}`,
        raw_address: String(it.raw_address || ''),
        province: (it as ParsedAddressItem).province ?? null,
        city: (it as ParsedAddressItem).city ?? null,
        district: (it as ParsedAddressItem).district ?? null,
        living_area: (it as ParsedAddressItem).living_area ?? null,
        street_type: (it as ParsedAddressItem).street_type ?? null,
        street_name: (it as ParsedAddressItem).street_name ?? null,
        house: (it as ParsedAddressItem).house ?? null,
        apartment: (it as ParsedAddressItem).apartment ?? null,
        entrance: (it as ParsedAddressItem).entrance ?? null,
        floor: (it as ParsedAddressItem).floor ?? null,
        landmark: (it as ParsedAddressItem).landmark ?? null,
        confidence: Number((it as ParsedAddressItem).confidence ?? 0),
      })
    );
    const durationMs = Math.max(1, Number((performance.now() - startTime).toFixed(2)));
    const msPerRecord = Number((durationMs / Math.max(1, normalized.length)).toFixed(3));
    return {
      records: normalized,
      metrics: {
        totalRecords: normalized.length,
        durationMs,
        msPerRecord,
        projected1000Ms: Math.round(msPerRecord * 1000),
        source: 'local',
        timestamp: new Date().toLocaleTimeString('ru-RU'),
      },
      apiOnline: false,
    };
  }

  const rawPayload: RawAddressItem[] = items.map((it, idx) => ({
    id: String(it.id || `rec_${String(idx + 1).padStart(5, '0')}`),
    raw_address: String(it.raw_address || ''),
  }));

  if (preferBackend && apiUrl.trim()) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2500);
      const response = await fetch(apiUrl.trim(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(rawPayload),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (response.ok) {
        const data = await response.json();
        const outputArray: Partial<ParsedAddressItem>[] = Array.isArray(data)
          ? data
          : Array.isArray(data?.results)
          ? data.results
          : [];

        if (outputArray.length === rawPayload.length) {
          const records: AddressRecordUI[] = rawPayload.map((orig, index) => {
            const parsed = outputArray[index] || {};
            return toStrictExportItem({
              id: orig.id,
              raw_address: orig.raw_address, // Запрет ТЗ №2: raw_address строго неизменен
              province: parsed.province ?? null,
              city: parsed.city ?? null,
              district: parsed.district ?? null,
              living_area: parsed.living_area ?? null,
              street_type: parsed.street_type ?? null,
              street_name: parsed.street_name ?? null,
              house: parsed.house ?? null,
              apartment: parsed.apartment ?? null,
              entrance: parsed.entrance ?? null,
              floor: parsed.floor ?? null,
              landmark: parsed.landmark ?? null,
              confidence: typeof parsed.confidence === 'number' ? parsed.confidence : 0,
            });
          });

          const durationMs = Math.max(
            1,
            Number((performance.now() - startTime).toFixed(2))
          );
          const msPerRecord = Number(
            (durationMs / Math.max(1, records.length)).toFixed(3)
          );

          return {
            records,
            metrics: {
              totalRecords: records.length,
              durationMs,
              msPerRecord,
              projected1000Ms: Math.round(msPerRecord * 1000),
              source: 'api',
              timestamp: new Date().toLocaleTimeString('ru-RU'),
            },
            apiOnline: true,
          };
        }
      }
    } catch {
      // Переход в автономный локальный демо-режим без ошибок в консоли
    }
  }

  // Локальный разбор (встроенный демо-режим)
  const localStart = performance.now();
  const records: AddressRecordUI[] = rawPayload.map((rawItem, idx) => {
    const inputCandidate = items[idx] as Partial<ParsedAddressItem>;
    if (
      inputCandidate &&
      typeof inputCandidate.confidence === 'number' &&
      ('street_name' in inputCandidate || 'city' in inputCandidate)
    ) {
      return toStrictExportItem({
        id: rawItem.id,
        raw_address: rawItem.raw_address,
        province: inputCandidate.province ?? null,
        city: inputCandidate.city ?? null,
        district: inputCandidate.district ?? null,
        living_area: inputCandidate.living_area ?? null,
        street_type: inputCandidate.street_type ?? null,
        street_name: inputCandidate.street_name ?? null,
        house: inputCandidate.house ?? null,
        apartment: inputCandidate.apartment ?? null,
        entrance: inputCandidate.entrance ?? null,
        floor: inputCandidate.floor ?? null,
        landmark: inputCandidate.landmark ?? null,
        confidence: inputCandidate.confidence,
      });
    }
    return parseRawAddressLocal(rawItem);
  });

  const durationMs = Math.max(
    0.4,
    Number((performance.now() - localStart).toFixed(2))
  );
  const msPerRecord = Number(
    (durationMs / Math.max(1, records.length)).toFixed(4)
  );

  return {
    records,
    metrics: {
      totalRecords: records.length,
      durationMs,
      msPerRecord,
      projected1000Ms: Math.max(12, Math.round(msPerRecord * 1000)),
      source: 'local',
      timestamp: new Date().toLocaleTimeString('ru-RU'),
    },
    apiOnline: false,
  };
}
