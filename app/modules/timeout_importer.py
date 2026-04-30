"""
modules/timeout_importer.py
FIX: Timestamps convertidos de UTC a COT (UTC-5).
FIX: restCallTimeTaken como campo alternativo.
"""
import pandas as pd
from datetime import datetime, timezone, timedelta

from modules.kibana_client import _get_session, _buscar, UUID_CLARO, UUID_ETB
from modules.timeout_history import guardar_timeouts_raw, HISTORY_FILE

UMBRAL_TIMEOUT_MS = 30000
COT = timezone(timedelta(hours=-5))


def _utc_a_cot(timestamp_str: str) -> str:
    if not timestamp_str:
        return ""
    try:
        ts = timestamp_str.replace("Z", "+00:00")
        dt_utc = datetime.fromisoformat(ts)
        dt_cot = dt_utc.astimezone(COT)
        return dt_cot.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(timestamp_str)[:19].replace("T", " ")


def _build_query_timeouts(operador: str, fecha_ini: str, fecha_fin: str) -> dict:
    rango = {"range": {"@timestamp": {"gte": fecha_ini, "lte": fecha_fin}}}
    filtro_tiempo = {
        "bool": {
            "should": [
                {"range": {"timeTaken":        {"gt": UMBRAL_TIMEOUT_MS}}},
                {"range": {"restCallTimeTaken": {"gt": UMBRAL_TIMEOUT_MS}}},
            ],
            "minimum_should_match": 1,
        }
    }
    if operador == "CLARO":
        filtro_op = {"bool": {"should": [
            {"match_phrase": {"request.Request.relatedParty.name": "VNO"}},
            {"match_phrase": {"request.Request.relatedParty.name": "CLARO"}},
            {"term": {"request.Request.relatedParty.id.keyword": UUID_CLARO}},
        ], "minimum_should_match": 1}}
    else:
        filtro_op = {"bool": {"should": [
            {"match_phrase": {"request.Request.relatedParty.name": "ETB"}},
            {"term": {"request.Request.relatedParty.id.keyword": UUID_ETB}},
        ], "minimum_should_match": 1}}
    return {"bool": {"must": [rango, filtro_tiempo, filtro_op]}}


def _extraer_fila_timeout(hit: dict, operador: str) -> dict:
    s = hit.get("_source", {})
    fecha_timeout_cot = _utc_a_cot(s.get("@timestamp", ""))
    time_taken = int(s.get("timeTaken") or s.get("restCallTimeTaken") or 0)
    status      = s.get("status", "")
    status_code = str(s.get("statusCode", s.get("extCallStatus", "")))

    descripcion = ""
    req = s.get("request", {})
    if isinstance(req, dict):
        descripcion = req.get("Request", {}).get("description", "") or req.get("description", "")
    if not descripcion:
        descripcion = s.get("request.Request.description", "")

    from modules.data_processor import MAPEO
    proceso = MAPEO.get(
        str(descripcion).strip().lower(),
        str(descripcion).title() if descripcion else "Desconocido"
    )

    return {
        "fecha_deteccion": datetime.now(COT).strftime("%Y-%m-%d %H:%M:%S"),
        "fecha_timeout":   fecha_timeout_cot,
        "operador":        operador,
        "proceso":         proceso,
        "codigo":          f"TIMEOUT_{time_taken}ms",
        "descripcion":     f"Respuesta lenta: {time_taken:,} ms (>{UMBRAL_TIMEOUT_MS // 1000}s)",
        "rango_consulta":  "Importación histórica",
        "time_taken_ms":   time_taken,
        "status":          status,
        "status_code":     status_code,
    }


