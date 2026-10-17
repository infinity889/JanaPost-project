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
    ? /(^|\s)(город|г\.|пос\.|поселок|қаласы|қала|қ\.|ауылы|ауыл|кенті|кент)(\s|$)|[/]/i.test(record.city)
    : false;

  const districtHasServiceWords = record.district
    ? /(^|\s)(район|р-н|ауданы|аудан|ауд\.)(\s|$)/i.test(record.district)
    : false;

  const detailsHaveServiceWords = [
    record.apartment,
    record.entrance,
    record.floor,
  ].some((val) =>
    val
      ? /(кв|квартира|пәтер|патер|flat|подъезд|подьезд|п-д|кіреберіс|киреберис|этаж|эт|қабат|кабат)(\.|\s|$|[0-9])/i.test(val)
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
 * (используется как резервный клиентский парсер, если сервер POST /api/parse недоступен).
 * Никакого сопоставления по полным входным строкам или id не используется.
 */
export function parseRawAddressLocal(item: RawAddressItem): ParsedAddressItem {
  const raw = item.raw_address;

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

  // 1. Определение города и области из текста (включая все 17 областей КАТО 2026 и казахские маркеры)
  const provincePatterns: Array<{ regex: RegExp; province: string }> = [
    { regex: /(?:область\s+абай(?:ская)?|абайская\s+область|абай\s+облысы|облысы\s+абай)/i, province: 'Абайская область' },
    { regex: /(?:область\s+жет[ыі]су(?:ская)?|жет[ыі]суская\s+область|жет[іы]су\s+облысы|облысы\s+жет[іы]су)/i, province: 'Жетысуская область' },
    { regex: /(?:область\s+[уұ]лытау(?:ская)?|[уұ]лытауская\s+область|[ұу]лытау\s+облысы|облысы\s+[ұу]лытау)/i, province: 'Улытауская область' },
    { regex: /(?:область\s+актюбинская|актюбинская\s+область|ақтөбе\s+облысы|облысы\s+ақтөбе)/i, province: 'Актюбинская область' },
    { regex: /(?:область\s+акмолинская|акмолинская\s+область|ақмола\s+облысы|облысы\s+ақмола)/i, province: 'Акмолинская область' },
    { regex: /(?:область\s+алматинская|алматинская\s+область|алматы\s+облысы|облысы\s+алматы)/i, province: 'Алматинская область' },
    { regex: /(?:область\s+атырауская|атырауская\s+область|атырау\s+облысы|облысы\s+атырау)/i, province: 'Атырауская область' },
    { regex: /(?:восточно[-\s]*казахстанская\s+область|шығыс\s+қазақстан\s+облысы)/i, province: 'Восточно-Казахстанская область' },
    { regex: /(?:область\s+жамбылская|жамбылская\s+область|жамбыл\s+облысы|облысы\s+жамбыл)/i, province: 'Жамбылская область' },
    { regex: /(?:западно[-\s]*казахстанская\s+область|батыс\s+қазақстан\s+облысы)/i, province: 'Западно-Казахстанская область' },
    { regex: /(?:область\s+карагандинская|карагандинская\s+область|қарағанды\s+облысы|облысы\s+қарағанды)/i, province: 'Карагандинская область' },
    { regex: /(?:область\s+костанайская|костанайская\s+область|қостанай\s+облысы|облысы\s+қостанай)/i, province: 'Костанайская область' },
    { regex: /(?:область\s+кызылординская|кызылординская\s+область|қызылорда\s+облысы|облысы\s+қызылорда)/i, province: 'Кызылординская область' },
    { regex: /(?:область\s+мангистауская|мангистауская\s+область|маңғыстау\s+облысы|облысы\s+маңғыстау)/i, province: 'Мангистауская область' },
    { regex: /(?:область\s+павлодарская|павлодарская\s+область|павлодар\s+облысы|облысы\s+павлодар)/i, province: 'Павлодарская область' },
    { regex: /(?:северо[-\s]*казахстанская\s+область|солтүстік\s+қазақстан\s+облысы)/i, province: 'Северо-Казахстанская область' },
    { regex: /(?:область\s+туркестанская|туркестанская\s+область|түркістан\s+облысы|облысы\s+түркістан)/i, province: 'Туркестанская область' },
  ];
  for (const pp of provincePatterns) {
    if (pp.regex.test(raw)) {
      province = pp.province;
      break;
    }
  }

  const cityPatterns: Array<{ regex: RegExp; city: string; province: string }> = [
    { regex: /(?:город\s+|г\.?\s*|қаласы\s+|қ\.?\s*)?алматы(?:\s*\/\s*алматы\s+қаласы|\s+(?:қаласы|қ\.?))?/i, city: 'Алматы', province: 'Алматы' },
    { regex: /(?:город\s+|г\.?\s*|қаласы\s+|қ\.?\s*)?(?:астана|нур-султан|нұр-сұлтан)(?:\s*\/\s*астана\s+қаласы|\s+(?:қаласы|қ\.?))?/i, city: 'Астана', province: 'Астана' },
    { regex: /(?:город\s+|г\.?\s*|қаласы\s+|қ\.?\s*)?шымкент(?:\s*\/\s*шымкент\s+қаласы|\s+(?:қаласы|қ\.?))?/i, city: 'Шымкент', province: 'Шымкент' },
    { regex: /(?:город\s+|г\.?\s*|қаласы\s+|қ\.?\s*)?(?:караганда|қарағанды)(?:\s+(?:қаласы|қ\.?))?/i, city: 'Караганда', province: 'Карагандинская область' },
    { regex: /(?:город\s+|г\.?\s*|қаласы\s+|қ\.?\s*)?(?:актобе|ақтөбе)(?:\s*\/\s*ақтөбе\s+қаласы|\s+(?:қаласы|қ\.?))?/i, city: 'Актобе', province: 'Актюбинская область' },
    { regex: /(?:город\s+|г\.?\s*|қаласы\s+|қ\.?\s*)?атырау(?:\s+(?:қаласы|қ\.?))?/i, city: 'Атырау', province: 'Атырауская область' },
    { regex: /(?:город\s+|г\.?\s*|қаласы\s+|қ\.?\s*)?(?:актау|ақтау)(?:\s+(?:қаласы|қ\.?))?/i, city: 'Актау', province: 'Мангистауская область' },
    { regex: /(?:город\s+|г\.?\s*|қаласы\s+|қ\.?\s*)?семей(?:\s+(?:қаласы|қ\.?))?/i, city: 'Семей', province: 'Абайская область' },
    { regex: /(?:город\s+|г\.?\s*|қаласы\s+|қ\.?\s*)?(?:талдыкорган|талдықорған)(?:\s+(?:қаласы|қ\.?))?/i, city: 'Талдыкорган', province: 'Жетысуская область' },
    { regex: /(?:город\s+|г\.?\s*|қаласы\s+|қ\.?\s*)?тараз(?:\s+(?:қаласы|қ\.?))?/i, city: 'Тараз', province: 'Жамбылская область' },
    { regex: /(?:город\s+|г\.?\s*|қаласы\s+|қ\.?\s*)?павлодар(?:\s+(?:қаласы|қ\.?))?/i, city: 'Павлодар', province: 'Павлодарская область' },
    { regex: /(?:город\s+|г\.?\s*|қаласы\s+|қ\.?\s*)?(?:усть-каменогорск|өскемен)(?:\s+(?:қаласы|қ\.?))?/i, city: 'Усть-Каменогорск', province: 'Восточно-Казахстанская область' },
    { regex: /(?:город\s+|г\.?\s*|қаласы\s+|қ\.?\s*)?(?:уральск|орал)(?:\s+(?:қаласы|қ\.?))?/i, city: 'Уральск', province: 'Западно-Казахстанская область' },
    { regex: /(?:город\s+|г\.?\s*|қаласы\s+|қ\.?\s*)?(?:костанай|қостанай)(?:\s+(?:қаласы|қ\.?))?/i, city: 'Костанай', province: 'Костанайская область' },
    { regex: /(?:город\s+|г\.?\s*|қаласы\s+|қ\.?\s*)?(?:кызылорда|қызылорда)(?:\s+(?:қаласы|қ\.?))?/i, city: 'Кызылорда', province: 'Кызылординская область' },
    { regex: /(?:город\s+|г\.?\s*|қаласы\s+|қ\.?\s*)?(?:туркестан|түркістан)(?:\s+(?:қаласы|қ\.?))?/i, city: 'Туркестан', province: 'Туркестанская область' },
    { regex: /(?:город\s+|г\.?\s*|қаласы\s+|қ\.?\s*)?(?:кокшетау|көкшетау)(?:\s+(?:қаласы|қ\.?))?/i, city: 'Кокшетау', province: 'Акмолинская область' },
    { regex: /(?:город\s+|г\.?\s*|қаласы\s+|қ\.?\s*)?(?:петропавловск|петропавл)(?:\s+(?:қаласы|қ\.?))?/i, city: 'Петропавловск', province: 'Северо-Казахстанская область' },
    { regex: /(?:город\s+|г\.?\s*|қаласы\s+|қ\.?\s*)?(?:жезказган|жезқазған)(?:\s+(?:қаласы|қ\.?))?/i, city: 'Жезказган', province: 'Улытауская область' },
    { regex: /(?:город\s+|г\.?\s*|қаласы\s+|қ\.?\s*)?(?:конаев|қонаев)(?:\s+(?:қаласы|қ\.?))?/i, city: 'Конаев', province: 'Алматинская область' },
    { regex: /(?:пос\.?\s+|поселок\s+|п\.?\s*|кенті\s+|к\.?\s*)?боралдай(?:\s+(?:кенті|к\.?))?/i, city: 'Боралдай', province: 'Алматинская область' },
  ];

  for (const cp of cityPatterns) {
    if (cp.regex.test(raw)) {
      city = cp.city;
      if (!province) province = cp.province;
      break;
    }
  }

  // 2. Определение района из текста (без слова "район" и без ложного срабатывания на "шағын ауданы" / "ықшам ауданы")
  const districtMatch = raw.match(
    /(?<!шағын\s)(?<!шагын\s)(?<!ықшам\s)(?<!ыкшам\s)(?<!мөлтек\s)([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+(?:\s+(?:би|хан|хана|батыр|батыра))?)\s+(?:район|р-н|ауданы|аудан|ауд\.)/i
  );
  if (
    districtMatch &&
    !['шағын', 'шагын', 'ықшам', 'ыкшам', 'мөлтек', 'жилой', 'тұрғын'].includes(
      districtMatch[1].trim().toLowerCase()
    )
  ) {
    district = districtMatch[1].trim();
  }

  // 3. Детали курьера: подъезд (RU+KK, включая «2-кіреберіс»), этаж (RU+KK, «7-қабат»), квартира (RU+KK, «42-пәтер»)
  const entranceMatch =
    raw.match(/(\d+)(?:\s*-\s*(?:ші|шы|ши)?)?\s*(?:подъезд|подьезд|п-д|кіреберіс|киреберис|кір\.)/i) ||
    raw.match(/(?:подъезд|подьезд|п-д|кіреберіс|киреберис|кір\.)\s*№?\s*(\d+)/i);
  if (entranceMatch) {
    entrance = entranceMatch[1];
  }

  const floorMatch =
    raw.match(/(\d+)(?:\s*-\s*(?:ші|шы|ши)?)?\s*(?:этаж|эт\.?|қабат|кабат|қаб\.)(?:\s|,|$)/i) ||
    raw.match(/(?:этаж|эт\.?|қабат|кабат|қаб\.)\s*№?\s*(\d+)/i);
  if (floorMatch) {
    floor = floorMatch[1];
  }

  const aptMatch =
    raw.match(/(?:кв\.?|квартира|пәтер|патер|пәт\.?|flat|kv|кеңсе)\s*№?\s*(\d+[а-яa-z]?)/i) ||
    raw.match(/(\d+[а-яa-z]?)(?:\s*-\s*(?:ші|шы|ши)?)?\s*(?:кв\.?|квартира|пәтер|патер|пәт\.?|flat|kv|кеңсе)(?:\s|,|$)/i);
  if (aptMatch) {
    apartment = aptMatch[1];
  }

  // 4. Ориентир (landmark), включая перекрёстки («уг. ул. ...», «... қиылысы») и казахские послелоги («... жанында», «... қарсысында»)
  const landmarkMatch =
    raw.match(
      /((?:уг\.?\s*(?:ул\.?|пр\.?)?|угол(?:\s+улицы)?|магазин|дүкен|дүкені|возле|напротив|рядом|ЖК|ТҮК|ТЦ|ТРЦ|СОО|БЦ|Qazpost|домофон|вход\s+со\s+двора|ауладан\s+кіру)\s+[^,]+)/i
    ) ||
    raw.match(
      /,\s*([^,\d]+\s+(?:қарсысында|жанында|қасында|маңында|артында|алдында|қиылысы|бұрышы)[^,]*)/i
    );
  if (landmarkMatch) {
    landmark = landmarkMatch[1]
      .replace(/\s+\d+(?:\s*-\s*(?:ші|шы|ши)?)?\s*(?:подъезд|подьезд|кіреберіс|киреберис|этаж|қабат|кабат|кв|пәтер|патер).*$/i, '')
      .trim();
  }

  // Рабочая копия без ориентира, чтобы вторая улица перекрёстка («уг. ул. Панфилова») не перезаписывала основную улицу
  const workWithoutLandmark = landmark ? raw.replace(landmark, ' ') : raw;

  // 5. Развилка: есть И микрорайон/жм, И отдельная улица (RU + KK: «пос. Боралдай, мкр Водник, ул Абая 1/2», «Водник шағын ауданы, Абай көшесі 1/2»)
  const mkrAndStreetMatch =
    workWithoutLandmark.match(
      /(?:мкр\.?|микрорайон|шағын\s+аудан(?:ы)?|шағынаудан(?:ы)?|ш\/а|ықшам\s+аудан(?:ы)?|ы\/а|ж\/м|жилмассив|тұрғын\s+алабы|т\/а)\s+([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ0-9-]+)\s*,\s*(?:(ул\.?|улица|көшесі|көше|к-сі|пр\.?|проспект|даңғылы|даңғыл|д-лы|пер\.?|переулок|орамы)\s*\.?\s*)([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ0-9-]+(?:\s+[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ]+)?)/i
    ) ||
    workWithoutLandmark.match(
      /([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ0-9-]+)\s+(?:микрорайон(?:ы)?|шағын\s+аудан(?:ы)?|шағынаудан(?:ы)?|ш\/а|ықшам\s+аудан(?:ы)?|ы\/а|жилмассив|тұрғын\s+алабы|т\/а)\s*,\s*([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ0-9-]+(?:\s+[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ]+)?)\s+(улица|көшесі|көше|к-сі|проспект|даңғылы|даңғыл|д-лы|переулок|орамы)/i
    );
  if (mkrAndStreetMatch) {
    living_area = mkrAndStreetMatch[1].trim();
    const isPost = /(?:көшесі|көше|к-сі|даңғылы|даңғыл|д-лы|орамы|улица|проспект|переулок)$/i.test(
      mkrAndStreetMatch[3]
    );
    const stTypeRaw = (isPost ? mkrAndStreetMatch[3] : mkrAndStreetMatch[2]).toLowerCase();
    street_type =
      stTypeRaw.startsWith('пр') || stTypeRaw.startsWith('даң') || stTypeRaw.startsWith('д-')
        ? 'проспект'
        : stTypeRaw.startsWith('пер') || stTypeRaw.startsWith('орам')
        ? 'переулок'
        : 'улица';
    street_name = (isPost ? mkrAndStreetMatch[2] : mkrAndStreetMatch[3]).trim();
  }

  // 6. Квартал (например, "66квартал 12дом 69квартира")
  const quarterMatch =
    workWithoutLandmark.match(/(\d+)(?:\s*-\s*(?:ші|шы|ши)?)?\s*(?:квартал|кварталы|кв-л)/i) ||
    workWithoutLandmark.match(/(?:квартал|кварталы|кв-л)\s*№?\s*(\d+)/i);
  if (quarterMatch && !street_name) {
    street_type = 'квартал';
    street_name = quarterMatch[1];
  }

  // 7. Явный тип улицы/микрорайона в строке (RU + KK, прямая и обратная конструкция, числовые мкр)
  if (!street_name) {
    const mkrPrefixMatch = workWithoutLandmark.match(
      /(?:(микрорайон|мкрн\.?|мкр\.?|шағын\s+ауданы|шағын\s+аудан|шағынауданы|шағынаудан|ш\/а|ықшам\s+ауданы|ықшам\s+аудан|ықшамауданы|ықшамаудан|ы\/а|мөлтек\s+ауданы|мөлтек\s+аудан|м\/а)\s*\.?\s*)([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z][А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z0-9-]*(?:\s+\d+[а-яa-z]?)?)/i
    );
    if (mkrPrefixMatch) {
      street_type = 'микрорайон';
      street_name = mkrPrefixMatch[2].trim();
    }
  }

  if (!street_name) {
    const explicitStreetMatch = workWithoutLandmark.match(
      /(?:(улица|ул\.?|көшесі|кошеси|көше|коше|к-сі|көш\.?|проспект|просп\.?|пр-т|пр\.?|даңғылы|дангылы|даңғыл|дангыл|д-лы|даңғ\.?|переулок|пер\.?|орамы|орам|бульвар|б-р|желекжолы|шоссе|тас\s+жолы)(?=\s|\.)\s*\.?\s*)((?:\d+(?:-?я|-?ші|-?шы|\s+лет|\s+жылдық)?\s+[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z-]+(?:\s+[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z-]+)?)|(?:[А-ЯЁӘІҢҒҮҰҚӨҺ]\.\s*[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+)|(?:[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z][А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z0-9-]*(?:\s+(?!(?:дом|д|үй|уй|кв|квартира|пәтер|патер|подъезд|подьезд|кіреберіс|этаж|қабат|уг|угол|возле|напротив)(?:\s|,|$))[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z]{2,})?))/i
    );
    if (explicitStreetMatch) {
      const rawType = explicitStreetMatch[1].toLowerCase();
      if (rawType.startsWith('ул') || rawType.startsWith('көш') || rawType.startsWith('кош') || rawType.startsWith('к-'))
        street_type = 'улица';
      else if (rawType.startsWith('пр') || rawType.startsWith('даң') || rawType.startsWith('дан') || rawType.startsWith('д-'))
        street_type = 'проспект';
      else if (rawType.startsWith('пер') || rawType.startsWith('орам'))
        street_type = 'переулок';
      else if (rawType.startsWith('б') || rawType.startsWith('желек'))
        street_type = 'бульвар';
      else if (rawType.startsWith('ш') || rawType.startsWith('тас'))
        street_type = 'шоссе';
      street_name = explicitStreetMatch[2].trim();
    }
  }

  if (!street_name) {
    const reverseStreetMatch = workWithoutLandmark.match(
      /([А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z][А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z0-9-]*(?:\s+(?:[А-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһA-Za-z]{2,}|\d+[а-яa-z]?))?)\s+(микрорайон|шағын\s+ауданы|шағын\s+аудан|шағынауданы|шағынаудан|ш\/а|ықшам\s+ауданы|ықшам\s+аудан|ықшамауданы|ықшамаудан|ы\/а|мөлтек\s+ауданы|мөлтек\s+аудан|м\/а|переулок|орамы|орам|проспект|даңғылы|дангылы|даңғыл|д-лы|даңғ\.?|улица|көшесі|кошеси|көше|к-сі|бульвар|желекжолы|тас\s+жолы|шоссе)/i
    );
    if (reverseStreetMatch) {
      let candName = reverseStreetMatch[1].trim();
      const firstWord = candName.split(/\s+/)[0].toLowerCase().replace(/\.$/, '');
      if (['город', 'қаласы', 'қала', 'қ', 'облысы', 'область', 'район', 'ауданы', 'аудан', 'кенті', 'ауылы'].includes(firstWord)) {
        candName = candName.split(/\s+/).slice(1).join(' ');
      }
      street_name = candName;
      const rt = reverseStreetMatch[2].toLowerCase();
      if (rt.includes('микр') || rt.includes('шағ') || rt.includes('шаг') || rt.includes('ықш') || rt.includes('ыкш') || rt.includes('мөлт') || rt === 'ш/а' || rt === 'ы/а' || rt === 'м/а')
        street_type = 'микрорайон';
      else if (rt.includes('пер') || rt.includes('орам'))
        street_type = 'переулок';
      else if (rt.includes('просп') || rt.includes('даң') || rt.includes('дан') || rt.startsWith('д-'))
        street_type = 'проспект';
      else if (rt.includes('бульв') || rt.includes('желек'))
        street_type = 'бульвар';
      else if (rt.includes('шосс') || rt.includes('тас'))
        street_type = 'шоссе';
      else street_type = 'улица';
    }
  }

  if (!street_name) {
    const numMkrMatch =
      workWithoutLandmark.match(/(\d+[а-яa-z]?)(?:\s*-\s*(?:ші|шы|ши)?)?\s*(?:микрорайон|мкр\.?|шағын\s+ауданы|шағын\s+аудан|ш\/а|ықшам\s+ауданы|ықшам\s+аудан|ы\/а)(?:\s|,|$)/i) ||
      workWithoutLandmark.match(/(?:микрорайон|мкр\.?|шағын\s+ауданы|шағын\s+аудан|ш\/а|ықшам\s+ауданы|ықшам\s+аудан|ы\/а)\s*№?\s*(\d+[а-яa-z]?)(?!\s*(?:дом|үй|уй|кв|пәтер|патер))/i);
    if (numMkrMatch) {
      street_type = 'микрорайон';
      street_name = numMkrMatch[1].trim();
    }
  }

  // 9. Выделение номера дома (сохраняя дроби, литеры, корпуса и казахский маркер «үй» / «15-үй»)
  const explicitHouseMatch =
    workWithoutLandmark.match(/(?:дом|д\.?|үй|уй)\s*№?\s*(\d+(?:\/\d+)?[а-яa-z]?(?:\s*корпус\s*\d+)?)/i) ||
    workWithoutLandmark.match(/(\d+(?:\/\d+)?[а-яa-z]?(?:\s*корпус\s*\d+)?)(?:\s*-\s*(?:ші|шы|ши)?)?\s*(?:дом|үй|уй)/i);

  if (explicitHouseMatch) {
    house = explicitHouseMatch[1].trim();
  } else if (street_name) {
    const escapedStreet = street_name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const afterStreetRegex = new RegExp(
      `${escapedStreet}(?:\\s+(?:микрорайон|шағын\\s+ауданы|шағын\\s+аудан|ықшам\\s+ауданы|переулок|орамы|улица|көшесі|көше|к-сі|проспект|даңғылы|даңғыл|д-лы))?\\s*,?\\s*(?:дом\\s*|д\\.?\\s*|үй\\s*|уй\\s*)?(\\d+(?:\\/\\d+)?[а-яa-z]?(?:\\s*корпус\\s*\\d+)?)`,
      'i'
    );
    const afterMatch = workWithoutLandmark.match(afterStreetRegex);
    if (afterMatch) {
      house = afterMatch[1].trim();
    }
  }

  // Голый хвост квартиры («Улица Курильская, 9, 2»)
  if (street_name && house && !apartment) {
    const bareApt = workWithoutLandmark.match(/,\s*(\d+[а-яa-z]?)\s*$/);
    if (bareApt && bareApt[1] !== house) {
      apartment = bareApt[1];
    }
  }

  // Правило ТЗ №8: Если нет отдельной улицы, living_area строго равен null
  if (!street_name && living_area) {
    street_name = living_area;
    street_type = 'микрорайон';
    living_area = null;
  }

  if (!street_name && !house && !city) {
    landmark = null;
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
