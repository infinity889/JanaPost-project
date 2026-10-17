import React, { useMemo, useState } from 'react';
import { AddressRecordUI } from '../../types/address';
import { isFieldFromDb } from '../../utils/addressParser';

interface DeliveryAnalyticsPageProps {
  records: AddressRecordUI[];
}

export const DeliveryAnalyticsPage: React.FC<DeliveryAnalyticsPageProps> = ({
  records,
}) => {
  const [geoGroupMode, setGeoGroupMode] = useState<'city' | 'province'>('city');

  const analytics = useMemo(() => {
    const total = records.length || 1;
    const cityCounts = new Map<string, number>();
    const provinceCounts = new Map<string, number>();

    const districtZones = new Map<
      string,
      {
        city: string;
        district: string;
        total: number;
        foundInString: number;
        restoredFromDb: number;
      }
    >();

    let houseFilled = 0;
    let apartmentFilled = 0;
    let entranceFilled = 0;
    let floorFilled = 0;
    let landmarkFilled = 0;
    let readyDoorToDoor = 0;

    for (const rec of records) {
      const cName = rec.city || 'Не определен';
      const pName = rec.province || 'Не определена';
      cityCounts.set(cName, (cityCounts.get(cName) || 0) + 1);
      provinceCounts.set(pName, (provinceCounts.get(pName) || 0) + 1);

      if (rec.city && rec.district) {
        const key = `${rec.city}::${rec.district}`;
        const existing = districtZones.get(key) || {
          city: rec.city,
          district: rec.district,
          total: 0,
          foundInString: 0,
          restoredFromDb: 0,
        };
        existing.total += 1;
        if (isFieldFromDb(rec.raw_address, rec.district)) {
          existing.restoredFromDb += 1;
        } else {
          existing.foundInString += 1;
        }
        districtZones.set(key, existing);
      }

      if (rec.house) houseFilled += 1;
      if (rec.apartment) apartmentFilled += 1;
      if (rec.entrance) entranceFilled += 1;
      if (rec.floor) floorFilled += 1;
      if (rec.landmark) landmarkFilled += 1;

      if (rec.city && rec.street_name && rec.house) {
        readyDoorToDoor += 1;
      }
    }

    const sortedCities = Array.from(cityCounts.entries())
      .map(([name, count]) => ({
        name,
        count,
        percent: Math.round((count / total) * 100),
      }))
      .sort((a, b) => b.count - a.count);

    const sortedProvinces = Array.from(provinceCounts.entries())
      .map(([name, count]) => ({
        name,
        count,
        percent: Math.round((count / total) * 100),
      }))
      .sort((a, b) => b.count - a.count);

    const sortedDistrictZones = Array.from(districtZones.values()).sort(
      (a, b) => b.total - a.total
    );

    const totalDistrictResolved = sortedDistrictZones.reduce(
      (acc, z) => acc + z.total,
      0
    );
    const totalDistrictFromDb = sortedDistrictZones.reduce(
      (acc, z) => acc + z.restoredFromDb,
      0
    );

    return {
      total: records.length,
      sortedCities,
      sortedProvinces,
      sortedDistrictZones,
      totalDistrictResolved,
      totalDistrictFromDb,
      readyDoorToDoor,
      courierFields: [
        {
          key: 'house',
          label: 'Номер дома',
          count: houseFilled,
          percent: Math.round((houseFilled / total) * 100),
        },
        {
          key: 'apartment',
          label: 'Квартира',
          count: apartmentFilled,
          percent: Math.round((apartmentFilled / total) * 100),
        },
        {
          key: 'entrance',
          label: 'Подъезд',
          count: entranceFilled,
          percent: Math.round((entranceFilled / total) * 100),
        },
        {
          key: 'floor',
          label: 'Этаж',
          count: floorFilled,
          percent: Math.round((floorFilled / total) * 100),
        },
        {
          key: 'landmark',
          label: 'Ориентир',
          count: landmarkFilled,
          percent: Math.round((landmarkFilled / total) * 100),
        },
      ],
    };
  }, [records]);

  const activeGeoDistribution =
    geoGroupMode === 'city' ? analytics.sortedCities : analytics.sortedProvinces;
  const maxGeoCount = Math.max(
    1,
    ...activeGeoDistribution.map((item) => item.count)
  );

  return (
    <div className="h-full overflow-y-auto p-6 bg-slate-50/60">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Top Summary Strip */}
        <div className="bg-white rounded-lg border border-slate-200 p-5 flex flex-wrap items-center justify-between gap-4 shadow-2xs">
          <div>
            <h1 className="text-base font-semibold text-slate-900">
              Аналитика зон доставки и полноты данных
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              Сводка по населенным пунктам, административным районам и заполненности полей
            </p>
          </div>

          <div className="flex items-center gap-6 text-xs">
            <div>
              <div className="text-slate-400">Готово к доставке</div>
              <div className="font-mono text-base font-semibold text-slate-900 mt-0.5">
                {analytics.readyDoorToDoor} / {analytics.total}
              </div>
            </div>
            <div className="h-8 w-px bg-slate-200" />
            <div>
              <div className="text-slate-400">Определено районов</div>
              <div className="font-mono text-base font-semibold text-slate-900 mt-0.5">
                {analytics.totalDistrictResolved}
              </div>
            </div>
            <div className="h-8 w-px bg-slate-200" />
            <div>
              <div className="text-slate-400">Восстановлено из БД</div>
              <div className="font-mono text-base font-semibold text-emerald-600 mt-0.5">
                +{analytics.totalDistrictFromDb}
              </div>
            </div>
          </div>
        </div>

        {/* Grid: Geo Distribution + Courier Completeness */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Horizontal Bar Chart */}
          <section className="lg:col-span-7 bg-white rounded-lg border border-slate-200 p-5 shadow-2xs">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-semibold text-slate-900">
                  Распределение заказов по географии
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Нормализованные населенные пункты и области
                </p>
              </div>

              <div className="inline-flex bg-slate-100 p-0.5 rounded-lg border border-slate-200/70 text-xs">
                <button
                  type="button"
                  onClick={() => setGeoGroupMode('city')}
                  className={`px-3 py-1 rounded-md font-medium transition-colors cursor-pointer ${
                    geoGroupMode === 'city'
                      ? 'bg-white text-slate-900 shadow-2xs'
                      : 'text-slate-500 hover:text-slate-900'
                  }`}
                >
                  По городам
                </button>
                <button
                  type="button"
                  onClick={() => setGeoGroupMode('province')}
                  className={`px-3 py-1 rounded-md font-medium transition-colors cursor-pointer ${
                    geoGroupMode === 'province'
                      ? 'bg-white text-slate-900 shadow-2xs'
                      : 'text-slate-500 hover:text-slate-900'
                  }`}
                >
                  По областям
                </button>
              </div>
            </div>

            <div className="space-y-3.5">
              {activeGeoDistribution.map((item) => {
                const widthPct = Math.max(
                  3,
                  Math.round((item.count / maxGeoCount) * 100)
                );
                return (
                  <div key={item.name} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-800 font-medium">
                        {item.name}
                      </span>
                      <span className="font-mono text-slate-600">
                        {item.count} зак. ({item.percent}%)
                      </span>
                    </div>
                    <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-600 rounded-full"
                        style={{ width: `${widthPct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Courier Completeness */}
          <section className="lg:col-span-5 bg-white rounded-lg border border-slate-200 p-5 shadow-2xs">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-semibold text-slate-900">
                  Заполненность детальных полей
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Доля записей с распознанными реквизитами доставки
                </p>
              </div>
              <span className="text-xs font-mono text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                {analytics.total} зап.
              </span>
            </div>

            <div className="space-y-3.5">
              {analytics.courierFields.map((f) => (
                <div key={f.key} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium text-slate-800">
                      {f.label}
                    </span>
                    <span className="font-mono text-slate-600">
                      {f.count} ({f.percent}%)
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-emerald-500 rounded-full"
                      style={{ width: `${f.percent}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* District Zones Table */}
        <section className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-2xs">
          <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">
                Зоны доставки по административным районам
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Разбивка: сколько районов было указано в исходной строке, а сколько восстановлено по справочнику улиц и микрорайонов
              </p>
            </div>
          </div>

          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-500">
                <th className="py-2.5 px-5 font-medium">Город</th>
                <th className="py-2.5 px-5 font-medium">Район доставки</th>
                <th className="py-2.5 px-5 text-right font-medium">
                  Всего заказов
                </th>
                <th className="py-2.5 px-5 text-right font-medium">
                  Найдено в строке
                </th>
                <th className="py-2.5 px-5 text-right font-medium">
                  Восстановлено из БД
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {analytics.sortedDistrictZones.map((zone) => (
                <tr
                  key={`${zone.city}-${zone.district}`}
                  className="hover:bg-slate-50/80"
                >
                  <td className="py-3 px-5 text-slate-900 font-medium">
                    {zone.city}
                  </td>
                  <td className="py-3 px-5 text-slate-700">{zone.district}</td>
                  <td className="py-3 px-5 text-right font-mono font-medium text-slate-900">
                    {zone.total}
                  </td>
                  <td className="py-3 px-5 text-right font-mono text-slate-500">
                    {zone.foundInString}
                  </td>
                  <td className="py-3 px-5 text-right font-mono">
                    {zone.restoredFromDb > 0 ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium">
                        +{zone.restoredFromDb} из БД
                      </span>
                    ) : (
                      <span className="text-slate-300">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </div>
  );
};
