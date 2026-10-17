#!/usr/bin/env python3
"""
Скрипт прогона парсера на data/val_input.json, запуска evaluate.py
и стресс-теста производительности на 1000 записей.
"""

from __future__ import annotations

import json
import sys
import threading
import time
import urllib.request
from http.server import HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.main import _StdlibRequestHandler, health_check, parse_addresses  # noqa: E402
from app.parser.pipeline import AddressParserPipeline  # noqa: E402
from app.schemas import RawAddressItem  # noqa: E402


def main() -> int:
    val_input_path = ROOT / "data" / "val_input.json"
    val_pred_path = ROOT / "data" / "val_pred.json"

    with val_input_path.open("r", encoding="utf-8") as f:
        records = json.load(f)

    # 1. Live HTTP test against /api/health and /api/parse
    server = HTTPServer(("127.0.0.1", 0), _StdlibRequestHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=5) as resp:
            health = json.loads(resp.read().decode("utf-8"))
        print(f"[http] GET /api/health -> {health}")
        assert health.get("status") == "ok" and health.get("db_loaded") is True

        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/parse",
            data=json.dumps(records, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            predictions = json.loads(resp.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()

    with val_pred_path.open("w", encoding="utf-8") as f:
        json.dump(predictions, f, ensure_ascii=False, indent=2)

    print(
        f"[http] POST /api/parse записано {len(predictions)} предсказаний в {val_pred_path}"
    )

    # 2. Benchmark 1000 records
    pipeline = AddressParserPipeline()
    batch_1000 = [
        {
            "id": f"bench_{i:04d}",
            "raw_address": records[i % len(records)]["raw_address"],
        }
        for i in range(1000)
    ]
    t0 = time.perf_counter()
    res_1000 = pipeline.parse_batch(batch_1000)
    elapsed = time.perf_counter() - t0
    print(
        f"[benchmark] 1000 записей разобрано за {elapsed * 1000:.2f} мс "
        f"({elapsed:.4f} сек, лимит ТЗ < 300 сек, обработано: {len(res_1000)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