def importar_historico_elasticsearch(
    meses_atras: int = 3,
    operadores: list = None,
    progress_callback=None,
) -> dict:
    if operadores is None:
        operadores = ["CLARO", "ETB"]

    ahora     = datetime.now(timezone.utc)
    fmt       = "%Y-%m-%dT%H:%M:%S.000Z"
    fecha_fin = ahora.strftime(fmt)
    fecha_ini = (ahora - timedelta(days=meses_atras * 30)).strftime(fmt)

    resumen = {
        "fecha_ini":    fecha_ini,
        "fecha_fin":    fecha_fin,
        "meses_atras":  meses_atras,
        "por_operador": {},
        "total_nuevos": 0,
        "errores":      [],
    }

    source = [
        "@timestamp", "timeTaken", "restCallTimeTaken",
        "status", "statusCode", "extCallStatus",
        "request.Request.description",
        "request.Request.relatedParty.name",
        "request.Request.relatedParty.id",
    ]

    session = _get_session()

    for op in operadores:
        if progress_callback:
            progress_callback(f"Consultando {op} — timeouts (>{UMBRAL_TIMEOUT_MS // 1000}s) desde {fecha_ini[:10]}...")
        try:
            all_rows     = []
            search_after = None
            pagina       = 0
            PAGE_SIZE    = 5000

            while True:
                payload = {
                    "size": PAGE_SIZE, "track_total_hits": True,
                    "_source": source,
                    "query":   _build_query_timeouts(op, fecha_ini, fecha_fin),
                    "sort": [
                        {"@timestamp": {"order": "desc"}},
                        {"_id":        {"order": "asc"}},
                    ],
                }
                if search_after:
                    payload["search_after"] = search_after

                data = _buscar(session, payload)
                hits = data.get("hits", {}).get("hits", [])

                if pagina == 0:
                    total_es = data.get("hits", {}).get("total", {})
                    if isinstance(total_es, dict):
                        total_es = total_es.get("value", 0)
                    if progress_callback:
                        progress_callback(f"{op}: {total_es:,} timeouts encontrados en Elasticsearch")

                if not hits:
                    break

                for h in hits:
                    all_rows.append(_extraer_fila_timeout(h, op))

                pagina += 1
                if progress_callback and pagina % 5 == 0:
                    progress_callback(f"{op}: página {pagina} — {len(all_rows):,} registros...")

                if len(hits) < PAGE_SIZE:
                    break
                search_after = hits[-1].get("sort")
                if not search_after:
                    break

            if not all_rows:
                resumen["por_operador"][op] = {"encontrados": 0, "nuevos": 0}
                if progress_callback:
                    progress_callback(f"{op}: Sin timeouts en el período")
                continue

            nuevos = guardar_timeouts_raw(pd.DataFrame(all_rows))
            resumen["por_operador"][op] = {"encontrados": len(all_rows), "nuevos": nuevos}
            resumen["total_nuevos"] += nuevos
            if progress_callback:
                progress_callback(f"✅ {op}: {len(all_rows):,} timeouts — {nuevos} nuevos guardados")

        except Exception as e:
            resumen["errores"].append(f"{op}: {str(e)}")
            resumen["por_operador"][op] = {"encontrados": 0, "nuevos": 0, "error": str(e)}
            if progress_callback:
                progress_callback(f"❌ {op}: Error — {str(e)[:80]}")

    return resumen


def contar_timeouts_elasticsearch(meses_atras: int = 3) -> dict:
    ahora     = datetime.now(timezone.utc)
    fmt       = "%Y-%m-%dT%H:%M:%S.000Z"
    fecha_fin = ahora.strftime(fmt)
    fecha_ini = (ahora - timedelta(days=meses_atras * 30)).strftime(fmt)
    session   = _get_session()
    resultado = {}

    for op in ["CLARO", "ETB"]:
        try:
            data = _buscar(session, {
                "size": 0, "track_total_hits": True,
                "query": _build_query_timeouts(op, fecha_ini, fecha_fin),
            })
            total = data.get("hits", {}).get("total", {})
            if isinstance(total, dict):
                total = total.get("value", 0)
            resultado[op] = {"total": total, "ok": True}
        except Exception as e:
            resultado[op] = {"total": 0, "ok": False, "error": str(e)}

    return resultado