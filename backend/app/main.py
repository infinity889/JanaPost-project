from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.parser.pipeline import AddressParserPipeline  # noqa: E402
from app.schemas import BatchParsePayload, ParsedAddressItem, RawAddressItem  # noqa: E402


DEFAULT_DB_PATH = BASE_DIR / "data" / "kaz_geo.sqlite"
DB_PATH = Path(os.getenv("JANA_GEO_DB_PATH", str(DEFAULT_DB_PATH)))

pipeline = AddressParserPipeline(db_path=DB_PATH)


def _extract_raw_items(payload: Any) -> List[RawAddressItem]:
    if isinstance(payload, list):
        return [
            item if isinstance(item, RawAddressItem) else RawAddressItem(**item)
            for item in payload
        ]
    if hasattr(payload, "records") and payload.records is not None:
        return payload.records
    if hasattr(payload, "items") and payload.items is not None:
        return payload.items
    if isinstance(payload, dict):
        raw_list = payload.get("records") or payload.get("items") or []
        return [
            item if isinstance(item, RawAddressItem) else RawAddressItem(**item)
            for item in raw_list
        ]
    return []


def health_check() -> Dict[str, Any]:
    return {
        "status": "ok",
        "db_loaded": DB_PATH.exists(),
        "settlements_loaded": len(pipeline.gazetteer.settlements),
        "streets_loaded": len(pipeline.gazetteer.streets_by_norm),
        "buildings_loaded": len(pipeline.gazetteer.buildings),
    }


