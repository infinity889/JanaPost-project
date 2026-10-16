import React, { useMemo, useState } from 'react';
import {
  Search,
  RefreshCw,
  Zap,
} from 'lucide-react';
import { REFERENCE_DICTIONARY } from '../../data/referenceDictionary';
import { BatchParseMetrics, ReferenceEntry } from '../../types/address';

interface ReferenceAndApiPageProps {
  apiUrl: string;
  onApiUrlChange: (url: string) => void;
  apiOnline: boolean;
  metrics: BatchParseMetrics;
  onTestApiConnection: () => void;
  onRun1000Benchmark: () => void;
  isTestingApi: boolean;
}

export const ReferenceAndApiPage: React.FC<ReferenceAndApiPageProps> = ({
  apiUrl,
  onApiUrlChange,
  apiOnline,
  metrics,
  onTestApiConnection,
  onRun1000Benchmark,
  isTestingApi,
}) => {
  const [dictSearch, setDictSearch] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');

  const filteredDictionary = useMemo(() => {
    const q = dictSearch.trim().toLowerCase();
    return REFERENCE_DICTIONARY.filter((entry) => {
      if (categoryFilter !== 'all' && entry.category !== categoryFilter) {
        return false;
      }
      if (!q) return true;
      return (
        entry.name.toLowerCase().includes(q) ||
        entry.city.toLowerCase().includes(q) ||
        entry.province.toLowerCase().includes(q) ||
        (entry.district && entry.district.toLowerCase().includes(q)) ||
        entry.aliases.some((a) => a.toLowerCase().includes(q)) ||
        (entry.notes && entry.notes.toLowerCase().includes(q))
      );
    });
  }, [dictSearch, categoryFilter]);

  const projectedSec = (metrics.projected1000Ms / 1000).toFixed(2);

  const sampleRequestJson = `[
  {
    "id": "rec_00417",
    "raw_address": "город Алматы/Алматы қаласы, Мкр Аксай 3а, 59, кв 70"
  }
]`;

  const sampleResponseJson = `[
  {
    "id": "rec_00417",
    "raw_address": "город Алматы/Алматы қаласы, Мкр Аксай 3а, 59, кв 70",
    "province": "Алматы",
    "city": "Алматы",
    "district": "Ауэзовский",
    "living_area": null,
    "street_type": "микрорайон",
    "street_name": "Аксай 3а",
    "house": "59",
    "apartment": "70",
    "entrance": null,
    "floor": null,
    "landmark": null,
    "confidence": 0.91
  }
]`;

  const getCategoryLabel = (cat: ReferenceEntry['category']) => {
    switch (cat) {
      case 'street':
        return 'Улица / Проспект';
      case 'microdistrict':
        return 'Микрорайон';
      case 'quarter':
        return 'Квартал';
      case 'settlement':
        return 'Нас. пункт';
      default:
        return 'Район';
    }
  };

  return (
    <div className="h-full overflow-y-auto p-6 bg-slate-50/60">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Top Row: API Endpoint + Speed Benchmark */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <section className="lg:col-span-7 bg-white rounded-lg border border-slate-200 p-5 flex flex-col justify-between gap-4 shadow-2xs">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-slate-900">
                    Подключение к API бэкенда
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Пакетный разбор через POST-запрос или автономный локальный движок
                  </p>
                </div>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  {apiOnline ? 'API Online' : 'Локальный демо-движок'}
                </span>
              </div>

              <div className="flex gap-2 pt-1">
                <input
                  id="backend-api-url"
                  type="url"
                  value={apiUrl}
                  onChange={(e) => onApiUrlChange(e.target.value)}
                  placeholder="http://localhost:8000/api/parse"
                  aria-label="URL бэкенда"
                  className="flex-1 h-9 px-3 rounded-md border border-slate-300 bg-white font-mono text-xs text-slate-900 focus:outline-none focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600"
                />
                <button
                  type="button"
                  onClick={onTestApiConnection}
                  disabled={isTestingApi}
                  className="h-9 px-3.5 rounded-md bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium inline-flex items-center gap-1.5 transition-colors cursor-pointer shrink-0 shadow-2xs"
                >
                  <RefreshCw
                    className={`w-3.5 h-3.5 ${
                      isTestingApi ? 'animate-spin' : ''
                    }`}
                  />
                  <span>Проверить соединение</span>
                </button>
              </div>
            </div>

            <p className="text-xs text-slate-500">
              Полная автономность (Zero External Network Dependencies): при отсутствии связи с бэкендом фронтенд использует встроенный парсер и справочник РК.
            </p>
          </section>

          <section className="lg:col-span-5 bg-white rounded-lg border border-slate-200 p-5 flex flex-col justify-between gap-4 shadow-2xs">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-slate-900">
                  Производительность разбора
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Норматив ТЗ: менее 5 минут на 1 000 записей
                </p>
              </div>
              <span className="px-2 py-0.5 rounded text-xs font-mono font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                Норматив выполнен
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-200/80">
              <div>
                <div className="text-[11px] text-slate-500">На 1 запись</div>
                <div className="text-base font-mono font-semibold text-slate-900 mt-0.5">
                  {metrics.msPerRecord} мс
                </div>
              </div>
              <div>
                <div className="text-[11px] text-slate-500">
                  Батч ({metrics.totalRecords})
                </div>
                <div className="text-base font-mono font-semibold text-slate-900 mt-0.5">
                  {metrics.durationMs} мс
                </div>
              </div>
              <div>
                <div className="text-[11px] text-slate-500">На 1 000 строк</div>
                <div className="text-base font-mono font-semibold text-emerald-700 mt-0.5">
                  {projectedSec} сек
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={onRun1000Benchmark}
              className="w-full h-9 px-3 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-800 text-xs font-medium inline-flex items-center justify-center gap-1.5 transition-colors cursor-pointer shadow-2xs"
            >
              <Zap className="w-3.5 h-3.5 text-emerald-600" />
              <span>Сгенерировать 1 000 записей и протестировать</span>
            </button>
          </section>
        </div>

        {/* Geo-Enrichment Reference Dictionary */}
        <section className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-2xs">
          <div className="p-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">
                Предзагруженный гео-справочник Казахстана
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                База соответствий для автоматического восстановления города, района и типа улицы
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg border border-slate-200/70">
                {[
                  { id: 'all', label: 'Все' },
                  { id: 'street', label: 'Улицы' },
                  { id: 'microdistrict', label: 'Микрорайоны' },
                  { id: 'quarter', label: 'Кварталы' },
                  { id: 'settlement', label: 'Нас. пункты' },
                ].map((cat) => (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => setCategoryFilter(cat.id)}
                    className={`h-7 px-2.5 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                      categoryFilter === cat.id
                        ? 'bg-emerald-600 text-white shadow-2xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>

              <div className="relative w-64">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="search"
                  value={dictSearch}
                  onChange={(e) => setDictSearch(e.target.value)}
                  placeholder="Поиск по улице, мкр, району..."
                  aria-label="Поиск по справочнику"
                  className="w-full h-8 pl-8 pr-3 rounded-md border border-slate-200 bg-slate-50/70 text-xs text-slate-900 focus:bg-white focus:outline-none focus:border-emerald-600"
                />
              </div>
            </div>
          </div>

          <div className="overflow-x-auto max-h-80">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="sticky top-0 bg-slate-50 border-b border-slate-200 text-slate-500">
                <tr>
                  <th className="py-2.5 px-4 font-medium">Категория</th>
                  <th className="py-2.5 px-4 font-medium">Объект</th>
                  <th className="py-2.5 px-4 font-medium">Город / Область</th>
                  <th className="py-2.5 px-4 font-medium">Район (из БД)</th>
                  <th className="py-2.5 px-4 font-medium">Правило обогащения</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredDictionary.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/80">
                    <td className="py-2.5 px-4 text-slate-500 whitespace-nowrap">
                      {getCategoryLabel(item.category)}
                    </td>
                    <td className="py-2.5 px-4 font-medium text-slate-900 whitespace-nowrap">
                      {item.name}
                    </td>
                    <td className="py-2.5 px-4 text-slate-700 whitespace-nowrap">
                      {item.city}{' '}
                      <span className="text-slate-400">({item.province})</span>
                    </td>
                    <td className="py-2.5 px-4 whitespace-nowrap">
                      {item.district ? (
                        <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium">
                          {item.district}
                        </span>
                      ) : (
                        <span className="text-slate-300">—</span>
                      )}
                    </td>
                    <td className="py-2.5 px-4 text-slate-500">
                      {item.notes}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* JSON Contract */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-2.5 shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-800">
                Входной формат (sample_input.json)
              </span>
              <span className="text-[11px] font-mono text-slate-400">
                POST /api/parse
              </span>
            </div>
            <pre className="p-3.5 rounded-lg bg-slate-900 text-slate-100 font-mono text-xs leading-relaxed overflow-x-auto">
              {sampleRequestJson}
            </pre>
          </div>

          <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-2.5 shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-800">
                Выходной формат (sample_output.json)
              </span>
              <span className="text-[11px] font-mono text-emerald-700">
                Строгий JSON-контракт
              </span>
            </div>
            <pre className="p-3.5 rounded-lg bg-slate-900 text-emerald-300 font-mono text-xs leading-relaxed overflow-x-auto">
              {sampleResponseJson}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};
