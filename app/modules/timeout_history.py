"""
modules/timeout_history.py
Manejo del histórico de timeouts en CSV local.
FIX: Deduplicación mejorada usando clave compuesta con codigo para evitar
     colapsar registros distintos con mismo timestamp/operador/proceso/time_taken.
"""
import pandas as pd
import os
from datetime import datetime

HISTORY_FILE = "data/timeout_history.csv"
COLUMNAS = [
    "fecha_deteccion",
    "fecha_timeout",
    "operador",
    "proceso",
    "codigo",
    "descripcion",
    "rango_consulta",
    "time_taken_ms",
    "status",
    "status_code",
]


def _asegurar_archivo():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(HISTORY_FILE):
        pd.DataFrame(columns=COLUMNAS).to_csv(HISTORY_FILE, index=False)


def guardar_timeouts_raw(df_nuevos):
    _asegurar_archivo()
    if df_nuevos.empty:
        return 0
    for col in COLUMNAS:
        if col not in df_nuevos.columns:
            df_nuevos[col] = ""
    try:
        df_hist = pd.read_csv(HISTORY_FILE)
    except Exception:
        df_hist = pd.DataFrame(columns=COLUMNAS)

    antes = len(df_hist)
    df_c = pd.concat([df_hist, df_nuevos[COLUMNAS]], ignore_index=True)

    df_c["_key"] = (
        df_c["fecha_timeout"].astype(str).str[:19] + "|" +
        df_c["operador"].astype(str) + "|" +
        df_c["proceso"].astype(str) + "|" +
        df_c["time_taken_ms"].astype(str) + "|" +
        df_c["codigo"].astype(str)
    )
    df_c = df_c.drop_duplicates(subset=["_key"], keep="first")
    df_c = df_c.drop(columns=["_key"])
    df_c = df_c.sort_values("fecha_timeout", ascending=False)
    df_c.to_csv(HISTORY_FILE, index=False)
    return max(len(df_c) - antes, 0)


def guardar_timeouts(df, operador, rango_consulta):
    _asegurar_archivo()
    if df.empty:
        return 0

    df_to = pd.DataFrame()
    if "Es_Timeout" in df.columns:
        df_to = df[df["Es_Timeout"] == True].copy()
    if "timetaken" in df.columns:
        df_slow = df[pd.to_numeric(df["timetaken"], errors="coerce") > 30000].copy()
        df_to = pd.concat([df_to, df_slow]).drop_duplicates()
    if df_to.empty:
        return 0

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    registros = []
    for _, row in df_to.iterrows():
        t = pd.to_numeric(row.get("timetaken", 0), errors="coerce") or 0
        registros.append({
            "fecha_deteccion": ahora,
            "fecha_timeout":   str(row.get("timestamp", ""))[:19],
            "operador":        operador,
            "proceso":         row.get("requestrequestdescription", "Desconocido"),
            "codigo":          f"TIMEOUT_{int(t)}ms",
            "descripcion":     f"Timeout: {int(t):,}ms",
            "rango_consulta":  rango_consulta,
            "time_taken_ms":   int(t) if t else 0,
            "status":          row.get("status", ""),
            "status_code":     str(row.get("statuscode", "")),
        })
    return guardar_timeouts_raw(pd.DataFrame(registros))


def leer_historico():
    _asegurar_archivo()
    try:
        df = pd.read_csv(HISTORY_FILE)
        if df.empty:
            return pd.DataFrame(columns=COLUMNAS)
        df["fecha_timeout"]   = pd.to_datetime(df["fecha_timeout"],   errors="coerce")
        df["fecha_deteccion"] = pd.to_datetime(df["fecha_deteccion"], errors="coerce")
        return df.sort_values("fecha_timeout", ascending=False)
    except Exception:
        return pd.DataFrame(columns=COLUMNAS)


def limpiar_historico():
    if os.path.exists(HISTORY_FILE):
        pd.DataFrame(columns=COLUMNAS).to_csv(HISTORY_FILE, index=False)


def estadisticas_historico(df):
    if df.empty:
        return {
            "total":         0,
            "por_operador":  {},
            "por_proceso":   {},
            "primer_evento": None,
            "ultimo_evento": None,
        }
    return {
        "total":         len(df),
        "por_operador":  df["operador"].value_counts().to_dict(),
        "por_proceso":   df["proceso"].value_counts().to_dict(),
        "primer_evento": df["fecha_timeout"].min(),
        "ultimo_evento": df["fecha_timeout"].max(),
    }