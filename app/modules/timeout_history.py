"""
modules/timeout_history.py
Manejo del histórico de timeouts en CSV local.

FIX: Deduplicación mejorada usando clave compuesta con codigo para evitar
     colapsar registros distintos con mismo timestamp/operador/proceso/time_taken.
FIX: Rutas absolutas para que funcione sin importar desde dónde se ejecute Streamlit.
FIX: Manejo robusto de PermissionError y validación de que HISTORY_FILE no sea carpeta.
FIX: Escritura atómica vía archivo temporal + os.replace para evitar corrupción.
FIX: CSV guardado con BOM UTF-8 + separador ';' para que Excel español lo abra
     con tildes correctas y columnas separadas al hacer doble-click.
"""
import os
import tempfile
import pandas as pd
from datetime import datetime

# ── RUTA ABSOLUTA — funciona sin importar el cwd de Streamlit ──────────────
_BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_DIR  = os.path.join(_BASE_DIR, "data")
HISTORY_FILE = os.path.join(HISTORY_DIR, "timeout_history.csv")
# ───────────────────────────────────────────────────────────────────────────

# ── FORMATO CSV PARA EXCEL ESPAÑOL ────────────────────────────────────────
# Excel en configuración regional español/latam espera ';' como separador
# y necesita BOM (utf-8-sig) para detectar UTF-8 y mostrar tildes bien.
CSV_SEP      = ";"
CSV_ENCODING = "utf-8-sig"
# ───────────────────────────────────────────────────────────────────────────

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
    """
    Garantiza que data/ exista y que timeout_history.csv sea archivo válido.
    Levanta errores claros si algo está mal.
    """
    try:
        os.makedirs(HISTORY_DIR, exist_ok=True)
    except PermissionError as e:
        raise PermissionError(
            f"No se puede crear/acceder a la carpeta: {HISTORY_DIR}\n"
            f"Verifica permisos de escritura. Detalle: {e}"
        )

    ruta_sin_ext = os.path.join(HISTORY_DIR, "timeout_history")
    if os.path.isdir(ruta_sin_ext):
        raise IsADirectoryError(
            f"Existe una CARPETA llamada 'timeout_history' (sin .csv) en "
            f"{HISTORY_DIR}. Bórrala manualmente:\n"
            f"  rmdir /S /Q \"{ruta_sin_ext}\"   (Windows)"
        )

    if os.path.exists(HISTORY_FILE) and not os.path.isfile(HISTORY_FILE):
        raise IsADirectoryError(
            f"La ruta '{HISTORY_FILE}' existe pero NO es un archivo. "
            f"Elimínala manualmente y vuelve a intentar."
        )

    if not os.path.exists(HISTORY_FILE):
        try:
            pd.DataFrame(columns=COLUMNAS).to_csv(
                HISTORY_FILE, index=False, sep=CSV_SEP, encoding=CSV_ENCODING
            )
        except PermissionError as e:
            raise PermissionError(
                f"No se puede crear el archivo: {HISTORY_FILE}\n"
                f"Posibles causas:\n"
                f"  - El archivo está abierto en Excel (ciérralo).\n"
                f"  - Antivirus / OneDrive lo tiene bloqueado.\n"
                f"  - No tienes permisos de escritura en la carpeta.\n"
                f"Detalle: {e}"
            )


def _leer_csv_compat(path):
    """
    Lee el CSV intentando primero el formato nuevo (sep=';', utf-8-sig)
    y si falla cae al formato viejo (sep=',', utf-8). Migra transparente
    el CSV existente sin perder datos.
    """
    # Intento 1: formato nuevo (';' + utf-8-sig)
    try:
        df = pd.read_csv(path, sep=CSV_SEP, encoding=CSV_ENCODING)
        # Si el archivo viejo tenía coma, al leer con ';' queda 1 sola columna
        if len(df.columns) == 1:
            raise ValueError("Probablemente formato viejo con coma")
        return df
    except Exception:
        pass

    # Intento 2: formato viejo (coma + utf-8)
    try:
        return pd.read_csv(path, sep=",", encoding="utf-8")
    except Exception:
        pass

    # Intento 3: último recurso, autodetectar
    try:
        return pd.read_csv(path, sep=None, engine="python")
    except Exception:
        return pd.DataFrame(columns=COLUMNAS)


def _escribir_csv_atomico(df: pd.DataFrame):
    """Escribe el CSV de forma atómica: archivo temporal + os.replace."""
    fd, tmp_path = tempfile.mkstemp(
        prefix=".timeout_history_", suffix=".csv.tmp", dir=HISTORY_DIR
    )
    try:
        with os.fdopen(fd, "w", encoding=CSV_ENCODING, newline="") as f:
            df.to_csv(f, index=False, sep=CSV_SEP)
        os.replace(tmp_path, HISTORY_FILE)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise


def guardar_timeouts_raw(df_nuevos):
    _asegurar_archivo()
    if df_nuevos.empty:
        return 0
    for col in COLUMNAS:
        if col not in df_nuevos.columns:
            df_nuevos[col] = ""

    try:
        df_hist = _leer_csv_compat(HISTORY_FILE)
        # Asegurar columnas (por si el viejo no las tenía todas)
        for col in COLUMNAS:
            if col not in df_hist.columns:
                df_hist[col] = ""
    except Exception:
        df_hist = pd.DataFrame(columns=COLUMNAS)

    antes = len(df_hist)
    df_c = pd.concat([df_hist[COLUMNAS], df_nuevos[COLUMNAS]], ignore_index=True)

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

    try:
        _escribir_csv_atomico(df_c)
    except PermissionError as e:
        raise PermissionError(
            f"No se pudo guardar {HISTORY_FILE}.\n"
            f"Cierra el archivo si lo tienes abierto en Excel y reintenta.\n"
            f"Detalle: {e}"
        )

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
        df = _leer_csv_compat(HISTORY_FILE)
        if df.empty:
            return pd.DataFrame(columns=COLUMNAS)
        for col in COLUMNAS:
            if col not in df.columns:
                df[col] = ""
        df["fecha_timeout"]   = pd.to_datetime(df["fecha_timeout"],   errors="coerce")
        df["fecha_deteccion"] = pd.to_datetime(df["fecha_deteccion"], errors="coerce")
        return df.sort_values("fecha_timeout", ascending=False)
    except Exception:
        return pd.DataFrame(columns=COLUMNAS)


def limpiar_historico():
    if os.path.exists(HISTORY_FILE) and os.path.isfile(HISTORY_FILE):
        pd.DataFrame(columns=COLUMNAS).to_csv(
            HISTORY_FILE, index=False, sep=CSV_SEP, encoding=CSV_ENCODING
        )


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