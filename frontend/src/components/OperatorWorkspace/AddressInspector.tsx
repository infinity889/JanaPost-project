import React, { useState } from 'react';
import {
  AlertTriangle,
  ArrowRightLeft,
  Copy,
  Check,
  CheckCircle2,
  Database,
} from 'lucide-react';
import { AddressRecordUI, ParsedAddressItem } from '../../types/address';
import { STREET_TYPE_OPTIONS } from '../../data/referenceDictionary';
import {
  isFieldFromDb,
  normalizeNullableString,
  toStrictExportItem,
  validateAddressRecord,
} from '../../utils/addressParser';

interface AddressInspectorProps {
  record: AddressRecordUI | null;
  onUpdateField: (
    id: string,
    field: keyof ParsedAddressItem,
    value: string | number | null
  ) => void;
  onTransferMkrToStreet: (id: string) => void;
  onConfirmAndNextLow: (id: string) => void;
}

export const AddressInspector: React.FC<AddressInspectorProps> = ({
  record,
  onUpdateField,
  onTransferMkrToStreet,
  onConfirmAndNextLow,
}) => {
  const [viewMode, setViewMode] = useState<'fields' | 'json'>('fields');
  const [copiedJson, setCopiedJson] = useState<boolean>(false);

  if (!record) {
    return (
      <aside className="flex flex-col h-full bg-white items-center justify-center p-6 text-center">
        <p className="text-sm text-slate-400">
          Выберите строку в таблице слева для редактирования
        </p>
      </aside>
    );
  }

  const warnings = validateAddressRecord(record);
  const cleanExportObject = toStrictExportItem(record);
  const pct = Math.round(record.confidence * 100);
  const districtFromDb = isFieldFromDb(record.raw_address, record.district);
  const streetTypeFromDb = isFieldFromDb(record.raw_address, record.street_type);

  const handleTextChange = (
    field: keyof ParsedAddressItem,
    rawVal: string
  ) => {
    const normalized = rawVal.trim() === '' ? null : rawVal;
    onUpdateField(record.id, field, normalized);
  };

  const handleKeyDownForm = (e: React.KeyboardEvent) => {
    if (
      e.key === 'Enter' &&
      (e.metaKey || e.ctrlKey || e.currentTarget === e.target)
    ) {
      e.preventDefault();
      onConfirmAndNextLow(record.id);
    }
  };

  const handleCopyJson = () => {
    navigator.clipboard?.writeText(JSON.stringify(cleanExportObject, null, 2));
    setCopiedJson(true);
    setTimeout(() => setCopiedJson(false), 1800);
  };

  const badgeStyle =
    record.confidence >= 0.85
      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
      : record.confidence >= 0.7
      ? 'bg-slate-100 text-slate-700 border-slate-200'
      : 'bg-amber-50 text-amber-800 border-amber-200';

  const inputClass =
    'w-full h-9 px-3 rounded-md border border-slate-200 bg-white text-sm text-slate-900 placeholder:text-slate-300 focus:outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-600/20 transition-colors';

  return (
    <aside
      aria-label="Инспектор записи"
      className="flex flex-col h-full bg-white overflow-hidden"
    >
      {/* Header: monospace ID, accuracy badge, and [ Поля | JSON ] toggle */}
      <div className="h-12 px-5 border-b border-slate-200 flex items-center justify-between gap-2 shrink-0 bg-white">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-semibold text-slate-900">
            {record.id}
          </span>
          <span
            className={`px-2 py-0.5 rounded-full text-[11px] font-mono font-medium border ${badgeStyle}`}
          >
            {pct}%
          </span>
          {record.isEdited && (
            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
              <CheckCircle2 className="w-3 h-3" />
              Проверено
            </span>
          )}
        </div>

        <div className="inline-flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200/70">
          <button
            type="button"
            onClick={() => setViewMode('fields')}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer ${
              viewMode === 'fields'
                ? 'bg-white text-slate-900 shadow-2xs'
                : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            Поля
          </button>
          <button
            type="button"
            onClick={() => setViewMode('json')}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer ${
              viewMode === 'json'
                ? 'bg-white text-slate-900 shadow-2xs'
                : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            JSON
          </button>
        </div>
      </div>

      {/* Scrollable Inspector Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5 bg-white">
        {/* Read-only raw_address */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium text-slate-500">
              Исходная строка
            </span>
            <span className="text-[11px] text-slate-400">
              Только для чтения
            </span>
          </div>
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs font-mono text-slate-900 leading-relaxed select-all break-words">
            {record.raw_address}
          </div>
        </div>

        {viewMode === 'json' ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500">
                Экспортируемый JSON-объект (sample_output.json)
              </span>
              <button
                type="button"
                onClick={handleCopyJson}
                className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 hover:text-emerald-800 cursor-pointer"
              >
                {copiedJson ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                    <span className="text-emerald-600">Скопировано</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    <span>Копировать</span>
                  </>
                )}
              </button>
            </div>
            <pre className="p-3.5 rounded-lg bg-slate-900 text-emerald-300 font-mono text-xs leading-relaxed overflow-x-auto">
              {JSON.stringify(cleanExportObject, null, 2)}
            </pre>
          </div>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              onConfirmAndNextLow(record.id);
            }}
            onKeyDown={handleKeyDownForm}
            className="space-y-5"
          >
            {/* Group 1: Основной адрес и география */}
            <div className="space-y-3">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                География и адрес
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label
                    htmlFor="field-province"
                    className="block text-xs font-medium text-slate-600 mb-1"
                  >
                    Область
                  </label>
                  <input
                    id="field-province"
                    type="text"
                    value={record.province ?? ''}
                    onChange={(e) =>
                      handleTextChange('province', e.target.value)
                    }
                    placeholder="—"
                    className={inputClass}
                  />
                </div>

                <div>
                  <label
                    htmlFor="field-city"
                    className="block text-xs font-medium text-slate-600 mb-1"
                  >
                    Город
                  </label>
                  <input
                    id="field-city"
                    type="text"
                    value={record.city ?? ''}
                    onChange={(e) => handleTextChange('city', e.target.value)}
                    placeholder="—"
                    className={
                      warnings.cityHasServiceWords
                        ? `${inputClass} border-amber-400 bg-amber-50/30`
                        : inputClass
                    }
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label
                      htmlFor="field-district"
                      className="text-xs font-medium text-slate-600"
                    >
                      Район
                    </label>
                    {districtFromDb && (
                      <span className="inline-flex items-center gap-0.5 text-[10px] font-medium text-slate-500 bg-slate-100 px-1.5 py-0.2 rounded border border-slate-200">
                        <Database className="w-2.5 h-2.5" />
                        из БД
                      </span>
                    )}
                  </div>
                  <input
                    id="field-district"
                    type="text"
                    value={record.district ?? ''}
                    onChange={(e) =>
                      handleTextChange('district', e.target.value)
                    }
                    placeholder="—"
                    className={inputClass}
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label
                      htmlFor="field-living-area"
                      className="text-xs font-medium text-slate-600"
                    >
                      Жилмассив / ЖК
                    </label>
                    {normalizeNullableString(record.living_area) && (
                      <button
                        type="button"
                        onClick={() => onTransferMkrToStreet(record.id)}
                        title="Перенести значение в поле Улица и установить тип «микрорайон»"
                        className="inline-flex items-center gap-1 px-1.5 py-0.2 rounded text-[10px] font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 transition-colors cursor-pointer"
                      >
                        <ArrowRightLeft className="w-2.5 h-2.5" />
                        <span>в Улицу</span>
                      </button>
                    )}
                  </div>
                  <input
                    id="field-living-area"
                    type="text"
                    value={record.living_area ?? ''}
                    onChange={(e) =>
                      handleTextChange('living_area', e.target.value)
                    }
                    placeholder="—"
                    className={inputClass}
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label
                      htmlFor="field-street-type"
                      className="text-xs font-medium text-slate-600"
                    >
                      Тип улицы
                    </label>
                    {streetTypeFromDb && (
                      <span className="inline-flex items-center gap-0.5 text-[10px] font-medium text-slate-500 bg-slate-100 px-1.5 py-0.2 rounded border border-slate-200">
                        <Database className="w-2.5 h-2.5" />
                        из БД
                      </span>
                    )}
                  </div>
                  <select
                    id="field-street-type"
                    value={record.street_type ?? ''}
                    onChange={(e) =>
                      handleTextChange('street_type', e.target.value)
                    }
                    className={inputClass}
                  >
                    {STREET_TYPE_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label
                    htmlFor="field-street-name"
                    className="block text-xs font-medium text-slate-600 mb-1"
                  >
                    Улица / Мкр
                  </label>
                  <input
                    id="field-street-name"
                    type="text"
                    value={record.street_name ?? ''}
                    onChange={(e) =>
                      handleTextChange('street_name', e.target.value)
                    }
                    placeholder="—"
                    className={
                      warnings.streetNameNotSubstring
                        ? `${inputClass} border-amber-400 bg-amber-50/30`
                        : inputClass
                    }
                  />
                </div>

                <div>
                  <label
                    htmlFor="field-house"
                    className="block text-xs font-medium text-slate-600 mb-1"
                  >
                    Дом
                  </label>
                  <input
                    id="field-house"
                    type="text"
                    value={record.house ?? ''}
                    onChange={(e) => handleTextChange('house', e.target.value)}
                    placeholder="—"
                    className={inputClass}
                  />
                </div>

                <div>
                  <label
                    htmlFor="field-apartment"
                    className="block text-xs font-medium text-slate-600 mb-1"
                  >
                    Квартира
                  </label>
                  <input
                    id="field-apartment"
                    type="text"
                    value={record.apartment ?? ''}
                    onChange={(e) =>
                      handleTextChange('apartment', e.target.value)
                    }
                    placeholder="—"
                    className={inputClass}
                  />
                </div>
              </div>

              {warnings.streetNameNotSubstring && (
                <div
                  role="alert"
                  className="p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 flex items-start gap-2 text-xs"
                >
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <span>
                    Подстрока не найдена в исходном адресе (сохраняйте исходное написание без исправления опечаток)
                  </span>
                </div>
              )}
            </div>

            {/* Group 2: Детали доставки */}
            <div className="space-y-3 pt-3 border-t border-slate-100">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Детали доставки
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label
                    htmlFor="field-entrance"
                    className="block text-xs font-medium text-slate-600 mb-1"
                  >
                    Подъезд
                  </label>
                  <input
                    id="field-entrance"
                    type="text"
                    value={record.entrance ?? ''}
                    onChange={(e) =>
                      handleTextChange('entrance', e.target.value)
                    }
                    placeholder="—"
                    className={inputClass}
                  />
                </div>

                <div>
                  <label
                    htmlFor="field-floor"
                    className="block text-xs font-medium text-slate-600 mb-1"
                  >
                    Этаж
                  </label>
                  <input
                    id="field-floor"
                    type="text"
                    value={record.floor ?? ''}
                    onChange={(e) => handleTextChange('floor', e.target.value)}
                    placeholder="—"
                    className={inputClass}
                  />
                </div>

                <div className="col-span-2">
                  <label
                    htmlFor="field-landmark"
                    className="block text-xs font-medium text-slate-600 mb-1"
                  >
                    Ориентир
                  </label>
                  <input
                    id="field-landmark"
                    type="text"
                    value={record.landmark ?? ''}
                    onChange={(e) =>
                      handleTextChange('landmark', e.target.value)
                    }
                    placeholder="—"
                    className={inputClass}
                  />
                </div>
              </div>
            </div>
          </form>
        )}
      </div>

      {/* Sticky Footer Action */}
      <div className="sticky bottom-0 p-4 border-t border-slate-200 bg-slate-50/60 shrink-0">
        <button
          type="button"
          onClick={() => onConfirmAndNextLow(record.id)}
          className="w-full h-9 px-4 rounded-md bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold inline-flex items-center justify-center gap-2 transition-colors shadow-2xs cursor-pointer"
        >
          <CheckCircle2 className="w-4 h-4" />
          <span>Подтвердить и далее (Enter)</span>
        </button>
      </div>
    </aside>
  );
};
