"""
modules/kibana_client.py
Conexion a Elasticsearch via sesion autenticada de Kibana.
Indice: http-rest-service-*

ACTUALIZACIÓN: Se agrega campo timeTaken al source para detectar
timeouts reales (transacciones que tardaron > 30,000 ms).
FIX: Se agrega restCallTimeTaken como campo alternativo en source y extracción.
Confirmado en Kibana: el código 100-5 no existe en este sistema.
Los timeouts se identifican por timeTaken > 30000 o restCallTimeTaken > 30000.
"""
import requests
import urllib3
import json
import os
import pandas as pd
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

KIBANA_URL = "https://kibana-atp.tecnotree.com"
USER       = os.getenv("KIBANA_USER", "atp_operations")
PASSWORD   = os.getenv("KIBANA_PASSWORD", "ATPOperations_2025")
INDEX      = "http-rest-service-*"
PAGE_SIZE  = 5000
TZ         = timezone.utc

UUID_CLARO = "bfa64110-9851-462f-858a-563c7e88dcb2"
UUID_ETB   = "9f722166-aea5-4ead-b19b-1b80eb45de76"

UMBRAL_TIMEOUT_MS = 30000  # 30 segundos — confirmado en Kibana

_session_cache = {"session": None, "expires": None}


def _rango_a_fechas(rango: str) -> tuple:
    ahora = datetime.now(TZ)
    fmt   = "%Y-%m-%dT%H:%M:%S.000Z"
    deltas = {
        "now-15m": timedelta(minutes=15),
        "now-30m": timedelta(minutes=30),
        "now-1h":  timedelta(hours=1),
        "now-6h":  timedelta(hours=6),
        "now-24h": timedelta(hours=24),
        "now-7d":  timedelta(days=7),
        "now-30d": timedelta(days=30),
        "now-90d": timedelta(days=90),
        "now-1y":  timedelta(days=365),
    }
    if rango == "today":
        inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        return inicio.strftime(fmt), ahora.strftime(fmt)
    if rango == "week":
        inicio = (ahora - timedelta(days=ahora.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0)
        return inicio.strftime(fmt), ahora.strftime(fmt)
    delta = deltas.get(rango, timedelta(hours=24))
    return (ahora - delta).strftime(fmt), ahora.strftime(fmt)


def _build_query(operador: str, fecha_ini: str, fecha_fin: str) -> dict:
    rango = {"range": {"@timestamp": {"gte": fecha_ini, "lte": fecha_fin}}}

    if operador == "CLARO":
        return {
            "bool": {
                "must": [rango],
                "should": [
                    {"match_phrase": {"request.Request.relatedParty.name": "VNO"}},
                    {"match_phrase": {"request.Request.relatedParty.name": "CLARO"}},
                    {"term": {"request.Request.relatedParty.id.keyword": UUID_CLARO}},
                ],
                "minimum_should_match": 1,
            }
        }

    if operador == "ETB":
        return {
            "bool": {
                "must": [rango],
                "should": [
                    {"match_phrase": {"request.Request.relatedParty.name": "ETB"}},
                    {"term": {"request.Request.relatedParty.id.keyword": UUID_ETB}},
                ],
                "minimum_should_match": 1,
            }
        }

    return {
        "bool": {
            "must": [rango],
            "should": [
                {"match_phrase": {"request.Request.relatedParty.name": "VNO"}},
                {"match_phrase": {"request.Request.relatedParty.name": "CLARO"}},
                {"match_phrase": {"request.Request.relatedParty.name": "ETB"}},
                {"term": {"request.Request.relatedParty.id.keyword": UUID_CLARO}},
                {"term": {"request.Request.relatedParty.id.keyword": UUID_ETB}},
            ],
            "minimum_should_match": 1,
        }
    }


def _login_selenium() -> dict:
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        driver = webdriver.Chrome(options=options)
        wait   = WebDriverWait(driver, 30)
        driver.get(f"{KIBANA_URL}/app/home#/")
        username = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "input[data-test-subj='loginUsername']")))
        username.send_keys(USER)
        driver.find_element(By.CSS_SELECTOR,
            "input[data-test-subj='loginPassword']").send_keys(PASSWORD)
        driver.find_element(By.CSS_SELECTOR,
            "button[data-test-subj='loginSubmit']").click()
        wait.until(EC.invisibility_of_element_located(
            (By.CSS_SELECTOR, "input[data-test-subj='loginUsername']")))
        cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
        driver.quit()
        return cookies
    except Exception as e:
        raise Exception(f"Login Selenium fallido: {e}")


