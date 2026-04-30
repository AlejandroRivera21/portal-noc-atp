"""
modules/data_processor.py
Logica de negocio ATP — MAPEO, SLA tecnico, clasificacion de errores.

ACTUALIZACIÓN: Los timeouts reales se detectan por timeTaken > 30,000 ms.
El código 100-5 no existe en el índice http-rest-service-*.
Confirmado en Kibana Discover el 29/04/2026.
"""
import pandas as pd
import re
from datetime import datetime

MAPEO = {
    'addservice':       'Activación Servicios',
    'addont':           'Activación ONT',
    'activateservice':  'Reconexión',
    'deleteservice':    'Eliminación servicio',
    'deleteont':        'Terminación',
    'changeont':        'Cambio ONT',
    'suspendservice':   'Suspensión',
    'statusquery':      'Estado servicio',
    'bandwidthquery':   'Ancho de banda',
    'neighborsquery':   'Soporte N1 Vecinos',
    'signallevelquery': 'Consulta niveles',
    'check':            'Consulta Disponibilidad',
    'add':              'Reserva',
    'delete':           'Cancelación',
    'query':            'Consulta reserva',
    '-':                'Error de solicitud',
}

PROCESOS_IMPORTANTES = [
    'Activación ONT',
    'Activación Servicios',
    'Terminación',
    'Reconexión',
    'Eliminación servicio',
    'Cambio ONT',
]

CODIGOS_FALLA_KIBANA = {
    "100-4",
    "100-190",
    "100-191",
    "200-46",
    "200-2",
    "100-5",
}

CODIGO_TIMEOUT    = "100-5"
UMBRAL_TIMEOUT_MS = 30000  # 30 segundos — confirmado en Kibana

FALLAS_TECNICAS = [
    "100-5: REQUEST_TIME_OUT",
    "100-190: No se creo la ONT nueva; rollback ejecutado",
    "100-191: No se asociaron servicios a ONT nueva; rollback ejecutado",
    "200-46: Error ejecutando el comando ADD-ONU",
    "200-46: Error ejecutando el comando CFG-ONUBW",
    "200-46: Error ejecutando el comando DEL-ONU",
    "100-4: Sin respuesta del servicio externo",
    "200-2: Error inesperado",
]

COLORES_PROCESO = {
    'Activación ONT':          '#E74C3C',
    'Activación Servicios':    '#9B59B6',
    'Terminación':             '#3498DB',
    'Reconexión':              '#1ABC9C',
    'Eliminación servicio':    '#2ECC71',
    'Cambio ONT':              '#E67E22',
    'Suspensión':              '#95A5A6',
    'Estado servicio':         '#F39C12',
    'Ancho de banda':          '#16A085',
    'Reserva':                 '#1ABC9C',
    'Consulta reserva':        '#F39C12',
    'Consulta Disponibilidad': '#2ECC71',
}

COL_TRANS     = 'requestrequestdescription'
COL_CODE      = 'responseresponsefinalresponseresponsecode'
COL_TIME      = 'timestamp'
COL_REASON    = 'responseresponsefinalresponseresponsereason'
COL_OPERATOR  = 'requestrequestrelatedpartyname'
COL_TIMETAKEN = 'timetaken'


def limpiar_encabezado(df: pd.DataFrame) -> pd.DataFrame:
    nuevos = {col: re.sub(r'[^a-zA-Z0-9_]', '', col).lower() for col in df.columns}
    return df.rename(columns=nuevos)


def traducir_error(codigo, razon=None) -> str:
    codigo = str(codigo).strip()
    if codigo in ("200", "200 TODO OK", ".", "-", "OK"):
        return "200 TODO OK"
    if codigo == "500":
        if razon and str(razon).strip() and str(razon).lower() not in ['nan', 'none', '']:
            return f"500: {str(razon).strip()[:80]}"
        return "500: Error interno del servidor"
    if codigo == "100-5":  return "100-5: REQUEST_TIME_OUT"
    if codigo == "100-4":  return "100-4: Sin respuesta del servicio externo"
    if codigo == "100-2":  return "100-2: Falta parametro requerido"
    if codigo == "100-190": return "100-190: No se creo la ONT nueva; rollback ejecutado"
    if codigo == "100-191": return "100-191: No se asociaron servicios a ONT nueva; rollback ejecutado"
    if codigo == "200-2":  return "200-2: Error inesperado"
    if codigo == "200-15": return "200-15: No existe la reserva para el VNO indicado"
    if codigo == "200-38": return "200-38: El servicio no esta asociado al VNO"
    if codigo == "200-39": return "200-39: La reserva ya tiene una ONT asignada"
    if codigo == "200-40": return "200-40: Error en parametros del servicio"
    if codigo == "200-41": return "200-41: Servicio sin componente asociado"
    if codigo == "200-42": return "200-42: Parametro de servicio invalido"
    if codigo == "200-46":
        if razon and str(razon).strip() and str(razon).lower() not in ['nan', 'none', '']:
            razon_limpia = str(razon).strip()
            if "debido a" in razon_limpia:
                razon_limpia = razon_limpia.split("debido a")[0].strip()
            return f"200-46: {razon_limpia}"
        return "200-46: Error ejecutando comando OLT"
    if codigo == "200-63":  return "200-63: Reserva no activa"
    if codigo == "200-68":  return "200-68: La ONT ya existe en el inventario"
    if codigo == "200-84":  return "200-84: Error de configuracion OLT"
    if codigo == "200-88":  return "200-88: No se encontro CVLAN relacionada para la OLT"
    if codigo == "200-141": return "200-141: Error en configuracion de VLAN"
    if razon and str(razon).strip() and str(razon).lower() not in ['nan', 'none', '']:
        razon_limpia = str(razon).strip()
        if codigo in ("200-40", "200-42"):
            if "no pueden" in razon_limpia:
                razon_limpia = razon_limpia.split("no pueden")[0].strip()
        return f"{codigo}: {razon_limpia[:80]}"
    return codigo


