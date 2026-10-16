import React from 'react';
import {
  Search,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  X,
} from 'lucide-react';
import { AddressRecordUI, TableFilterTab } from '../../types/address';
import { isFieldFromDb } from '../../utils/addressParser';

interface AddressTableProps {
  records: AddressRecordUI[];
  totalUnfilteredCount: number;
  selectedId: string | null;
  onSelectRecord: (id: string) => void;
  activeFilter: TableFilterTab;
  onFilterChange: (filter: TableFilterTab) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  sortAsc: boolean;
  onToggleSort: () => void;
  currentPage: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  counts: {
    all: number;
    low: number;
    fromDb: number;
    edited: number;
  };
}

export const AddressTable: React.FC<AddressTableProps> = ({
  records,
  selectedId,
  onSelectRecord,
  activeFilter,
  onFilterChange,
  searchQuery,
  onSearchChange,
  sortAsc,
  onToggleSort,
  currentPage,
  pageSize,
  onPageChange,
  counts,
}) => {
  const totalPages = Math.max(1, Math.ceil(records.length / pageSize));
  const safePage = Math.min(currentPage, totalPages);
  const startIdx = (safePage - 1) * pageSize;
  const paginatedRecords = records.slice(startIdx, startIdx + pageSize);

  const filterTabs: Array<{
    id: TableFilterTab;
    label: string;
    count: number;
  }> = [
    { id: 'all', label: 'Все', count: counts.all },
    { id: 'low_confidence', label: 'На проверку', count: counts.low },
    { id: 'from_db', label: 'Из БД', count: counts.fromDb },
    { id: 'edited', label: 'Проверено', count: counts.edited },
  ];

  const handleRowKeyDown = (
    e: React.KeyboardEvent<HTMLTableRowElement>,
    idxInPage: number,
    recId: string
  ) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelectRecord(recId);
    } else if (
      e.key === 'ArrowDown' &&
      idxInPage + 1 < paginatedRecords.length
    ) {
      e.preventDefault();
      const nextRec = paginatedRecords[idxInPage + 1];
      onSelectRecord(nextRec.id);
    } else if (e.key === 'ArrowUp' && idxInPage - 1 >= 0) {
      e.preventDefault();
      const prevRec = paginatedRecords[idxInPage - 1];
      onSelectRecord(prevRec.id);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white border-r border-slate-200 overflow-hidden">
      {/* Sub-header: Filter Pills + Search + Sort */}
      <div className="h-12 px-5 border-b border-slate-200 flex items-center justify-between gap-3 shrink-0 bg-white">
        <div
          role="tablist"
          aria-label="Фильтры таблицы"
          className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg border border-slate-200/70"
        >
          {filterTabs.map((tab) => {
            const active = activeFilter === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => onFilterChange(tab.id)}
                className={`h-7 px-2.5 rounded-md text-xs font-medium inline-flex items-center gap-1.5 transition-all cursor-pointer ${
                  active
                    ? 'bg-emerald-600 text-white shadow-2xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <span>{tab.label}</span>
                <span
                  className={`text-[10px] font-mono px-1 rounded ${
                    active
                      ? 'bg-emerald-700 text-emerald-50'
                      : 'text-slate-400'
                  }`}
                >
                  {tab.count}
                </span>
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-2.5 flex-1 justify-end max-w-md">
          {/* Spacious Search */}
          <div className="relative flex-1 max-w-xs">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Поиск по ID, улице, городу..."
              aria-label="Поиск по таблице"
              className="w-full h-8 px-3 pl-9 pr-7 rounded-md border border-slate-200 bg-slate-50/70 text-xs text-slate-900 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-600/20 transition-colors"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => onSearchChange('')}
                aria-label="Очистить"
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Sort Button */}
          <button
            type="button"
            onClick={onToggleSort}
            title={
              sortAsc
                ? 'Сортировка по точности: сначала сложные записи'
                : 'Сортировка по точности: сначала точные записи'
            }
            className="h-8 px-3 rounded-md border border-slate-200 bg-white text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 inline-flex items-center gap-1.5 transition-colors cursor-pointer shrink-0"
          >
            <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
            <span className="hidden sm:inline">
              {sortAsc ? 'Точность ↑' : 'Точность ↓'}
            </span>
          </button>
        </div>
      </div>

      {/* Scrollable Table Body */}
      <div className="flex-1 overflow-y-auto overflow-x-auto bg-white">
        <table className="w-full text-left border-collapse table-fixed">
          <thead className="sticky top-0 z-10 bg-slate-50 border-b border-slate-200">
            <tr className="text-xs font-medium text-slate-500">
              <th className="py-2.5 pl-5 pr-2 w-28 font-medium">ID</th>
              <th className="py-2.5 px-3 w-[34%] font-medium">
                Исходный адрес
              </th>
              <th className="py-2.5 px-3 w-36 font-medium">Локация</th>
              <th className="py-2.5 px-3 w-44 font-medium">Улица и дом</th>
              <th className="py-2.5 px-3 w-28 font-medium">Кв / Детали</th>
              <th className="py-2.5 pl-2 pr-5 w-24 text-right font-medium">
                Точность
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-sm">
            {paginatedRecords.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-16 text-center">
                  <p className="text-sm font-medium text-slate-600">
                    Записи не найдены
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    Попробуйте изменить параметры поиска или переключить фильтр
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      onFilterChange('all');
                      onSearchChange('');
                    }}
                    className="mt-3 px-3 py-1.5 rounded-md text-xs font-medium bg-emerald-600 text-white hover:bg-emerald-700 cursor-pointer transition-colors"
                  >
                    Показать все записи
                  </button>
                </td>
              </tr>
            ) : (
              paginatedRecords.map((rec, idxInPage) => {
                const isSelected = rec.id === selectedId;
                const districtFromDb = isFieldFromDb(
                  rec.raw_address,
                  rec.district
                );
                const streetTypeFromDb = isFieldFromDb(
                  rec.raw_address,
                  rec.street_type
                );

                const detailsParts: string[] = [];
                if (rec.apartment) detailsParts.push(`кв. ${rec.apartment}`);
                if (rec.entrance) detailsParts.push(`п. ${rec.entrance}`);
                if (rec.floor) detailsParts.push(`эт. ${rec.floor}`);

                const pct = Math.round(rec.confidence * 100);
                const badgeClass =
                  rec.confidence >= 0.85
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200/80'
                    : rec.confidence >= 0.7
                    ? 'bg-slate-100 text-slate-700 border-slate-200'
                    : 'bg-amber-50 text-amber-800 border-amber-200';

                return (
                  <tr
                    key={rec.id}
                    onClick={() => onSelectRecord(rec.id)}
                    tabIndex={0}
                    onKeyDown={(e) => handleRowKeyDown(e, idxInPage, rec.id)}
                    className={`group transition-colors cursor-pointer border-l-[3px] ${
                      isSelected
                        ? 'bg-emerald-50/60 border-l-emerald-600'
                        : 'border-l-transparent hover:bg-slate-50/90'
                    }`}
                  >
                    {/* 1. ID */}
                    <td className="py-3 pl-4 pr-2 align-middle whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`font-mono text-xs ${
                            isSelected
                              ? 'text-emerald-800 font-semibold'
                              : 'text-slate-500'
                          }`}
                        >
                          {rec.id}
                        </span>
                        {rec.isEdited && (
                          <span title="Проверено оператором">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                          </span>
                        )}
                      </div>
                    </td>

                    {/* 2. Исходный адрес + вторая строка для ориентира */}
                    <td className="py-3 px-3 align-middle min-w-0">
                      <div className="text-xs font-medium text-slate-900 truncate">
                        {rec.raw_address}
                      </div>
                      {rec.landmark && (
                        <div className="text-xs text-slate-400 truncate mt-0.5">
                          Ориентир: {rec.landmark}
                        </div>
                      )}
                    </td>

                    {/* 3. Локация */}
                    <td className="py-3 px-3 align-middle min-w-0">
                      {rec.city || rec.district ? (
                        <div>
                          <div className="text-xs font-medium text-slate-800 truncate">
                            {rec.city ?? (
                              <span className="text-slate-300 font-normal">
                                —
                              </span>
                            )}
                          </div>
                          {rec.district && (
                            <div className="flex items-center gap-1 mt-0.5">
                              <span className="text-[11px] text-slate-500 truncate">
                                {rec.district}
                              </span>
                              {districtFromDb && (
                                <span
                                  title="Район обогащен из справочника БД"
                                  className="text-[9px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-1 rounded shrink-0"
                                >
                                  БД
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      ) : (
                        <span className="text-slate-300">—</span>
                      )}
                    </td>

                    {/* 4. Улица и дом */}
                    <td className="py-3 px-3 align-middle min-w-0">
                      {rec.street_name || rec.house ? (
                        <div>
                          <div className="text-xs font-medium text-slate-800 truncate">
                            {rec.street_name ?? (
                              <span className="text-slate-300 font-normal">
                                —
                              </span>
                            )}
                            {rec.house ? `, д. ${rec.house}` : ''}
                          </div>
                          {rec.street_type && (
                            <div className="flex items-center gap-1 mt-0.5">
                              <span className="text-[11px] text-slate-500 truncate">
                                {rec.street_type}
                              </span>
                              {streetTypeFromDb && (
                                <span
                                  title="Тип улицы обогащен из справочника БД"
                                  className="text-[9px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-1 rounded shrink-0"
                                >
                                  БД
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      ) : (
                        <span className="text-slate-300">—</span>
                      )}
                    </td>

                    {/* 5. Кв / Детали */}
                    <td className="py-3 px-3 align-middle whitespace-nowrap">
                      {detailsParts.length > 0 ? (
                        <span className="text-xs text-slate-600">
                          {detailsParts.join(' · ')}
                        </span>
                      ) : (
                        <span className="text-slate-300">—</span>
                      )}
                    </td>

                    {/* 6. Точность */}
                    <td className="py-3 pl-2 pr-5 align-middle text-right whitespace-nowrap">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full font-mono text-[11px] font-medium border ${badgeClass}`}
                      >
                        {pct}%
                      </span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Minimalist Pagination Bar */}
      <div className="h-10 px-5 border-t border-slate-200 bg-slate-50/60 flex items-center justify-between text-xs text-slate-500 shrink-0 select-none">
        <span>
          Показано{' '}
          <strong className="font-medium text-slate-700">
            {records.length === 0 ? 0 : startIdx + 1}–
            {Math.min(startIdx + pageSize, records.length)}
          </strong>{' '}
          из{' '}
          <strong className="font-medium text-slate-700">
            {records.length}
          </strong>
        </span>

        <div className="flex items-center gap-1">
          <button
            type="button"
            disabled={safePage <= 1}
            onClick={() => onPageChange(safePage - 1)}
            aria-label="Предыдущая страница"
            className="h-6 px-2 rounded border border-slate-200 bg-white flex items-center justify-center text-slate-600 hover:text-slate-900 hover:bg-slate-50 disabled:opacity-40 disabled:pointer-events-none cursor-pointer"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <span className="px-2 font-mono text-[11px] text-slate-600">
            {safePage} / {totalPages}
          </span>
          <button
            type="button"
            disabled={safePage >= totalPages}
            onClick={() => onPageChange(safePage + 1)}
            aria-label="Следующая страница"
            className="h-6 px-2 rounded border border-slate-200 bg-white flex items-center justify-center text-slate-600 hover:text-slate-900 hover:bg-slate-50 disabled:opacity-40 disabled:pointer-events-none cursor-pointer"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