def _get_session() -> requests.Session:
    global _session_cache
    if (_session_cache["session"] is not None and
            _session_cache["expires"] is not None and
            datetime.now() < _session_cache["expires"]):
        return _session_cache["session"]

    session = requests.Session()
    session.verify  = False
    session.headers.update({"kbn-xsrf": "true", "Content-Type": "application/json"})
    session.auth = (USER, PASSWORD)

    try:
        r = session.post(
            f"{KIBANA_URL}/internal/security/login",
            json={"providerType": "basic", "providerName": "basic",
                  "currentURL": f"{KIBANA_URL}/login",
                  "params": {"username": USER, "password": PASSWORD}},
            timeout=15)
        if r.status_code in (200, 204):
            _session_cache = {"session": session,
                              "expires": datetime.now() + timedelta(hours=1)}
            return session
    except Exception:
        pass

    try:
        cookies = _login_selenium()
        session.auth = None
        session.cookies.update(cookies)
        _session_cache = {"session": session,
                          "expires": datetime.now() + timedelta(hours=1)}
        return session
    except Exception:
        pass

    _session_cache = {"session": session,
                      "expires": datetime.now() + timedelta(minutes=10)}
    return session


def _buscar(session: requests.Session, payload: dict) -> dict:
    body = json.dumps(payload)
    endpoints = [
        f"{KIBANA_URL}/api/console/proxy?path={INDEX}/_search&method=POST",
        f"{KIBANA_URL}/elasticsearch/{INDEX}/_search",
        f"https://localhost:8443/api/console/proxy?path={INDEX}/_search&method=POST",
        f"https://localhost:8443/elasticsearch/{INDEX}/_search",
        f"http://localhost:8088/api/console/proxy?path={INDEX}/_search&method=POST",
    ]
    last_err = ""
    for url in endpoints:
        try:
            r = session.post(url, data=body, timeout=60)
            if r.status_code == 200 and r.text.strip().startswith("{"):
                data = r.json()
                if "hits" in data:
                    return data
            last_err = f"{url} -> {r.status_code}"
        except Exception as e:
            last_err = f"{url} -> {str(e)[:50]}"
    raise Exception(f"Todos los endpoints fallaron. Ultimo: {last_err}")


def verificar_conexion() -> dict:
    try:
        session = _get_session()
        for base in [KIBANA_URL, "https://localhost:8443", "http://localhost:8088"]:
            try:
                r = session.get(f"{base}/api/status", timeout=5)
                if r.status_code == 200:
                    return {"ok": True, "msg": "Conectado a Kibana ✅"}
            except Exception:
                pass
        return {"ok": False, "msg": "Sin conexion a Kibana"}
    except Exception as e:
        return {"ok": False, "msg": str(e)}


def _extraer_fila(hit: dict) -> dict:
    s   = hit.get("_source", {})
    req = s.get("request", {}).get("Request", {})

    descripcion = req.get("description", "")

    rp = req.get("relatedParty", [])
    if isinstance(rp, list) and rp:
        rp_id   = rp[0].get("id", "")
        rp_name = rp[0].get("name", "")
    elif isinstance(rp, dict):
        rp_id   = rp.get("id", "")
        rp_name = rp.get("name", "")
    else:
        rp_id   = ""
        rp_name = ""

    if rp_name in ("VNO", "CLARO") or rp_id == UUID_CLARO:
        name = "CLARO"
    elif rp_name == "ETB" or rp_id == UUID_ETB:
        name = "ETB"
    else:
        name = rp_name or "Desconocido"

    code   = ""
    reason = ""

    resp = (s.get("response", {})
             .get("response", {})
             .get("finalResponse", {})
             .get("response", {}))
    if resp:
        c  = str(resp.get("code", "")).strip()
        r2 = str(resp.get("reason", "")).strip()
        if c and c not in ("None", "nan", "none", ""):
            code, reason = c, r2

    if not code:
        resp_may = (s.get("response", {})
                     .get("response", {})
                     .get("finalResponse", {})
                     .get("Response", {}))
        if resp_may:
            c  = str(resp_may.get("code", "")).strip()
            r2 = str(resp_may.get("reason", "")).strip()
            if c and c not in ("None", "nan", "none", ""):
                code, reason = c, r2

    if not code:
        resp_alt = (s.get("response", {})
                     .get("finalResponse", {})
                     .get("response", {}))
        if resp_alt:
            c  = str(resp_alt.get("code", "")).strip()
            r2 = str(resp_alt.get("reason", "")).strip()
            if c and c not in ("None", "nan", "none", ""):
                code, reason = c, r2

    if not code:
        ext = str(s.get("extCallStatus", "")).strip()
        if ext and ext not in ("", "None", "nan"):
            code = ext

    if code in ("None", "nan", "none"):
        code = ""

    # FIX: fallback a restCallTimeTaken si timeTaken es None
    time_taken = s.get("timeTaken") or s.get("restCallTimeTaken")

    return {
        "timestamp":                                   s.get("@timestamp", ""),
        "requestrequestdescription":                   descripcion,
        "requestrequestrelatedpartyname":              name,
        "responseresponsefinalresponseresponsecode":   code,
        "responseresponsefinalresponseresponsereason": reason,
        "timetaken":                                   time_taken,
    }


