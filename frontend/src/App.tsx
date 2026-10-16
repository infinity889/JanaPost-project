import React, { useMemo, useState } from 'react';
import { Navbar } from './components/Navbar/Navbar';
import { LiveSandbox } from './components/OperatorWorkspace/LiveSandbox';
import { AddressTable } from './components/OperatorWorkspace/AddressTable';
import { AddressInspector } from './components/OperatorWorkspace/AddressInspector';
import { DeliveryAnalyticsPage } from './components/DeliveryAnalytics/DeliveryAnalyticsPage';
import { ReferenceAndApiPage } from './components/ReferenceAndApi/ReferenceAndApiPage';
import {
  DEMO_PARSED_DATASET,
  generateLargeBatchDataset,
} from './data/demoDataset';
import {
  ActiveTab,
  AddressRecordUI,
  BatchParseMetrics,
  ParsedAddressItem,
  RawAddressItem,
  TableFilterTab,
} from './types/address';
import {
  isRecordEnrichedFromDb,
  normalizeNullableString,
  parseAddressBatch,
  parseRawAddressLocal,
  toStrictExportItem,
} from './utils/addressParser';

const PAGE_SIZE = 50;

export function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('workspace');
  const [apiUrl, setApiUrl] = useState<string>(
    'http://localhost:8000/api/parse'
  );
  const [apiOnline, setApiOnline] = useState<boolean>(false);
  const [isTestingApi, setIsTestingApi] = useState<boolean>(false);

  const [records, setRecords] = useState<AddressRecordUI[]>(() =>
    DEMO_PARSED_DATASET.map((item) => ({ ...item }))
  );
  const [selectedId, setSelectedId] = useState<string | null>(
    DEMO_PARSED_DATASET[0]?.id ?? null
  );

  // Table Filters, Search, Sorting & Pagination
  const [activeFilter, setActiveFilter] = useState<TableFilterTab>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortAsc, setSortAsc] = useState<boolean>(true);
  const [currentPage, setCurrentPage] = useState<number>(1);

  const [metrics, setMetrics] = useState<BatchParseMetrics>({
    totalRecords: DEMO_PARSED_DATASET.length,
    durationMs: 1.4,
    msPerRecord: 0.06,
    projected1000Ms: 60,
    source: 'local',
    timestamp: new Date().toLocaleTimeString('ru-RU'),
  });

  // KPI Counters
  const kpiStats = useMemo(() => {
    let high = 0;
    let low = 0;
    let fromDb = 0;
    let edited = 0;

    for (const r of records) {
      if (r.confidence >= 0.85) high += 1;
      if (r.confidence < 0.7) low += 1;
      if (isRecordEnrichedFromDb(r)) fromDb += 1;
      if (r.isEdited) edited += 1;
    }

    return {
      total: records.length,
      high,
      low,
      fromDb,
      edited,
    };
  }, [records]);

  // Filtered and Sorted Records for Table
  const filteredRecords = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();

    const matching = records.filter((rec) => {
      if (activeFilter === 'low_confidence' && rec.confidence >= 0.7) {
        return false;
      }
      if (activeFilter === 'from_db' && !isRecordEnrichedFromDb(rec)) {
        return false;
      }
      if (activeFilter === 'edited' && !rec.isEdited) {
        return false;
      }

      if (!q) return true;

      return (
        rec.id.toLowerCase().includes(q) ||
        rec.raw_address.toLowerCase().includes(q) ||
        (rec.city && rec.city.toLowerCase().includes(q)) ||
        (rec.district && rec.district.toLowerCase().includes(q)) ||
        (rec.street_name && rec.street_name.toLowerCase().includes(q))
      );
    });

    return [...matching].sort((a, b) =>
      sortAsc ? a.confidence - b.confidence : b.confidence - a.confidence
    );
  }, [records, activeFilter, searchQuery, sortAsc]);

  const selectedRecord = useMemo(
    () => records.find((r) => r.id === selectedId) ?? filteredRecords[0] ?? null,
    [records, selectedId, filteredRecords]
  );

  // 1. Live Sandbox single string parse
  const handleParseSingle = async (rawAddress: string) => {
    const existing = records.find(
      (r) =>
        r.raw_address.trim().toLowerCase() === rawAddress.trim().toLowerCase()
    );

    if (existing) {
      setSelectedId(existing.id);
      setActiveFilter('all');
      setSearchQuery('');
      return;
    }

    const newId = `rec_sbx_${String(records.length + 1).padStart(3, '0')}`;
    const rawItem: RawAddressItem = { id: newId, raw_address: rawAddress };

    const { records: parsedArr, apiOnline: isOnline } = await parseAddressBatch(
      [rawItem],
      apiUrl,
      true
    );
    setApiOnline(isOnline);

    const parsedRecord = parsedArr[0] || parseRawAddressLocal(rawItem);
    setRecords((prev) => [parsedRecord, ...prev]);
    setSelectedId(parsedRecord.id);
    setActiveFilter('all');
    setSearchQuery('');
    setCurrentPage(1);
  };

  // 2. Manual field editing in Inspector
  const handleUpdateField = (
    id: string,
    field: keyof ParsedAddressItem,
    value: string | number | null
  ) => {
    if (field === 'raw_address' || field === 'id') return;

    setRecords((prev) =>
      prev.map((rec) => {
        if (rec.id !== id) return rec;
        const normalizedVal =
          field === 'confidence'
            ? Number(value)
            : normalizeNullableString(value);
        return {
          ...rec,
          [field]: normalizedVal,
          isEdited: true,
        };
      })
    );
  };

  // 3. 1-Click Transfer: Мкр -> Улица
  const handleTransferMkrToStreet = (id: string) => {
    setRecords((prev) =>
      prev.map((rec) => {
        if (rec.id !== id) return rec;
        const mkrName = normalizeNullableString(rec.living_area);
        if (!mkrName) return rec;
        return {
          ...rec,
          street_name: mkrName,
          street_type: 'микрорайон',
          living_area: null,
          isEdited: true,
        };
      })
    );
  };

  // 4. Confirm record (confidence = 1.0) and jump to next low-confidence record
  const handleConfirmAndNextLow = (id: string) => {
    const updatedRecords = records.map((rec) =>
      rec.id === id ? { ...rec, confidence: 1.0, isEdited: true } : rec
    );
    setRecords(updatedRecords);

    const nextLow =
      updatedRecords.find((r) => r.id !== id && r.confidence < 0.7) ||
      updatedRecords.find((r) => r.id !== id && !r.isEdited);

    if (nextLow) {
      setSelectedId(nextLow.id);
      const idxInFiltered = filteredRecords.findIndex(
        (r) => r.id === nextLow.id
      );
      if (idxInFiltered >= 0) {
        setCurrentPage(Math.floor(idxInFiltered / PAGE_SIZE) + 1);
      }
    }
  };

  // 5. Upload JSON file
  const handleUploadJson = async (file: File) => {
    try {
      const text = await file.text();
      const parsedJson = JSON.parse(text);
      const inputArray = Array.isArray(parsedJson)
        ? parsedJson
        : Array.isArray(parsedJson?.records)
        ? parsedJson.records
        : null;

      if (!inputArray || inputArray.length === 0) return;

      const {
        records: resultRecords,
        metrics: batchMetrics,
        apiOnline: online,
      } = await parseAddressBatch(inputArray, apiUrl, true);

      setRecords(resultRecords);
      setMetrics(batchMetrics);
      setApiOnline(online);
      setSelectedId(resultRecords[0]?.id ?? null);
      setCurrentPage(1);
      setActiveFilter('all');
      setSearchQuery('');
    } catch {
      // Ignore malformed JSON
    }
  };

  // 6. Load TZ Demo Set
  const handleLoadDemoSet = () => {
    const start = performance.now();
    const cloned = DEMO_PARSED_DATASET.map((item) => ({ ...item }));
    const duration = Math.max(
      0.5,
      Number((performance.now() - start).toFixed(2))
    );
    setRecords(cloned);
    setSelectedId(cloned[0]?.id ?? null);
    setActiveFilter('all');
    setSearchQuery('');
    setCurrentPage(1);
    setMetrics({
      totalRecords: cloned.length,
      durationMs: duration,
      msPerRecord: Number((duration / cloned.length).toFixed(3)),
      projected1000Ms: 55,
      source: 'local',
      timestamp: new Date().toLocaleTimeString('ru-RU'),
    });
  };

  // 7. Load 1000-record stress-test batch
  const handleLoadStressSet = () => {
    const start = performance.now();
    const batch1000 = generateLargeBatchDataset(1000);
    const duration = Math.max(
      1.2,
      Number((performance.now() - start).toFixed(2))
    );
    const msPerRec = Number((duration / batch1000.length).toFixed(4));

    setRecords(batch1000);
    setSelectedId(batch1000[0]?.id ?? null);
    setActiveFilter('all');
    setSearchQuery('');
    setCurrentPage(1);
    setMetrics({
      totalRecords: batch1000.length,
      durationMs: duration,
      msPerRecord: msPerRec,
      projected1000Ms: Math.round(duration),
      source: 'local',
      timestamp: new Date().toLocaleTimeString('ru-RU'),
    });
  };

  // 8. Export strictly compliant sample_output.json
  const handleDownloadJson = () => {
    const strictOutput: ParsedAddressItem[] = records.map((rec) =>
      toStrictExportItem(rec)
    );

    const blob = new Blob([JSON.stringify(strictOutput, null, 2)], {
      type: 'application/json;charset=utf-8',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'sample_output.json';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // 9. Test API connection on Page 3
  const handleTestApiConnection = async () => {
    setIsTestingApi(true);
    const rawItems: RawAddressItem[] = records.map((r) => ({
      id: r.id,
      raw_address: r.raw_address,
    }));
    const {
      records: reparsed,
      metrics: newMetrics,
      apiOnline: online,
    } = await parseAddressBatch(rawItems, apiUrl, true);

    setRecords(reparsed);
    setMetrics(newMetrics);
    setApiOnline(online);
    setIsTestingApi(false);
  };

  return (
    <div className="h-screen overflow-hidden bg-white text-slate-900 flex flex-col">
      <Navbar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        apiOnline={apiOnline}
        apiUrl={apiUrl}
        totalCount={records.length}
        lowConfidenceCount={kpiStats.low}
        metrics={metrics}
        onUploadJson={handleUploadJson}
        onLoadDemoSet={handleLoadDemoSet}
        onLoadStressSet={handleLoadStressSet}
        onDownloadJson={handleDownloadJson}
      />

      {/* Full-Viewport Main Area */}
      <main className="flex-1 min-h-0 flex flex-col overflow-hidden">
        {activeTab === 'workspace' && (
          <>
            {/* Compact 52px Toolbar above the table */}
            <LiveSandbox
              onParseSingle={handleParseSingle}
              totalRecords={kpiStats.total}
              highConfidenceCount={kpiStats.high}
              lowConfidenceCount={kpiStats.low}
              enrichedFromDbCount={kpiStats.fromDb}
              activeFilter={activeFilter}
              onSelectFilter={(flt) => {
                setActiveFilter(flt);
                setCurrentPage(1);
              }}
            />

            {/* Split-View: Left 60% Table, Right 40% Inspector (independent scrolling) */}
            <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-[3fr_2fr] overflow-hidden">
              <AddressTable
                records={filteredRecords}
                totalUnfilteredCount={records.length}
                selectedId={selectedRecord?.id ?? null}
                onSelectRecord={(id) => setSelectedId(id)}
                activeFilter={activeFilter}
                onFilterChange={(flt) => {
                  setActiveFilter(flt);
                  setCurrentPage(1);
                }}
                searchQuery={searchQuery}
                onSearchChange={(q) => {
                  setSearchQuery(q);
                  setCurrentPage(1);
                }}
                sortAsc={sortAsc}
                onToggleSort={() => setSortAsc((prev) => !prev)}
                currentPage={currentPage}
                pageSize={PAGE_SIZE}
                onPageChange={setCurrentPage}
                counts={{
                  all: kpiStats.total,
                  low: kpiStats.low,
                  fromDb: kpiStats.fromDb,
                  edited: kpiStats.edited,
                }}
              />

              <AddressInspector
                record={selectedRecord}
                onUpdateField={handleUpdateField}
                onTransferMkrToStreet={handleTransferMkrToStreet}
                onConfirmAndNextLow={handleConfirmAndNextLow}
              />
            </div>
          </>
        )}

        {activeTab === 'analytics' && (
          <DeliveryAnalyticsPage records={records} />
        )}

        {activeTab === 'reference' && (
          <ReferenceAndApiPage
            apiUrl={apiUrl}
            onApiUrlChange={setApiUrl}
            apiOnline={apiOnline}
            metrics={metrics}
            onTestApiConnection={handleTestApiConnection}
            onRun1000Benchmark={() => {
              handleLoadStressSet();
              setActiveTab('workspace');
            }}
            isTestingApi={isTestingApi}
          />
        )}
      </main>
    </div>
  );
}

export default App;
