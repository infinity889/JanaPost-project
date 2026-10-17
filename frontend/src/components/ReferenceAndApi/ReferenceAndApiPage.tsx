import React, { useEffect, useState } from 'react';
import { Search, RefreshCw } from 'lucide-react';
import { BatchParseMetrics, ReferenceEntry } from '../../types/address';

interface ReferenceAndApiPageProps {
  apiUrl: string;
  onApiUrlChange: (url: string) => void;
  apiOnline: boolean;
  metrics: BatchParseMetrics;
  onTestApiConnection: () => void;
  isTestingApi: boolean;
}

export const ReferenceAndApiPage: React.FC<ReferenceAndApiPageProps> = ({
  apiUrl,
  onApiUrlChange,
  apiOnline,
  metrics,
  onTestApiConnection,
  isTestingApi,
}) => {
  const [dictSearch, setDictSearch] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [entries, setEntries] = useState<ReferenceEntry[]>([]);
  const [totalSettlements, setTotalSettlements] = useState<number>(0);
  const [totalStreets, setTotalStreets] = useState<number>(0);
  const [isLoadingDict, setIsLoadingDict] = useState<boolean>(false);

  const baseApiOrigin = apiUrl.replace(/\/(?:api\/)?parse\/?$/, '');

  useEffect(() => {
    let cancelled = false;
    setIsLoadingDict(true);

    const timer = setTimeout(async () => {
      const params = new URLSearchParams({
        q: dictSearch.trim(),
        category: categoryFilter,
        limit: '100',
      });
      const targetUrl = `${baseApiOrigin || 'http://localhost:8000'}/api/reference?${params.toString()}`;
      try {
        const res = await fetch(targetUrl);
        if (!cancelled && res.ok) {
          const data = await res.json();
          setEntries(Array.isArray(data.items) ? data.items : []);
          if (typeof data.total_settlements === 'number') {
            setTotalSettlements(data.total_settlements);
          }
          if (typeof data.total_streets === 'number') {
            setTotalStreets(data.total_streets);
          }
        }
      } catch {
        if (!cancelled) {
          setEntries([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingDict(false);
        }
      }
    }, 200);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [dictSearch, categoryFilter, baseApiOrigin, apiOnline]);

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
                  {apiOnline ? 'API подключен' : 'Ожидание подключения'}
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
              Все запросы разбора и поиска по справочнику выполняются через локальную базу SQLite бэкенда.
            </p>
          </section>

          <section className="lg:col-span-5 bg-white rounded-lg border border-slate-200 p-5 flex flex-col justify-between gap-4 shadow-2xs">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-slate-900">
                  Локальный гео-индекс (КАТО 2026 + OpenStreetMap РК)
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  База kaz_geo.sqlite: 20 регионов, районы, города, сёла и улицы РК
                </p>
              </div>
              <span className="px-2 py-0.5 rounded text-xs font-mono font-medium bg-slate-100 text-slate-700 border border-slate-200">
                kaz_geo.sqlite
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-200/80">
              <div>
                <div className="text-[11px] text-slate-500">Нас. пункты КАТО</div>
                <div className="text-base font-mono font-semibold text-slate-900 mt-0.5">
                  {totalSettlements > 0
                    ? totalSettlements.toLocaleString('ru-RU')
                    : '—'}
                </div>
              </div>
              <div>
                <div className="text-[11px] text-slate-500">Улицы и мкр OSM</div>
                <div className="text-base font-mono font-semibold text-slate-900 mt-0.5">
                  {totalStreets > 0
                    ? totalStreets.toLocaleString('ru-RU')
                    : '—'}
                </div>
              </div>
              <div>
                <div className="text-[11px] text-slate-500">Загружено записей</div>
                <div className="text-base font-mono font-semibold text-emerald-700 mt-0.5">
                  {metrics.totalRecords} зап.
                </div>
              </div>
            </div>
          </section>
        </div>

        {/* Geo-Enrichment Reference Dictionary from SQLite */}
        <section className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-2xs">
          <div className="p-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">
                Реестр гео-объектов Казахстана (КАТО 2026 + OpenStreetMap)
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Прямая выборка из локальной базы backend/data/kaz_geo.sqlite
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
                  placeholder="Поиск в kaz_geo.sqlite..."
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
                {entries.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-10 text-center text-slate-400">
                      {isLoadingDict
                        ? 'Загрузка данных из kaz_geo.sqlite...'
                        : apiOnline
                        ? 'Ничего не найдено по вашему запросу'
                        : 'Запустите бэкенд (uvicorn) для просмотра справочника kaz_geo.sqlite'}
                    </td>
                  </tr>
                ) : (
                  entries.map((item) => (
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
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
};