def _paginar(session, query_base, source) -> tuple:
    all_rows     = []
    search_after = None
    pagina       = 0

    while True:
        payload = {
            "size": PAGE_SIZE, "track_total_hits": True,
            "_source": source, "query": query_base,
            "sort": [
                {"@timestamp": {"order": "desc"}},
                {"_id":        {"order": "asc"}},
            ],
        }
        if search_after:
            payload["search_after"] = search_after

        try:
            data = _buscar(session, payload)
        except Exception as e:
            if pagina == 0:
                return [], str(e)
            break

        hits = data.get("hits", {}).get("hits", [])
        if pagina == 0 and not hits:
            return [], "Sin datos en el rango"

        for h in hits:
            all_rows.append(_extraer_fila(h))

        pagina += 1
        if len(hits) < PAGE_SIZE:
            break
        search_after = hits[-1].get("sort")
        if not search_after:
            break

    return all_rows, None


def obtener_total_registros(operador: str, rango: str) -> dict:
    fecha_ini, fecha_fin = _rango_a_fechas(rango)
    payload = {"size": 0, "track_total_hits": True,
               "query": _build_query(operador, fecha_ini, fecha_fin)}
    try:
        data  = _buscar(_get_session(), payload)
        total = data.get("hits", {}).get("total", {})
        if isinstance(total, dict):
            total = total.get("value", 0)
        return {"ok": True, "total": total}
    except Exception as e:
        return {"ok": False, "total": 0, "msg": str(e)}


def obtener_total_custom(operador: str, fecha_ini: str, fecha_fin: str) -> dict:
    payload = {"size": 0, "track_total_hits": True,
               "query": _build_query(operador, fecha_ini, fecha_fin)}
    try:
        data  = _buscar(_get_session(), payload)
        total = data.get("hits", {}).get("total", {})
        if isinstance(total, dict):
            total = total.get("value", 0)
        return {"ok": True, "total": total}
    except Exception as e:
        return {"ok": False, "total": 0, "msg": str(e)}


def obtener_transacciones_raw(operador: str, rango: str):
    fecha_ini, fecha_fin = _rango_a_fechas(rango)
    source = [
        "@timestamp",
        "timeTaken",
        "restCallTimeTaken",   # FIX: campo alternativo
        "extCallStatus",
        "statusCode",
        "request.Request.description",
        "request.Request.relatedParty.name",
        "request.Request.relatedParty.id",
        "response.response.finalResponse.response.code",
        "response.response.finalResponse.response.reason",
        "response.response.finalResponse.Response.code",
        "response.response.finalResponse.Response.reason",
        "response.finalResponse.response.code",
        "response.finalResponse.response.reason",
    ]
    rows, err = _paginar(
        _get_session(),
        _build_query(operador, fecha_ini, fecha_fin),
        source
    )
    if err:
        return pd.DataFrame(), err
    df = pd.DataFrame(rows)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df, None


def obtener_transacciones_custom(operador: str, fecha_ini: str, fecha_fin: str):
    source = [
        "@timestamp",
        "timeTaken",
        "restCallTimeTaken",   # FIX: campo alternativo
        "extCallStatus",
        "statusCode",
        "request.Request.description",
        "request.Request.relatedParty.name",
        "request.Request.relatedParty.id",
        "response.response.finalResponse.response.code",
        "response.response.finalResponse.response.reason",
        "response.response.finalResponse.Response.code",
        "response.response.finalResponse.Response.reason",
        "response.finalResponse.response.code",
        "response.finalResponse.response.reason",
    ]
    rows, err = _paginar(
        _get_session(),
        _build_query(operador, fecha_ini, fecha_fin),
        source
    )
    if err:
        return pd.DataFrame(), err
    df = pd.DataFrame(rows)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df, None


def obtener_kpis_agrupados(operador: str, rango: str):
    fecha_ini, fecha_fin = _rango_a_fechas(rango)
    payload = {
        "size": 0, "track_total_hits": True,
        "query": _build_query(operador, fecha_ini, fecha_fin),
        "aggs": {
            "por_proceso": {
                "terms": {
                    "field": "request.Request.description.keyword",
                    "size":  50,
                }
            },
            "timeline": {
                "date_histogram": {
                    "field":          "@timestamp",
                    "fixed_interval": "1h",
                    "min_doc_count":  0,
                },
                "aggs": {
                    "por_proceso": {
                        "terms": {
                            "field": "request.Request.description.keyword",
                            "size":  20,
                        }
                    }
                },
            },
        },
    }
    try:
        data = _buscar(_get_session(), payload)
        return data.get("aggregations", {}), None
    except Exception as e:
        return {}, str(e)