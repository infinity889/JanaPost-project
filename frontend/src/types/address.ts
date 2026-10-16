export interface RawAddressItem {
  id: string;
  raw_address: string;
}

/**
 * Строгий JSON-контракт выходного файла (sample_output.json) и ответа POST /api/parse.
 * Все пустые значения строго null (не "").
 * Строка raw_address возвращается без малейших изменений.
 */
export interface ParsedAddressItem {
  id: string;
  raw_address: string;
  province: string | null;
  city: string | null;
  district: string | null;
  living_area: string | null;
  street_type: string | null;
  street_name: string | null;
  house: string | null;
  apartment: string | null;
  entrance: string | null;
  floor: string | null;
  landmark: string | null;
  confidence: number;
}

/**
 * Внутренняя модель для UI (при экспорте в JSON все вспомогательные поля строго удаляются).
 */
export interface AddressRecordUI extends ParsedAddressItem {
  isEdited?: boolean;
}

export type ActiveTab = 'workspace' | 'analytics' | 'reference';

export type TableFilterTab = 'all' | 'low_confidence' | 'from_db' | 'edited';

export interface ReferenceEntry {
  id: string;
  category: 'street' | 'microdistrict' | 'quarter' | 'district' | 'settlement';
  name: string;
  aliases: string[];
  street_type: string | null;
  city: string;
  province: string;
  district: string | null;
  living_area?: string | null;
  postalZone: string;
  notes?: string;
}

export interface BatchParseMetrics {
  totalRecords: number;
  durationMs: number;
  msPerRecord: number;
  projected1000Ms: number;
  source: 'api' | 'local';
  timestamp: string;
}
