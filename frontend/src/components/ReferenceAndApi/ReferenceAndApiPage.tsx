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

  const dictStats = useMemo(() => {
    let streets = 0;
    let microdistricts = 0;
    let settlements = 0;
    for (const item of REFERENCE_DICTIONARY) {
      if (item.category === 'street') streets += 1;
      else if (item.category === 'microdistrict' || item.category === 'quarter')
        microdistricts += 1;
      else settlements += 1;
    }
    return {
      total: REFERENCE_DICTIONARY.length,
      streets,
      microdistricts,
      settlements,
    };
  }, []);

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
        {/* Top Row: API Endpoint + Geo-Database Overview */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <section className="lg:col-span-7 bg-white rounded-lg border border-slate-200 p-5 flex flex-col justify-between gap-4 shadow-2xs">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-slate-900">
                    Подключение к API бэкенда
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Эндпоинт пакетного разбора адресов (POST /api/parse)
                  </p>
                </div>
                <span
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
                    apiOnline
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : 'bg-slate-100 text-slate-600 border-slate-200'
                  }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      apiOnline ? 'bg-emerald-500' : 'bg-slate-400'
                    }`}
                  />
                  {apiOnline ? 'API подключен' : 'Автономный режим'}
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
              Если сервер бэкенда недоступен, интерфейс автоматически переключается на встроенный клиентский парсер.
            </p>
          </section>

          <section className="lg:col-span-5 bg-white rounded-lg border border-slate-200 p-5 flex flex-col justify-between gap-4 shadow-2xs">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-slate-900">
                  Локальный гео-индекс (КАТО + OSM)
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Справочник для восстановления районов и типов улиц
                </p>
              </div>
              <span className="px-2 py-0.5 rounded text-xs font-mono font-medium bg-slate-100 text-slate-700 border border-slate-200">
                SQLite + FTS
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-200/80">
              <div>
                <div className="text-[11px] text-slate-500">Улицы</div>
                <div className="text-base font-mono font-semibold text-slate-900 mt-0.5">
                  {dictStats.streets}
                </div>
              </div>
              <div>
                <div className="text-[11px] text-slate-500">Мкр / Кварталы</div>
                <div className="text-base font-mono font-semibold text-slate-900 mt-0.5">
                  {dictStats.microdistricts}
                </div>
              </div>
              <div>
                <div className="text-[11px] text-slate-500">В выборке</div>
                <div className="text-base font-mono font-semibold text-emerald-700 mt-0.5">
                  {metrics.totalRecords} зап.
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={onRun1000Benchmark}
              className="w-full h-9 px-3 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-800 text-xs font-medium inline-flex items-center justify-center gap-1.5 transition-colors cursor-pointer shadow-2xs"
            >
              <Zap className="w-3.5 h-3.5 text-emerald-600" />
              <span>Загрузить тестовый пакет (1 000 записей)</span>
            </button>
          </section>
        </div>

        {/* Geo-Enrichment Reference Dictionary */}
        <section className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-2xs">
          <div className="p-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">
                Реестр гео-объектов Казахстана
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Соответствие улиц, микрорайонов и кварталов административным районам городов
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

          <div className="overflow-x-auto max-h-96">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="sticky top-0 bg-slate-50 border-b border-slate-200 text-slate-500">
                <tr>
                  <th className="py-2.5 px-4 font-medium">Категория</th>
                  <th className="py-2.5 px-4 font-medium">Объект</th>
                  <th className="py-2.5 px-4 font-medium">Тип (`street_type`)</th>
                  <th className="py-2.5 px-4 font-medium">Город / Область</th>
                  <th className="py-2.5 px-4 font-medium">Район</th>
                  <th className="py-2.5 px-4 font-medium">Алиасы поиска</th>
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
                    <td className="py-2.5 px-4 font-mono text-slate-600 whitespace-nowrap">
                      {item.street_type ?? '—'}
                    </td>
                    <td className="py-2.5 px-4 text-slate-700 whitespace-nowrap">
                      {item.city}{' '}
                      <span className="text-slate-400">({item.province})</span>
                    </td>
                    <td className="py-2.5 px-4 whitespace-nowrap">
                      {item.district ? (
                        <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-medium">
                          {item.district}
                        </span>
                      ) : (
                        <span className="text-slate-300">—</span>
                      )}
                    </td>
                    <td className="py-2.5 px-4 font-mono text-[11px] text-slate-500">
                      {item.aliases.join(', ')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
};
