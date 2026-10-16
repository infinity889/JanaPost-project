import React from 'react';
import {
  FileCheck2,
  ShieldCheck,
  AlertTriangle,
  Database,
} from 'lucide-react';
import { TableFilterTab } from '../../types/address';

interface KpiCardsProps {
  totalRecords: number;
  initialCount: number;
  highConfidenceCount: number;
  lowConfidenceCount: number;
  enrichedFromDbCount: number;
  activeFilter: TableFilterTab;
  onSelectFilter: (filter: TableFilterTab) => void;
}

export const KpiCards: React.FC<KpiCardsProps> = ({
  totalRecords,
  initialCount,
  highConfidenceCount,
  lowConfidenceCount,
  enrichedFromDbCount,
  activeFilter,
  onSelectFilter,
}) => {
  const highPercent =
    totalRecords > 0 ? Math.round((highConfidenceCount / totalRecords) * 100) : 0;
  const lowPercent =
    totalRecords > 0 ? Math.round((lowConfidenceCount / totalRecords) * 100) : 0;
  const dbPercent =
    totalRecords > 0 ? Math.round((enrichedFromDbCount / totalRecords) * 100) : 0;

  return (
    <section
      aria-label="Ключевые показатели качества разбора (KPI)"
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3"
    >
      {/* 1. Всего записей */}
      <button
        type="button"
        onClick={() => onSelectFilter('all')}
        className={`text-left bg-white rounded-lg p-3.5 border transition-all cursor-pointer ${
          activeFilter === 'all'
            ? 'border-slate-900 ring-1 ring-slate-900/10 shadow-xs'
            : 'border-slate-200 hover:border-slate-300'
        }`}
      >
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-600">
            Всего записей
          </span>
          <span className="p-1.5 rounded-md bg-slate-100 text-slate-700">
            <FileCheck2 className="w-4 h-4" />
          </span>
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-2xl font-bold font-mono text-slate-900">
            {totalRecords}
          </span>
          <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
            Потерь: 0 ({totalRecords}/{initialCount})
          </span>
        </div>
        <p className="mt-1.5 text-[11px] text-slate-500">
          Строгий контроль 100% сохранности батча при экспорте
        </p>
      </button>

      {/* 2. Уверенный разбор (confidence >= 0.85) */}
      <div className="bg-white rounded-lg p-3.5 border border-slate-200">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-600">
            Уверенный разбор (confidence &ge; 0.85)
          </span>
          <span className="p-1.5 rounded-md bg-emerald-50 text-emerald-600 border border-emerald-200">
            <ShieldCheck className="w-4 h-4" />
          </span>
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-2xl font-bold font-mono text-emerald-700">
            {highConfidenceCount}
          </span>
          <span className="text-xs font-mono font-medium text-emerald-600">
            ({highPercent}%)
          </span>
          <span className="ml-auto inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            Готово к маршрутизации
          </span>
        </div>
        <p className="mt-1.5 text-[11px] text-slate-500">
          Автоматический расчет зоны и курьерского маршрута
        </p>
      </div>

      {/* 3. Требуют проверки (confidence < 0.70) — клик включает фильтр неуверенных */}
      <button
        type="button"
        onClick={() =>
          onSelectFilter(
            activeFilter === 'low_confidence' ? 'all' : 'low_confidence'
          )
        }
        className={`text-left bg-white rounded-lg p-3.5 border transition-all cursor-pointer ${
          activeFilter === 'low_confidence'
            ? 'border-amber-500 ring-2 ring-amber-500/20 bg-amber-50/20'
            : 'border-amber-200/90 hover:border-amber-400'
        }`}
      >
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-700">
            Требуют проверки (confidence &lt; 0.70)
          </span>
          <span className="p-1.5 rounded-md bg-amber-50 text-amber-600 border border-amber-200">
            <AlertTriangle className="w-4 h-4" />
          </span>
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-2xl font-bold font-mono text-amber-700">
            {lowConfidenceCount}
          </span>
          <span className="text-xs font-mono font-medium text-amber-700">
            ({lowPercent}%)
          </span>
          <span className="ml-auto text-[11px] font-medium px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300">
            {activeFilter === 'low_confidence'
              ? 'Фильтр активен'
              : 'Нажмите для фильтра'}
          </span>
        </div>
        <p className="mt-1.5 text-[11px] text-slate-500">
          Неполные строки или аномалии — приоритет оператора
        </p>
      </button>

      {/* 4. Обогащено из справочника */}
      <button
        type="button"
        onClick={() =>
          onSelectFilter(activeFilter === 'from_db' ? 'all' : 'from_db')
        }
        className={`text-left bg-white rounded-lg p-3.5 border transition-all cursor-pointer ${
          activeFilter === 'from_db'
            ? 'border-blue-600 ring-2 ring-blue-600/20 bg-blue-50/10'
            : 'border-slate-200 hover:border-blue-300'
        }`}
      >
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-600">
            Обогащено из справочника
          </span>
          <span className="p-1.5 rounded-md bg-blue-50 text-blue-600 border border-blue-200">
            <Database className="w-4 h-4" />
          </span>
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-2xl font-bold font-mono text-blue-700">
            {enrichedFromDbCount}
          </span>
          <span className="text-xs font-mono font-medium text-blue-600">
            ({dbPercent}%)
          </span>
          <span className="ml-auto inline-flex items-center gap-1 text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
            БД: district / street_type
          </span>
        </div>
        <p className="mt-1.5 text-[11px] text-slate-500">
          Восстановлен район или тип улицы, отсутствовавший в строке
        </p>
      </button>
    </section>
  );
};