def procesar_dataframe(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = limpiar_encabezado(df_raw.copy())

    # ── TIMESTAMP ─────────────────────────────────────────────
    if COL_TIME in df.columns:
        ts = pd.to_datetime(
            df[COL_TIME].astype(str).str.replace(' @ ', ' ', regex=False),
            errors='coerce', utc=True
        )
        df[COL_TIME] = ts.dt.tz_convert('America/Bogota').dt.tz_localize(None)
        df = df.dropna(subset=[COL_TIME])

    # ── PROCESO ───────────────────────────────────────────────
    if COL_TRANS in df.columns:
        df[COL_TRANS] = (
            df[COL_TRANS].astype(str).str.strip().str.lower()
            .map(lambda x: MAPEO.get(x, x.title() if x not in ('nan', '') else 'Desconocido'))
        )

    # ── TIMETAKEN — normalizar ────────────────────────────────
    if COL_TIMETAKEN in df.columns:
        df[COL_TIMETAKEN] = pd.to_numeric(df[COL_TIMETAKEN], errors='coerce').fillna(0)

    # ── CÓDIGO DE RESPUESTA ───────────────────────────────────
    if COL_CODE in df.columns:
        df[COL_CODE] = df[COL_CODE].astype(str).str.strip()

        def clasificar(codigo):
            codigo = str(codigo).strip()
            if codigo in ('', 'nan', 'None', 'SIN_CODIGO', '-'):
                return 'sin_codigo'
            if codigo in CODIGOS_FALLA_KIBANA:
                return 'falla'
            return 'ok'

        df['_clasificacion']   = df[COL_CODE].apply(clasificar)
        df['Es_Exito']         = df['_clasificacion'] == 'ok'
        df['Es_Exito_Tecnico'] = df['_clasificacion'] == 'ok'
        df['Sin_Codigo']       = df['_clasificacion'] == 'sin_codigo'

        # ── TIMEOUT por timeTaken > 30,000 ms ─────────────────
        # Confirmado en Kibana 29/04/2026: código 100-5 no existe.
        # Los timeouts reales son transacciones con timeTaken > 30s.
        if COL_TIMETAKEN in df.columns:
            df['Es_Timeout'] = df[COL_TIMETAKEN] > UMBRAL_TIMEOUT_MS
        else:
            df['Es_Timeout'] = df[COL_CODE].astype(str).str.strip() == CODIGO_TIMEOUT

        df[COL_CODE] = df.apply(
            lambda row: traducir_error(row[COL_CODE], row.get(COL_REASON, '')),
            axis=1
        )
        df.drop(columns=['_clasificacion'], inplace=True)

    return df


def calcular_kpis(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "total_tx": 0, "sla_global": 0.0,
            "pct_error": 0.0, "pct_timeout": 0.0,
            "total_fallas": 0, "total_timeouts": 0,
            "total_sin_codigo": 0,
            "resumen_proceso": pd.DataFrame(),
            "top_errores": pd.DataFrame(),
        }

    total_registros  = len(df)
    sin_codigo       = int(df['Sin_Codigo'].sum()) if 'Sin_Codigo' in df.columns else 0
    df_con_codigo    = df[~df['Sin_Codigo']] if 'Sin_Codigo' in df.columns else df
    total_con_codigo = len(df_con_codigo)
    total_tx         = total_con_codigo
    total_ok         = int(df_con_codigo["Es_Exito_Tecnico"].sum()) if not df_con_codigo.empty else 0
    total_fallas     = total_con_codigo - total_ok
    total_to         = int(df["Es_Timeout"].sum()) if "Es_Timeout" in df.columns else 0

    sla_global  = (total_ok / total_con_codigo * 100) if total_con_codigo > 0 else 0.0
    pct_error   = (total_fallas / total_con_codigo * 100) if total_con_codigo > 0 else 0.0
    pct_timeout = (total_to / total_con_codigo * 100) if total_con_codigo > 0 else 0.0

    resumen = (
        df_con_codigo.groupby(COL_TRANS)
        .agg(Total=('Es_Exito_Tecnico', 'size'), OK=('Es_Exito_Tecnico', 'sum'))
        .reset_index()
    )
    resumen['Fallas']    = resumen['Total'] - resumen['OK']
    resumen['SLA_pct']   = (resumen['OK'] / resumen['Total'] * 100).round(1)
    resumen['Error_pct'] = (resumen['Fallas'] / resumen['Total'] * 100).round(1)
    resumen = resumen.sort_values('Total', ascending=False)

    top_errores = pd.DataFrame()
    if not df_con_codigo.empty and 'Es_Exito_Tecnico' in df_con_codigo.columns:
        errores_df = df_con_codigo[~df_con_codigo["Es_Exito_Tecnico"]]
        if not errores_df.empty and COL_CODE in errores_df.columns:
            top_errores = errores_df[COL_CODE].value_counts().head(5).reset_index()
            top_errores.columns = ['Error', 'Cantidad']
            top_errores['Pct'] = (top_errores['Cantidad'] / total_con_codigo * 100).round(1)

    return {
        "total_tx":         total_tx,
        "total_registros":  total_registros,
        "total_con_codigo": total_con_codigo,
        "total_sin_codigo": sin_codigo,
        "sla_global":       round(sla_global, 2),
        "pct_error":        round(pct_error, 2),
        "pct_timeout":      round(pct_timeout, 2),
        "total_fallas":     total_fallas,
        "total_timeouts":   total_to,
        "resumen_proceso":  resumen,
        "top_errores":      top_errores,
    }


def evaluar_alertas(kpis: dict, umbral_sla=95.0,
                    umbral_timeout=5.0, umbral_error=10.0) -> list:
    alertas = []
    if kpis["total_tx"] == 0:
        return alertas
    if kpis["sla_global"] < umbral_sla:
        diff  = umbral_sla - kpis["sla_global"]
        nivel = "CRÍTICO" if diff >= 2 else "SERIO"
        alertas.append({
            "nivel": nivel, "titulo": "SLA de plataforma bajo umbral ANS",
            "descripcion": f"SLA actual {kpis['sla_global']:.2f}% — umbral {umbral_sla}%",
            "valor": kpis["sla_global"], "umbral": umbral_sla,
            "metrica": "SLA_GLOBAL", "timestamp": datetime.now().isoformat(),
        })
    if kpis["pct_timeout"] > umbral_timeout:
        alertas.append({
            "nivel": "CRÍTICO", "titulo": "Tasa de Timeout elevada",
            "descripcion": f"Timeouts: {kpis['pct_timeout']:.2f}% — umbral {umbral_timeout}%",
            "valor": kpis["pct_timeout"], "umbral": umbral_timeout,
            "metrica": "TIMEOUT_PCT", "timestamp": datetime.now().isoformat(),
        })
    if kpis["pct_error"] > umbral_error:
        alertas.append({
            "nivel": "SERIO", "titulo": "Errores tecnicos masivos detectados",
            "descripcion": f"Error tecnico: {kpis['pct_error']:.2f}% — umbral {umbral_error}%",
            "valor": kpis["pct_error"], "umbral": umbral_error,
            "metrica": "ERROR_MASIVO", "timestamp": datetime.now().isoformat(),
        })
    return alertas


def calcular_disponibilidad_mensual(df_mes: pd.DataFrame) -> dict:
    if df_mes.empty:
        return {"disponibilidad": 0.0, "horas_inactividad": 720.0,
                "horas_activo": 0.0, "cumple_ans": False}
    HORAS_MES = 720.0
    df_mes = df_mes.copy()
    df_mes['hora'] = df_mes[COL_TIME].dt.floor('h')
    horas_con_tx = df_mes['hora'].nunique()
    h_inicio    = df_mes[COL_TIME].min().floor('h')
    h_fin       = df_mes[COL_TIME].max().ceil('h')
    todas_horas = pd.date_range(h_inicio, h_fin, freq='h')
    horas_inactivas = len(todas_horas) - horas_con_tx
    pct_inactivo          = horas_inactivas / len(todas_horas) if len(todas_horas) > 0 else 0
    horas_inactividad_mes = pct_inactivo * HORAS_MES
    horas_activo_mes      = HORAS_MES - horas_inactividad_mes
    disponibilidad        = (horas_activo_mes / HORAS_MES) * 100
    return {
        "disponibilidad":    round(disponibilidad, 3),
        "horas_inactividad": round(horas_inactividad_mes, 2),
        "horas_activo":      round(horas_activo_mes, 2),
        "cumple_ans":        disponibilidad >= 99.9,
    }