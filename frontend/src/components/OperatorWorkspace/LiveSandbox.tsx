import React, { useState } from 'react';
import { CornerDownLeft, Search } from 'lucide-react';
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

export const LiveSandbox: React.FC<LiveSandboxProps> = ({ onParseSingle }) => {
  const [inputValue, setInputValue] = useState<string>('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;
    onParseSingle(inputValue.trim());
    setInputValue('');
  };

  return (
    <div className="h-14 shrink-0 bg-slate-50/80 border-b border-slate-200 px-5 flex items-center justify-between gap-4">
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
              placeholder="Введите адресную строку для разбора через API (или загрузите JSON-файл)..."
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
      </div>
    </div>
  );
};
