import React, { useEffect, useRef, useState } from 'react';
import {
  ChevronDown,
  CornerDownLeft,
  Search,
} from 'lucide-react';
import { SANDBOX_CHIP_EXAMPLES } from '../../data/referenceDictionary';
import { TableFilterTab } from '../../types/address';

interface LiveSandboxProps {
  onParseSingle: (rawAddress: string) => void;
  totalRecords: number;
  highConfidenceCount: number;
  lowConfidenceCount: number;
  enrichedFromDbCount: number;
  activeFilter: TableFilterTab;
  onSelectFilter: (filter: TableFilterTab) => void;
}

const EXAMPLE_LABELS: Record<string, string> = {
  'город Алматы/Алматы қаласы, Мкр Аксай 3а, 59, кв 70':
    'Двуязычный город + микрорайон без улицы',
  '66квартал 12дом 69квартира': 'Слитное написание квартала и дома',
  'Ул .Курильская 9 кв 1': 'Определение города и района по улице из БД',
  'Туран 55/6 магазин береке 4подьезд 9этаж':
    'Дробный дом + ориентир + подъезд/этаж',
  'Нурсити 2 микрорайон 11дом 5 подьезд 239 кв':
    'Инверсия «Нурсити 2 микрорайон» (г. Актобе)',
  'Турксибский район, Рыбинский переулок, дом 4':
    'Определение города по связке района и переулка',
  'Кулманова 133': 'Короткий адрес (только улица и дом, г. Атырау)',
  'жуалы 19': 'Строка в нижнем регистре без типа улицы',
};

export const LiveSandbox: React.FC<LiveSandboxProps> = ({
  onParseSingle,
  totalRecords,
  highConfidenceCount,
  lowConfidenceCount,
  enrichedFromDbCount,
  activeFilter,
  onSelectFilter,
}) => {
  const [inputValue, setInputValue] = useState<string>('');
  const [popoverOpen, setPopoverOpen] = useState<boolean>(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(e.target as Node)
      ) {
        setPopoverOpen(false);
      }
    };
    if (popoverOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [popoverOpen]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;
    onParseSingle(inputValue.trim());
  };

  const handleSelectExample = (example: string) => {
    setInputValue(example);
    setPopoverOpen(false);
    onParseSingle(example);
  };

  return (
    <div className="h-14 shrink-0 bg-slate-50/80 border-b border-slate-200 px-5 flex items-center justify-between gap-4">
      {/* Left: Spacious Input + Standalone Parse Button + Popover "Примеры из ТЗ" */}
      <div className="flex items-center gap-2.5 flex-1 max-w-3xl">
        <form
          onSubmit={handleSubmit}
          className="flex items-center gap-2 flex-1"
        >
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Введите любой сырой адрес для быстрого разбора..."
              aria-label="Проверить адрес вручную"
              className="w-full h-9 pl-10 pr-3.5 rounded-lg bg-white border border-slate-300 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-600/20 transition-all shadow-2xs"
            />
          </div>

          <button
            type="submit"
            title="Разобрать введенный адрес (Enter)"
            className="h-9 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-xs font-semibold text-white inline-flex items-center gap-1.5 cursor-pointer transition-colors shadow-2xs shrink-0"
          >
            <span>Разобрать</span>
            <CornerDownLeft className="w-3.5 h-3.5 opacity-80" />
          </button>
        </form>

        {/* Выпадающий по клику поповер "Примеры из ТЗ" */}
        <div ref={popoverRef} className="relative shrink-0">
          <button
            type="button"
            onClick={() => setPopoverOpen((prev) => !prev)}
            aria-expanded={popoverOpen}
            className={`h-9 px-3 rounded-lg border text-xs font-medium inline-flex items-center gap-1.5 transition-colors cursor-pointer shadow-2xs ${
              popoverOpen
                ? 'bg-emerald-50 border-emerald-600 text-emerald-800'
                : 'bg-white border-slate-300 text-slate-700 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <span>Примеры из ТЗ</span>
            <ChevronDown
              className={`w-3.5 h-3.5 text-slate-400 transition-transform ${
                popoverOpen ? 'rotate-180 text-emerald-600' : ''
              }`}
            />
          </button>

          {popoverOpen && (
            <div className="absolute left-0 mt-1.5 w-[480px] max-w-[92vw] bg-white rounded-lg border border-slate-200 shadow-xl py-1.5 z-40">
              <div className="px-3.5 py-1.5 text-[11px] font-medium text-slate-500 border-b border-slate-100 flex items-center justify-between">
                <span>Тестовые кейсы из технического задания</span>
                <span className="font-mono text-[10px] text-slate-400">
                  8 примеров
                </span>
              </div>
              <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
                {SANDBOX_CHIP_EXAMPLES.map((example) => (
                  <button
                    key={example}
                    type="button"
                    onClick={() => handleSelectExample(example)}
                    className="w-full text-left px-3.5 py-2.5 hover:bg-emerald-50/60 transition-colors cursor-pointer block group"
                  >
                    <div className="text-xs font-mono text-slate-900 group-hover:text-emerald-900 truncate">
                      {example}
                    </div>
                    {EXAMPLE_LABELS[example] && (
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        {EXAMPLE_LABELS[example]}
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right: 4 компактных статусных счетчика в одну строчку */}
      <div className="hidden xl:flex items-center gap-1.5 text-xs shrink-0 select-none">
        <button
          type="button"
          onClick={() => onSelectFilter('all')}
          className={`px-2.5 py-1.5 rounded-md transition-colors cursor-pointer ${
            activeFilter === 'all'
              ? 'bg-white text-slate-900 font-medium border border-slate-200 shadow-2xs'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          Всего:{' '}
          <span className="font-mono font-semibold text-slate-900">
            {totalRecords}
          </span>
        </button>

        <span className="text-slate-300">·</span>

        <div className="px-2 py-1.5 text-slate-600">
          Уверенные:{' '}
          <span className="font-mono font-semibold text-emerald-700">
            {highConfidenceCount}
          </span>
        </div>

        <span className="text-slate-300">·</span>

        <button
          type="button"
          onClick={() =>
            onSelectFilter(
              activeFilter === 'low_confidence' ? 'all' : 'low_confidence'
            )
          }
          className={`px-2.5 py-1.5 rounded-md transition-colors cursor-pointer ${
            activeFilter === 'low_confidence'
              ? 'bg-amber-50 text-amber-900 font-medium border border-amber-200'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          На проверку:{' '}
          <span className="font-mono font-semibold text-amber-700">
            {lowConfidenceCount}
          </span>
        </button>

        <span className="text-slate-300">·</span>

        <button
          type="button"
          onClick={() =>
            onSelectFilter(activeFilter === 'from_db' ? 'all' : 'from_db')
          }
          className={`px-2.5 py-1.5 rounded-md transition-colors cursor-pointer ${
            activeFilter === 'from_db'
              ? 'bg-emerald-50 text-emerald-900 font-medium border border-emerald-200'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          Из БД:{' '}
          <span className="font-mono font-semibold text-emerald-700">
            {enrichedFromDbCount}
          </span>
        </button>
      </div>
    </div>
  );
};