def reference_search(
    q: str = "",
    category: str = "all",
    limit: int = 100,
) -> Dict[str, Any]:
    """Возвращает реальные записи из локальной базы kaz_geo.sqlite (КАТО 2026 + OSM)."""
    import sqlite3

    if not DB_PATH.exists():
        return {"items": [], "total_settlements": 0, "total_streets": 0}

    q_clean = q.strip().lower()
    safe_limit = max(1, min(limit, 300))
    items: List[Dict[str, Any]] = []

    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        total_settlements = cur.execute(
            "SELECT COUNT(DISTINCT city || ':' || province) FROM settlements"
        ).fetchone()[0]
        total_streets = cur.execute(
            "SELECT COUNT(DISTINCT city || ':' || name_canonical || ':' || COALESCE(street_type, '')) FROM streets"
        ).fetchone()[0]

        if category in ("all", "settlement"):
            sql_s = """
                SELECT city, province, district, GROUP_CONCAT(alias_norm, ', ') AS aliases
                FROM settlements
                GROUP BY city, province
            """
            s_limit = safe_limit if category == "settlement" else max(20, safe_limit // 4)
            s_count = 0
            for idx, row in enumerate(cur.execute(sql_s)):
                city_val = row["city"] or ""
                prov_val = row["province"] or ""
                dist_val = row["district"] or ""
                aliases_str = row["aliases"] or ""
                if q_clean:
                    haystack = f"{city_val} {prov_val} {dist_val} {aliases_str}".lower()
                    if q_clean not in haystack:
                        continue
                items.append(
                    {
                        "id": f"kato_{idx}",
                        "category": "settlement",
                        "name": city_val,
                        "street_type": None,
                        "city": city_val,
                        "province": prov_val,
                        "district": row["district"],
                        "aliases": [a for a in aliases_str.split(", ") if a][:4],
                    }
                )
                s_count += 1
                if s_count >= s_limit:
                    break

        if category in ("all", "street", "microdistrict", "quarter"):
            sql_st = """
                SELECT name_canonical, street_type, city, default_district, province, GROUP_CONCAT(name_norm, ', ') AS aliases
                FROM streets
                WHERE 1=1
            """
            if category == "microdistrict":
                sql_st += " AND street_type = 'микрорайон'"
            elif category == "quarter":
                sql_st += " AND street_type = 'квартал'"
            elif category == "street":
                sql_st += " AND COALESCE(street_type, 'улица') NOT IN ('микрорайон', 'квартал')"

            sql_st += " GROUP BY city, name_canonical, street_type"

            st_count = 0
            for idx, row in enumerate(cur.execute(sql_st)):
                name_val = row["name_canonical"] or ""
                st_type = row["street_type"] or "улица"
                city_val = row["city"] or ""
                prov_val = row["province"] or ""
                dist_val = row["default_district"] or ""
                aliases_str = row["aliases"] or ""

                if q_clean:
                    haystack = f"{name_val} {st_type} {city_val} {prov_val} {dist_val} {aliases_str}".lower()
                    if q_clean not in haystack:
                        continue

                cat = (
                    "microdistrict"
                    if st_type == "микрорайон"
                    else "quarter"
                    if st_type == "квартал"
                    else "street"
                )
                items.append(
                    {
                        "id": f"osm_{idx}",
                        "category": cat,
                        "name": name_val,
                        "street_type": st_type,
                        "city": city_val,
                        "province": prov_val,
                        "district": row["default_district"],
                        "aliases": [a for a in aliases_str.split(", ") if a][:4],
                    }
                )
                st_count += 1
                if st_count >= safe_limit:
                    break

    return {
        "items": items[:safe_limit],
        "total_settlements": total_settlements,
        "total_streets": total_streets,
    }


def parse_addresses(payload: BatchParsePayload) -> List[ParsedAddressItem]:
    """
    Пакетный разбор адресных строк.
    Принимает как чистый JSON-массив `[{"id": "...", "raw_address": "..."}]`,
    так и обёртку `{"records": [...]}` или `{"items": [...]}`.
    Возвращает ровно столько же объектов в том же порядке.
    """
    items = _extract_raw_items(payload)
    return pipeline.parse_batch(items)


try:
    from fastapi import FastAPI, File, HTTPException, UploadFile
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(
        title="Jana Address API (Jana Post)",
        description=(
            "Автономный REST API сервис нормализации и гео-обогащения адресов доставки РК "
            "(КАТО 2026 + OpenStreetMap)."
        ),
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.get("/api/health")(health_check)
    app.get("/health")(health_check)
    app.get("/api/reference")(reference_search)
    app.post("/api/parse", response_model=List[ParsedAddressItem])(parse_addresses)
    app.post("/parse", response_model=List[ParsedAddressItem])(parse_addresses)

    @app.post("/api/parse-file", response_model=List[ParsedAddressItem])
    async def parse_address_file(file: UploadFile = File(...)) -> List[ParsedAddressItem]:
        """Загрузка и разбор JSON-файла напрямую через multipart/form-data."""
        try:
            raw_bytes = await file.read()
            data = json.loads(raw_bytes.decode("utf-8"))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Некорректный JSON-файл: {exc}") from exc

        if isinstance(data, dict):
            records_raw = data.get("records") or data.get("items") or []
        elif isinstance(data, list):
            records_raw = data
        else:
            raise HTTPException(status_code=400, detail="Ожидается JSON-массив объектов")

        items = [
            RawAddressItem(
                id=str(item.get("id", f"rec_{idx + 1:05d}")),
                raw_address=str(item.get("raw_address", "")),
            )
            for idx, item in enumerate(records_raw)
            if isinstance(item, dict)
        ]
        return pipeline.parse_batch(items)

except ImportError:
    app = None  # type: ignore[assignment]


class _StdlibRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, body: Any) -> None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send_json(200, {"status": "ok"})

    def do_GET(self) -> None:  # noqa: N802
        from urllib.parse import parse_qs, urlparse

        parsed_url = urlparse(self.path)
        clean_path = parsed_url.path.rstrip("/")
        if clean_path in ("/api/health", "/health"):
            self._send_json(200, health_check())
        elif clean_path == "/api/reference":
            qs = parse_qs(parsed_url.query)
            q_val = qs.get("q", [""])[0]
            cat_val = qs.get("category", ["all"])[0]
            self._send_json(200, reference_search(q=q_val, category=cat_val))
        else:
            self._send_json(404, {"detail": "Not Found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") in ("/api/parse", "/parse"):
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length).decode("utf-8")
            data = json.loads(raw_body) if raw_body else []
            parsed = parse_addresses(data)
            self._send_json(200, [item.model_dump() for item in parsed])
        else:
            self._send_json(404, {"detail": "Not Found"})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    if app is not None:
        try:
            import uvicorn

            uvicorn.run(app, host="0.0.0.0", port=port)
        except ImportError:
            server = HTTPServer(("0.0.0.0", port), _StdlibRequestHandler)
            print(f"[Jana Address API] Сервер запущен на http://0.0.0.0:{port}")
            server.serve_forever()
    else:
        server = HTTPServer(("0.0.0.0", port), _StdlibRequestHandler)
        print(f"[Jana Address API] Сервер запущен на http://0.0.0.0:{port}")
        server.serve_forever()


