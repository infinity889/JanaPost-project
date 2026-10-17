import React, { useRef } from 'react';
import {
  Upload,
  Download,
  MapPin,
  RotateCcw,
} from 'lucide-react';
import { ActiveTab, BatchParseMetrics } from '../../types/address';

interface NavbarProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  apiOnline: boolean;
  apiUrl: string;
  totalCount: number;
  lowConfidenceCount: number;
  metrics: BatchParseMetrics;
  onUploadJson: (file: File) => void;
  onLoadDemoSet: () => void;
  onLoadStressSet: () => void;
  onDownloadJson: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onTabChange,
  apiOnline,
  apiUrl,
  totalCount,
  lowConfidenceCount,
  onUploadJson,
  onLoadDemoSet,
  onDownloadJson,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onUploadJson(file);
      e.target.value = '';
    }
  };

  return (
    <header className="h-14 shrink-0 bg-white border-b border-slate-200 px-5 flex items-center justify-between gap-4 select-none z-20">
      {/* Left: Brand Identity + Primary Navigation */}
      <div className="flex items-center gap-6 h-full min-w-0">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-emerald-600 text-white flex items-center justify-center shadow-2xs shrink-0">
            <MapPin className="w-4 h-4 stroke-[2.2]" />
          </div>
          <div className="leading-none">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm tracking-tight text-slate-900">
                Jana Address
              </span>
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200/80">
                Jana Post
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1 hidden sm:block">
              Нормализация и гео-обогащение адресов
            </p>
          </div>
        </div>

        <div className="h-5 w-px bg-slate-200 hidden md:block" />

        {/* Navigation Tabs with crisp bottom active bar */}
        <nav
          role="tablist"
          aria-label="Разделы системы"
          className="flex items-center gap-1 h-full"
        >
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'workspace'}
            onClick={() => onTabChange('workspace')}
            className={`h-full px-3 text-xs font-medium border-b-2 transition-colors inline-flex items-center gap-2 cursor-pointer ${
              activeTab === 'workspace'
                ? 'border-emerald-600 text-emerald-700 font-semibold'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            <span>Рабочее место</span>
            {lowConfidenceCount > 0 && (
              <span
                title="Записи, требующие проверки оператора"
                className="px-1.5 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-amber-100 text-amber-800"
              >
                {lowConfidenceCount}
              </span>
            )}
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'analytics'}
            onClick={() => onTabChange('analytics')}
            className={`h-full px-3 text-xs font-medium border-b-2 transition-colors inline-flex items-center cursor-pointer ${
              activeTab === 'analytics'
                ? 'border-emerald-600 text-emerald-700 font-semibold'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            Аналитика зон доставки
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'reference'}
            onClick={() => onTabChange('reference')}
            className={`h-full px-3 text-xs font-medium border-b-2 transition-colors inline-flex items-center cursor-pointer ${
              activeTab === 'reference'
                ? 'border-emerald-600 text-emerald-700 font-semibold'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            Справочник и API
          </button>
        </nav>
      </div>

      {/* Right: Engine Status & Dataset Actions */}
      <div className="flex items-center gap-2 shrink-0">
        <button
          type="button"
          onClick={() => onTabChange('reference')}
          title={`Эндпоинт: ${apiUrl}`}
          className="hidden xl:inline-flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs text-slate-600 hover:text-slate-900 hover:bg-slate-100 border border-transparent transition-colors cursor-pointer"
        >
          <span
            className={`w-2 h-2 rounded-full ${
              apiOnline ? 'bg-emerald-500' : 'bg-slate-400'
            }`}
          />
          <span className="font-medium">
            {apiOnline ? 'API подключен' : 'Автономный режим'}
          </span>
        </button>

        <div className="h-4 w-px bg-slate-200 hidden xl:block" />

        <input
          ref={fileInputRef}
          type="file"
          accept=".json,application/json"
          onChange={handleFileChange}
          className="hidden"
          aria-label="Загрузить JSON"
        />

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="h-8 px-3 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-200 inline-flex items-center gap-1.5 transition-colors cursor-pointer shadow-2xs"
        >
          <Upload className="w-3.5 h-3.5 text-slate-500" />
          <span>Загрузить JSON</span>
        </button>

        <button
          type="button"
          onClick={onLoadDemoSet}
          title="Восстановить исходный демо-набор"
          className="h-8 px-3 rounded-md text-xs font-medium text-slate-700 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-200 inline-flex items-center gap-1.5 transition-colors cursor-pointer shadow-2xs"
        >
          <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
          <span className="hidden sm:inline">Сбросить</span>
        </button>

        <button
          type="button"
          onClick={onDownloadJson}
          className="h-8 px-3.5 rounded-md text-xs font-medium bg-emerald-600 hover:bg-emerald-700 text-white inline-flex items-center gap-1.5 transition-colors shadow-2xs cursor-pointer"
        >
          <Download className="w-3.5 h-3.5" />
          <span>Скачать .json</span>
          <span className="ml-0.5 px-1.5 py-0.2 rounded bg-emerald-700/80 text-emerald-50 font-mono text-[11px]">
            {totalCount}
          </span>
        </button>
      </div>
    </header>
  );
};
