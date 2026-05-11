"""
pages/dashboard.py
Dashboard de KPIs — Vista 3 columnas igual a Kibana (VNO+CLARO / CLARO / ETB)
Sincronización en paralelo con Elasticsearch.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import os
import time
import concurrent.futures
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIG DE PAGINA (titulo de la pestaña del navegador) ────
st.set_page_config(
    page_title="Portal NOC ATP — Dashboard KPIs",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── SIDEBAR COMPARTIDO (azul, con botones de navegacion + tunel) ───
from modules.styles import sidebar_comun
sidebar_comun(mostrar_timeouts=False)

from modules.data_processor import (
    procesar_dataframe, calcular_kpis, evaluar_alertas,
    COL_TRANS, COL_CODE, COL_TIME, COLORES_PROCESO, PROCESOS_IMPORTANTES
)
from modules.kibana_client import (
    obtener_transacciones_raw, obtener_transacciones_custom,
    obtener_total_registros, obtener_total_custom, verificar_conexion
)
from modules.notificaciones import enviar_alerta_teams

RANGOS_RAPIDOS = {
    "Últimos 15 minutos":     "now-15m",
    "Últimos 30 minutos":     "now-30m",
    "Última hora":            "now-1h",
    "Últimas 6 horas":        "now-6h",
    "Últimas 24 horas":       "now-24h",
    "Hoy":                    "today",
    "Esta semana":            "week",
    "Últimos 7 días":         "now-7d",
    "Últimos 30 días":        "now-30d",
    "Últimos 90 días":        "now-90d",
    "Último año":             "now-1y",
    "📅 Rango personalizado": "custom",
}

COLORES_MEJORADOS = {
    'Activación ONT':       '#E74C3C',
    'Activación Servicios': '#9B59B6',
    'Terminación':          '#3498DB',
    'Reconexión':           '#1ABC9C',
    'Eliminación servicio': '#2ECC71',
    'Cambio ONT':           '#F39C12',
}

CODIGOS_FALLA = {'100-4', '100-190', '100-191', '200-46', '200-2', '100-5'}


def _badge_sla(sla):
    if sla >= 99.9:
        return (
            "<span style='background:#DCFCE7;color:#166534;padding:3px 12px;"
            "border-radius:12px;font-size:12px;font-weight:700;'>"
            f"✅ {sla:.2f}% — CUMPLE META</span>"
        )
    elif sla >= 95:
        return (
            "<span style='background:#FEF3C7;color:#92400E;padding:3px 12px;"
            "border-radius:12px;font-size:12px;font-weight:700;'>"
            f"⚠️ {sla:.2f}% — POR DEBAJO META</span>"
        )
    return (
        "<span style='background:#FEE2E2;color:#991B1B;padding:3px 12px;"
        "border-radius:12px;font-size:12px;font-weight:700;'>"
        f"🔴 {sla:.2f}% — CRÍTICO</span>"
    )


def _color_sla_value(sla):
    if sla >= 99:   return "#166534"
    if sla >= 95:   return "#92400E"
    return "#991B1B"


def _bg_sla_value(sla):
    if sla >= 99:   return "#DCFCE7"
    if sla >= 95:   return "#FEF3C7"
    return "#FEE2E2"


def _cargar_operador(operador: str, rango_es: str,
                     fecha_ini_iso=None, fecha_fin_iso=None):
    try:
        if rango_es == "custom" and fecha_ini_iso and fecha_fin_iso:
            df_raw, err = obtener_transacciones_custom(operador, fecha_ini_iso, fecha_fin_iso)
        else:
            df_raw, err = obtener_transacciones_raw(operador, rango_es)

        if err or df_raw.empty:
            return operador, pd.DataFrame(), err or "Sin datos"
        df_procesado = procesar_dataframe(df_raw)
        try:
            from modules.timeout_history import guardar_timeouts
            guardar_timeouts(df_procesado, operador, rango_es)
        except Exception:
            pass
        return operador, df_procesado, None
    except Exception as e:
        return operador, pd.DataFrame(), str(e)


def _cargar_todos_paralelo(rango_es, fecha_ini_iso=None, fecha_fin_iso=None):
    resultado = {"CLARO": pd.DataFrame(), "ETB": pd.DataFrame(), "errors": {}}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(_cargar_operador, op, rango_es, fecha_ini_iso, fecha_fin_iso): op
            for op in ["CLARO", "ETB"]
        }
        for future in concurrent.futures.as_completed(futures):
            op, df, err = future.result()
            resultado[op] = df
            if err:
                resultado["errors"][op] = err
    return resultado


def _render_operador_card(label: str, dot_color: str, kpis: dict, df: pd.DataFrame):
    sla          = kpis["sla_global"]
    pct_error    = kpis["pct_error"]
    pct_timeout  = kpis["pct_timeout"]
    total_tx     = kpis["total_tx"]
    total_fallas = kpis["total_fallas"]
    total_to     = kpis["total_timeouts"]
    delta_sla    = sla - 99.9
    col_sla_color = _color_sla_value(sla)

    st.markdown(
        f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:8px;'>"
        f"<div style='width:14px;height:14px;border-radius:50%;background:{dot_color};flex-shrink:0;'></div>"
        f"<span style='font-size:16px;font-weight:600;'>{label}</span>"
        f"</div>",
        unsafe_allow_html=True
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"<div style='background:#f9f9f9;border:0.5px solid #e0e0e0;border-radius:8px;"
            f"padding:12px 10px;text-align:center;'>"
            f"<div style='font-size:11px;color:#888;margin-bottom:4px;'>📦 Total</div>"
            f"<div style='font-size:24px;font-weight:700;color:#1a1a2e;'>{total_tx:,}</div>"
            f"<div style='font-size:11px;color:#aaa;'>Transacciones</div>"
            f"</div>", unsafe_allow_html=True)
    with c2:
        delta_str = f"{'▼' if delta_sla < 0 else '▲'} {abs(delta_sla):.2f}% vs meta 99.9%"
        delta_color = "#C0392B" if delta_sla < 0 else "#1D9E75"
        st.markdown(
            f"<div style='background:#f9f9f9;border:0.5px solid #e0e0e0;border-radius:8px;"
            f"padding:12px 10px;text-align:center;'>"
            f"<div style='font-size:11px;color:#888;margin-bottom:4px;'>✅ Exitosas</div>"
            f"<div style='font-size:24px;font-weight:700;color:{col_sla_color};'>{sla:.2f}%</div>"
            f"<div style='font-size:11px;color:{delta_color};'>{delta_str}</div>"
            f"</div>", unsafe_allow_html=True)
    with c3:
        st.markdown(
            f"<div style='background:#f9f9f9;border:0.5px solid #e0e0e0;border-radius:8px;"
            f"padding:12px 10px;text-align:center;'>"
            f"<div style='font-size:11px;color:#888;margin-bottom:4px;'>❌ No Exitosas</div>"
            f"<div style='font-size:24px;font-weight:700;color:#C0392B;'>{pct_error:.2f}%</div>"
            f"<div style='font-size:11px;color:#E67E22;'>▲ {total_fallas:,} fallas</div>"
            f"</div>", unsafe_allow_html=True)
    with c4:
        to_color = "#C0392B" if pct_timeout > 0 else "#1D9E75"
        st.markdown(
            f"<div style='background:#f9f9f9;border:0.5px solid #e0e0e0;border-radius:8px;"
            f"padding:12px 10px;text-align:center;'>"
            f"<div style='font-size:11px;color:#888;margin-bottom:4px;'>⏱ Timeouts</div>"
            f"<div style='font-size:24px;font-weight:700;color:{to_color};'>{pct_timeout:.2f}%</div>"
            f"<div style='font-size:11px;color:#aaa;'>▲ {total_to:,} timeouts</div>"
            f"</div>", unsafe_allow_html=True)


def _render_detalle_proceso(kpis: dict):
    resumen = kpis.get("resumen_proceso", pd.DataFrame())
    if resumen.empty:
        st.info("Sin datos de procesos.")
        return

    def color_tasa(v):
        if v >= 99:   return 'background-color: #DCFCE7; color: #166534'
        if v >= 95:   return 'background-color: #FEF3C7; color: #92400E'
        return 'background-color: #FEE2E2; color: #7F1D1D'

    df_tabla = (
        resumen[[COL_TRANS, 'Total', 'OK', 'Fallas', 'SLA_pct', 'Error_pct']]
        .rename(columns={
            COL_TRANS:   'Proceso',
            'SLA_pct':   'Tasa de Éxito %',
            'Error_pct': 'Error %'
        })
        .copy()
    )
    df_tabla['Tasa de Éxito %'] = df_tabla['Tasa de Éxito %'].round(2)
    df_tabla['Error %']         = df_tabla['Error %'].round(2)

    st.dataframe(
        df_tabla.style
            .map(color_tasa, subset=['Tasa de Éxito %'])
            .format({'Tasa de Éxito %': '{:.2f}%', 'Error %': '{:.2f}%'}),
        use_container_width=True,
        hide_index=True,
    )


def render():
    st.markdown("## 📊 Dashboard de KPIs — Tiempo Real")

    c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
    with c1:
        vista = st.selectbox(
            "Vista",
            ["🔵 Todas (3 columnas Kibana)", "🔴 Solo CLARO", "🔵 Solo ETB"],
            key="db_vista"
        )
    with c2:
        rango_label = st.selectbox(
            "Ventana de tiempo",
            list(RANGOS_RAPIDOS.keys()),
            index=7,
            key="db_rango"
        )
    with c3:
        fuente = st.radio("Fuente", ["🔌 En vivo", "📂 CSV"],
                          key="db_fuente", horizontal=True)
    with c4:
        auto_refresh = st.checkbox("Auto-refresh 5min", value=False, key="db_auto")

    rango_es      = RANGOS_RAPIDOS[rango_label]
    fecha_ini_iso = None
    fecha_fin_iso = None

    if rango_es == "custom":
        st.markdown("#### 📅 Selecciona el rango de fechas")
        cf1, cf2, cf3, cf4 = st.columns(4)
        with cf1:
            fecha_ini = st.date_input("Fecha inicio",
                                      value=date.today() - timedelta(days=1),
                                      key="db_fecha_ini")
        with cf2:
            hora_ini = st.time_input("Hora inicio",
                                     value=datetime.strptime("00:00", "%H:%M").time(),
                                     key="db_hora_ini")
        with cf3:
            fecha_fin = st.date_input("Fecha fin", value=date.today(), key="db_fecha_fin")
        with cf4:
            hora_fin = st.time_input("Hora fin",
                                     value=datetime.strptime("23:59", "%H:%M").time(),
                                     key="db_hora_fin")

        fecha_ini_iso = f"{fecha_ini}T{hora_ini.strftime('%H:%M:%S')}.000Z"
        fecha_fin_iso = f"{fecha_fin}T{hora_fin.strftime('%H:%M:%S')}.000Z"

    st.markdown("---")

    vista_todos  = "3 columnas" in vista
    vista_claro  = "CLARO" in vista
    vista_etb    = "ETB" in vista

    datos  = {}
    errors = {}

    if "🔌" in fuente:
        col_btn, col_estado = st.columns([1, 4])
        with col_btn:
            btn_sync = st.button("🔄 Sincronizar ahora", type="primary", key="db_sync")
        with col_estado:
            if "last_sync" in st.session_state:
                st.caption(f"Última sincronización: {st.session_state.last_sync}")

        rango_cache = st.session_state.get("db_rango_cache", "")
        vista_cache = st.session_state.get("db_vista_cache", "")
        cambio = (rango_cache != rango_es) or (vista_cache != vista)
        cargar = btn_sync or ("db_datos" not in st.session_state) or auto_refresh or cambio

        if cargar:
            cx = verificar_conexion()
            if not cx["ok"]:
                st.error(f"❌ Sin conexión: {cx['msg']}")
                st.info("💡 Verifica que el túnel SSH esté activo.")
                return

            if vista_todos:
                ops_a_cargar = ["CLARO", "ETB"]
            elif vista_claro:
                ops_a_cargar = ["CLARO"]
            else:
                ops_a_cargar = ["ETB"]

            totales_info = {}
            for op in ops_a_cargar:
                if rango_es == "custom" and fecha_ini_iso and fecha_fin_iso:
                    info = obtener_total_custom(op, fecha_ini_iso, fecha_fin_iso)
                else:
                    info = obtener_total_registros(op, rango_es)
                totales_info[op] = info

            for op, info in totales_info.items():
                if info.get("ok") and info.get("total", 0) > 0:
                    st.info(f"📊 **{op}**: Elasticsearch tiene **{info['total']:,} registros** — descargando en páginas de 5,000...")

            with st.spinner(f"Sincronizando {'CLARO + ETB' if vista_todos else ops_a_cargar[0]} — {rango_label}..."):
                if vista_todos:
                    resultado = _cargar_todos_paralelo(rango_es, fecha_ini_iso, fecha_fin_iso)
                    datos  = {op: resultado[op] for op in ["CLARO", "ETB"]}
                    errors = resultado.get("errors", {})
                else:
                    op = ops_a_cargar[0]
                    _, df_op, err = _cargar_operador(op, rango_es, fecha_ini_iso, fecha_fin_iso)
                    datos[op]  = df_op
                    if err: errors[op] = err

            # ── FIX: usar if/else en lugar de ternario bare ──────
            for op in ops_a_cargar:
                df_op = datos.get(op, pd.DataFrame())
                info  = totales_info.get(op, {})
                if not df_op.empty and info.get("ok") and info.get("total", 0) > 0:
                    pct = len(df_op) / info["total"] * 100
                    txt = f"✅ **{op}**: {len(df_op):,} de {info['total']:,} registros ({pct:.1f}%)"
                    if pct >= 99:
                        st.success(txt)
                    else:
                        st.warning(txt)
                elif op in errors:
                    st.warning(f"⚠️ **{op}**: {errors[op]}")

            st.session_state.db_datos       = datos
            st.session_state.db_vista_cache = vista
            st.session_state.db_rango_cache = rango_es
            st.session_state.last_sync      = datetime.now().strftime("%H:%M:%S")

        elif "db_datos" in st.session_state:
            datos = st.session_state.db_datos

    else:
        st.info("📂 Modo CSV: sube un archivo por operador.")
        c_csv1, c_csv2 = st.columns(2)
        with c_csv1:
            arc_claro = st.file_uploader("CSV CLARO", type=["csv"], key="db_csv_claro")
            if arc_claro:
                datos["CLARO"] = procesar_dataframe(pd.read_csv(arc_claro, encoding='latin-1'))
        with c_csv2:
            arc_etb = st.file_uploader("CSV ETB", type=["csv"], key="db_csv_etb")
            if arc_etb:
                datos["ETB"] = procesar_dataframe(pd.read_csv(arc_etb, encoding='latin-1'))

        if datos:
            st.session_state.db_datos = datos
        elif "db_datos" in st.session_state:
            datos = st.session_state.db_datos

    if not datos or all(df.empty for df in datos.values()):
        st.info("👆 Selecciona la fuente de datos y sincroniza para ver el dashboard.")
        return

    kpis_por_op = {}
    for op, df_op in datos.items():
        if not df_op.empty:
            kpis_por_op[op] = calcular_kpis(df_op)

    df_global = pd.concat([df for df in datos.values() if not df.empty], ignore_index=True)
    kpis_global = calcular_kpis(df_global) if not df_global.empty else {}

    periodo_str = ""
    if not df_global.empty and COL_TIME in df_global.columns:
        periodo_str = (
            f"{df_global[COL_TIME].min().strftime('%d/%m/%Y %H:%M')} — "
            f"{df_global[COL_TIME].max().strftime('%d/%m/%Y %H:%M')}"
        )

    sla_global = kpis_global.get("sla_global", 0)
    umbral_sla = float(os.getenv("UMBRAL_SLA_CRITICO", 95.0))
    umbral_to  = float(os.getenv("UMBRAL_TIMEOUT_PCT", 5.0))
    umbral_err = float(os.getenv("UMBRAL_ERROR_MASIVO_PCT", 10.0))
    alertas    = evaluar_alertas(kpis_global, umbral_sla, umbral_to, umbral_err)

    if sla_global >= 99.9:
        st.success(f"✅ OPERACIÓN NORMAL | Fuente: Elasticsearch (en vivo) | {periodo_str}")
    elif sla_global >= 95:
        st.warning(f"⚠️ ATENCIÓN — Tasa de éxito por debajo de la meta | Fuente: Elasticsearch (en vivo)")
    else:
        st.error(f"🔴 ALERTA CRÍTICA — Tasa de éxito {sla_global:.2f}% — Activar protocolo de escalamiento")

    st.markdown(f"Tasa de éxito actual: {_badge_sla(sla_global)}", unsafe_allow_html=True)
    if periodo_str:
        op_label = "CLARO + ETB" if vista_todos else ("CLARO" if vista_claro else "ETB")
        st.markdown(f"**Período:** {periodo_str} &nbsp;|&nbsp; **Operador:** {op_label}")

    for a in alertas:
        css = "alerta-critico" if a["nivel"] == "CRÍTICO" else "alerta-serio"
        st.markdown(
            f"<div class='{css}'>⚠️ <strong>[{a['nivel']}]</strong> "
            f"{a['titulo']} — {a['descripcion']}</div>",
            unsafe_allow_html=True
        )

    st.markdown("---")

    with st.expander("🔍 Diagnóstico de datos (comparar con Kibana)", expanded=False):
        for op_d, k_d in kpis_por_op.items():
            df_d = datos.get(op_d, pd.DataFrame())
            total_reg    = k_d.get('total_con_codigo', 0)
            total_fallas = k_d.get('total_fallas', 0)
            total_ok     = total_reg - total_fallas

            st.markdown(f"**{op_d}**")
            cols_d = st.columns(5)
            cols_d[0].metric("Registros descargados",  f"{k_d.get('total_registros', '?'):,}")
            cols_d[1].metric("Con código respuesta",   f"{total_reg:,}")
            cols_d[2].metric("Sin código (excluidos)", f"{k_d.get('total_sin_codigo', 0):,}")
            cols_d[3].metric("OK", f"{total_ok:,}",
                             delta=f"{total_ok/total_reg*100:.2f}% del total" if total_reg > 0 else "")
            cols_d[4].metric("Fallas", f"{total_fallas:,}",
                             delta=f"{total_fallas/total_reg*100:.2f}% del total" if total_reg > 0 else "",
                             delta_color="inverse")

            if not df_d.empty and COL_CODE in df_d.columns:
                st.caption(f"Top códigos de respuesta en {op_d}:")
                top_codes = df_d[COL_CODE].value_counts().head(10).reset_index()
                top_codes.columns = ['Código', 'Cantidad']
                top_codes['% vs Total'] = (top_codes['Cantidad'] / total_reg * 100).round(2)
                top_codes['% vs OK']    = top_codes.apply(
                    lambda r: round(r['Cantidad'] / total_ok * 100, 2) if total_ok > 0 else 0, axis=1)
                top_codes['¿Es Falla?'] = top_codes['Código'].apply(
                    lambda x: '❌ SÍ' if any(c in str(x) for c in CODIGOS_FALLA) else '✅ NO')
                top_codes['% vs Fallas'] = top_codes.apply(
                    lambda r: round(r['Cantidad'] / total_fallas * 100, 2)
                    if (total_fallas > 0 and any(c in str(r['Código']) for c in CODIGOS_FALLA))
                    else 'N/A', axis=1)

                def color_fila(row):
                    if row['¿Es Falla?'] == '❌ SÍ':
                        return ['background-color:#FEE2E2'] * len(row)
                    return [''] * len(row)

                def color_es_falla(val):
                    if val == '❌ SÍ': return 'color:#991B1B;font-weight:700'
                    return 'color:#166534;font-weight:700'

                st.dataframe(
                    top_codes[['Código', 'Cantidad', '% vs Total', '% vs OK', '% vs Fallas', '¿Es Falla?']]
                    .style
                    .apply(color_fila, axis=1)
                    .map(color_es_falla, subset=['¿Es Falla?'])
                    .format({
                        'Cantidad':    '{:,}',
                        '% vs Total':  '{:.2f}%',
                        '% vs OK':     '{:.2f}%',
                        '% vs Fallas': lambda x: f'{x:.2f}%' if isinstance(x, float) else x,
                    }),
                    hide_index=True, use_container_width=True
                )

                st.markdown("**🔍 Verificación vs cuadros superiores:**")
                v1, v2, v3, v4 = st.columns(4)
                with v1:
                    st.markdown(
                        f"<div style='background:#f0f4ff;border-radius:8px;padding:12px;text-align:center;'>"
                        f"<div style='font-size:10px;color:#3C3489;font-weight:600;'>TOTAL REGISTROS</div>"
                        f"<div style='font-size:22px;font-weight:700;color:#3C3489;'>{total_reg:,}</div>"
                        f"<div style='font-size:10px;color:#888;'>= cuadros 1 y 2</div>"
                        f"</div>", unsafe_allow_html=True)
                with v2:
                    st.markdown(
                        f"<div style='background:#DCFCE7;border-radius:8px;padding:12px;text-align:center;'>"
                        f"<div style='font-size:10px;color:#166534;font-weight:600;'>OK</div>"
                        f"<div style='font-size:22px;font-weight:700;color:#166534;'>{total_ok:,}</div>"
                        f"<div style='font-size:10px;color:#888;'>{total_ok/total_reg*100:.2f}% · cuadro 4</div>"
                        f"</div>", unsafe_allow_html=True)
                with v3:
                    st.markdown(
                        f"<div style='background:#FEE2E2;border-radius:8px;padding:12px;text-align:center;'>"
                        f"<div style='font-size:10px;color:#991B1B;font-weight:600;'>FALLAS</div>"
                        f"<div style='font-size:22px;font-weight:700;color:#991B1B;'>{total_fallas:,}</div>"
                        f"<div style='font-size:10px;color:#888;'>{total_fallas/total_reg*100:.2f}% · cuadro 5</div>"
                        f"</div>", unsafe_allow_html=True)
                with v4:
                    meta_ok    = total_reg * 0.999
                    diferencia = total_ok - meta_ok
                    color_v4   = '#166534' if diferencia >= 0 else '#991B1B'
                    bg_v4      = '#DCFCE7' if diferencia >= 0 else '#FEE2E2'
                    st.markdown(
                        f"<div style='background:{bg_v4};border-radius:8px;padding:12px;text-align:center;'>"
                        f"<div style='font-size:10px;color:{color_v4};font-weight:600;'>VS META 99.9%</div>"
                        f"<div style='font-size:22px;font-weight:700;color:{color_v4};'>{diferencia:,.0f}</div>"
                        f"<div style='font-size:10px;color:#888;'>{'✅ dentro' if diferencia >= 0 else '❌ faltan'} transacciones</div>"
                        f"</div>", unsafe_allow_html=True)

                st.caption(
                    f"📌 **Lectura:** "
                    f"**% vs Total** = cantidad / {total_reg:,} registros totales. "
                    f"**% vs OK** = cantidad / {total_ok:,} exitosos. "
                    f"**% vs Fallas** = cantidad / {total_fallas:,} fallas — solo aplica a códigos ❌ SÍ."
                )
            st.markdown("---")

    if vista_todos:
        df_claro = datos.get("CLARO", pd.DataFrame())
        df_etb   = datos.get("ETB", pd.DataFrame())
        k_claro  = kpis_por_op.get("CLARO", {})
        k_etb    = kpis_por_op.get("ETB", {})

        col_vno, col_claro, col_etb = st.columns(3)
        with col_vno:
            st.markdown(
                "<div style='background:white;border:0.5px solid #e0e0e0;border-radius:8px;"
                "padding:14px 16px 8px;margin-bottom:4px;'>"
                "<div style='display:flex;align-items:center;gap:10px;margin-bottom:10px;"
                "padding-bottom:10px;border-bottom:0.5px solid #eee;'>"
                "<div style='width:14px;height:14px;border-radius:50%;background:#888;'></div>"
                "<span style='font-size:15px;font-weight:600;'>Transacciones (CLARO, ETB)</span>"
                "</div>", unsafe_allow_html=True)
            if kpis_global:
                _mini_kpis(kpis_global)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_claro:
            st.markdown(
                "<div style='background:white;border:0.5px solid #e0e0e0;border-radius:8px;"
                "padding:14px 16px 8px;margin-bottom:4px;'>"
                "<div style='display:flex;align-items:center;gap:10px;margin-bottom:10px;"
                "padding-bottom:10px;border-bottom:0.5px solid #eee;'>"
                "<div style='width:14px;height:14px;border-radius:50%;background:#e5211d;'></div>"
                "<span style='font-size:15px;font-weight:600;'>CLARO</span>"
                "</div>", unsafe_allow_html=True)
            if k_claro:
                _mini_kpis(k_claro)
            elif "CLARO" in errors:
                st.warning(f"Error CLARO: {errors['CLARO']}")
            st.markdown("</div>", unsafe_allow_html=True)

        with col_etb:
            st.markdown(
                "<div style='background:white;border:0.5px solid #e0e0e0;border-radius:8px;"
                "padding:14px 16px 8px;margin-bottom:4px;'>"
                "<div style='display:flex;align-items:center;gap:10px;margin-bottom:10px;"
                "padding-bottom:10px;border-bottom:0.5px solid #eee;'>"
                "<div style='width:14px;height:14px;border-radius:50%;background:#1a6ab5;'></div>"
                "<span style='font-size:15px;font-weight:600;'>ETB</span>"
                "</div>", unsafe_allow_html=True)
            if k_etb:
                _mini_kpis(k_etb)
            elif "ETB" in errors:
                st.warning(f"Error ETB: {errors['ETB']}")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")

        tab_global, tab_claro, tab_etb = st.tabs([
            "📊 Global (CLARO + ETB)",
            "🔴 Detalle CLARO",
            "🔵 Detalle ETB",
        ])

        with tab_global:
            _render_tabs_detalle(df_global, kpis_global, "Global")
        with tab_claro:
            if not df_claro.empty and k_claro:
                _render_tabs_detalle(df_claro, k_claro, "CLARO")
            else:
                st.info("Sin datos de CLARO.")
        with tab_etb:
            if not df_etb.empty and k_etb:
                _render_tabs_detalle(df_etb, k_etb, "ETB")
            else:
                st.info("Sin datos de ETB.")

    else:
        op_unico = "CLARO" if vista_claro else "ETB"
        df_op    = datos.get(op_unico, pd.DataFrame())
        k_op     = kpis_por_op.get(op_unico, kpis_global)
        dot_col  = "#e5211d" if op_unico == "CLARO" else "#1a6ab5"

        if not df_op.empty:
            _render_operador_card(op_unico, dot_col, k_op, df_op)
            st.markdown("---")
            _render_tabs_detalle(df_op, k_op, op_unico)
        else:
            st.warning(f"Sin datos para {op_unico}.")


def _mini_kpis(kpis: dict):
    sla         = kpis.get("sla_global", 0)
    pct_error   = kpis.get("pct_error", 0)
    pct_timeout = kpis.get("pct_timeout", 0)
    total_tx    = kpis.get("total_tx", 0)
    total_f     = kpis.get("total_fallas", 0)
    total_to    = kpis.get("total_timeouts", 0)
    delta_sla   = sla - 99.9
    delta_color = "#C0392B" if delta_sla < 0 else "#1D9E75"
    sla_color   = _color_sla_value(sla)
    to_color    = "#C0392B" if pct_timeout > 0 else "#888"

    st.markdown(
        f"""
        <div style='display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:8px;'>
          <div style='grid-column:span 2;background:#f5f5f5;border-radius:6px;padding:10px 12px;text-align:center;'>
            <div style='font-size:10px;color:#888;'>📦 Total</div>
            <div style='font-size:26px;font-weight:700;color:#1a1a2e;'>{total_tx:,}</div>
            <div style='font-size:10px;color:#aaa;'>Transacciones</div>
          </div>
          <div style='background:#f5f5f5;border-radius:6px;padding:10px 8px;text-align:center;'>
            <div style='font-size:10px;color:#888;'>✅ Exitosas</div>
            <div style='font-size:20px;font-weight:700;color:{sla_color};'>{sla:.2f}%</div>
            <div style='font-size:10px;color:{delta_color};'>{'▼' if delta_sla < 0 else '▲'} {abs(delta_sla):.2f}% vs meta</div>
          </div>
          <div style='background:#f5f5f5;border-radius:6px;padding:10px 8px;text-align:center;'>
            <div style='font-size:10px;color:#888;'>❌ No Exitosas</div>
            <div style='font-size:20px;font-weight:700;color:#C0392B;'>{pct_error:.2f}%</div>
            <div style='font-size:10px;color:#E67E22;'>▲ {total_f:,} fallas</div>
          </div>
          <div style='grid-column:span 2;background:#f5f5f5;border-radius:6px;padding:8px 12px;text-align:center;'>
            <div style='font-size:10px;color:#888;'>⏱ Timeouts</div>
            <div style='font-size:18px;font-weight:700;color:{to_color};'>{pct_timeout:.2f}%</div>
            <div style='font-size:10px;color:#aaa;'>▲ {total_to:,} timeouts</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def _render_tabs_detalle(df: pd.DataFrame, kpis: dict, label: str):
    key_suffix = label.lower().replace(" ", "_").replace("+", "").replace("(", "").replace(")", "")
    tab1, tab2, tab3 = st.tabs([
        "📊 Composición & Tasa de Éxito",
        "📈 Evolución temporal",
        "📋 Detalle por proceso",
    ])
    with tab1:
        _render_composicion(df, kpis, key_suffix)
    with tab2:
        _render_evolucion(df, label, key_suffix)
    with tab3:
        _render_detalle_proceso(kpis)
        _render_top_errores(kpis, key_suffix)


def _render_composicion(df: pd.DataFrame, kpis: dict, key_suffix: str = ""):
    total_tx     = kpis.get("total_tx", 0)
    total_fallas = kpis.get("total_fallas", 0)
    total_ok     = total_tx - total_fallas
    sla_global   = kpis.get("sla_global", 0)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        color = "#166534" if sla_global >= 99.9 else ("#92400E" if sla_global >= 95 else "#991B1B")
        bg    = "#DCFCE7" if sla_global >= 99.9 else ("#FEF3C7" if sla_global >= 95 else "#FEE2E2")
        st.markdown(
            f"<div style='background:{bg};border-radius:12px;padding:18px;text-align:center;'>"
            f"<div style='font-size:11px;color:{color};font-weight:700;letter-spacing:1px;'>TASA DE ÉXITO</div>"
            f"<div style='font-size:38px;font-weight:800;color:{color};line-height:1.1;'>{sla_global:.2f}%</div>"
            f"<div style='font-size:11px;color:{color};opacity:0.8;'>Meta contractual: 99.9%</div>"
            f"</div>", unsafe_allow_html=True)
    with m2:
        st.markdown(
            f"<div style='background:#f0f4ff;border-radius:12px;padding:18px;text-align:center;'>"
            f"<div style='font-size:11px;color:#3C3489;font-weight:700;letter-spacing:1px;'>TOTAL TX</div>"
            f"<div style='font-size:38px;font-weight:800;color:#1a1a2e;line-height:1.1;'>{total_tx:,}</div>"
            f"<div style='font-size:11px;color:#888;'>transacciones totales</div>"
            f"</div>", unsafe_allow_html=True)
    with m3:
        st.markdown(
            f"<div style='background:#DCFCE7;border-radius:12px;padding:18px;text-align:center;'>"
            f"<div style='font-size:11px;color:#166534;font-weight:700;letter-spacing:1px;'>EXITOSAS</div>"
            f"<div style='font-size:38px;font-weight:800;color:#166534;line-height:1.1;'>{total_ok:,}</div>"
            f"<div style='font-size:11px;color:#166534;opacity:0.8;'>{total_ok/total_tx*100:.2f}% del total</div>"
            f"</div>", unsafe_allow_html=True)
    with m4:
        st.markdown(
            f"<div style='background:#FEE2E2;border-radius:12px;padding:18px;text-align:center;'>"
            f"<div style='font-size:11px;color:#991B1B;font-weight:700;letter-spacing:1px;'>FALLAS TÉCNICAS</div>"
            f"<div style='font-size:38px;font-weight:800;color:#991B1B;line-height:1.1;'>{total_fallas:,}</div>"
            f"<div style='font-size:11px;color:#991B1B;opacity:0.8;'>{total_fallas/total_tx*100:.2f}% del total</div>"
            f"</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin:24px 0 8px;'></div>", unsafe_allow_html=True)

    col_bar, col_donut = st.columns([1.6, 1])

    with col_bar:
        resumen = kpis.get("resumen_proceso", pd.DataFrame())
        if not resumen.empty:
            df_bar = resumen.sort_values('SLA_pct', ascending=True).copy()
            df_bar['SLA_pct'] = df_bar['SLA_pct'].round(1)
            colors = []
            for v in df_bar['SLA_pct']:
                if v < 95:   colors.append('#C0392B')
                elif v < 99: colors.append('#E67E22')
                else:        colors.append('#1D9E75')
            altura = max(420, len(df_bar) * 40)
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=[100] * len(df_bar), y=df_bar[COL_TRANS],
                orientation='h', marker_color='#f0f2f5',
                showlegend=False, hoverinfo='skip', width=0.65,
            ))
            fig.add_trace(go.Bar(
                x=df_bar['SLA_pct'], y=df_bar[COL_TRANS],
                orientation='h',
                marker=dict(color=colors, line=dict(color='white', width=0.5)),
                text=[f"  {v:.1f}%" for v in df_bar['SLA_pct']],
                textposition='outside',
                textfont=dict(size=12, color='#333', family='monospace'),
                hovertemplate='<b>%{y}</b><br>Tasa de éxito: <b>%{x:.1f}%</b><extra></extra>',
                width=0.65,
            ))
            fig.add_vline(x=99.9, line_color="#3C3489", line_width=2.5, line_dash="solid")
            fig.add_annotation(
                x=99.9, y=1.04, xref="x", yref="paper",
                text="<b>Meta 99.9%</b>", showarrow=False,
                font=dict(color="#3C3489", size=11),
                bgcolor="white", bordercolor="#3C3489", borderwidth=1.5, borderpad=5,
            )
            fig.add_vline(x=95, line_color="#C0392B", line_width=1.5, line_dash="dot", opacity=0.5)
            fig.add_annotation(
                x=95, y=0, xref="x", yref="paper",
                text="95%", showarrow=False,
                font=dict(color="#C0392B", size=10), yanchor="bottom",
            )
            fig.update_layout(
                title=dict(text="<b>Tasa de éxito por proceso</b> vs meta contractual",
                           font=dict(size=14, color='#1a1a2e'), x=0, pad=dict(b=10)),
                barmode='overlay',
                xaxis=dict(
                    range=[0, 110],
                    title=dict(text="Tasa de Éxito (%)", font=dict(size=12)),
                    showgrid=True, gridcolor='#ececec', gridwidth=1, zeroline=False,
                    tickfont=dict(size=11),
                    tickvals=[0, 25, 50, 75, 95, 99.9, 100],
                    ticktext=['0%', '25%', '50%', '75%', '95%', '99.9%', '100%'],
                ),
                yaxis=dict(tickfont=dict(size=11), automargin=True, gridcolor='#f8f8f8'),
                height=altura, margin=dict(l=10, r=90, t=60, b=50),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='white', showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True, key=f"chart_bar_sla_{key_suffix}")
            st.markdown(
                "<div style='display:flex;gap:24px;margin-top:-8px;padding-left:8px;flex-wrap:wrap;'>"
                "<span style='font-size:12px;color:#1D9E75;font-weight:600;'>● ≥ 99% Cumple meta</span>"
                "<span style='font-size:12px;color:#E67E22;font-weight:600;'>● 95–99% Requiere atención</span>"
                "<span style='font-size:12px;color:#C0392B;font-weight:600;'>● < 95% Crítico</span>"
                "<span style='font-size:12px;color:#3C3489;font-weight:600;'>— Meta contractual 99.9%</span>"
                "</div>", unsafe_allow_html=True)

    with col_donut:
        otros = max(0, total_fallas - kpis.get("total_timeouts", 0))
        labels, values, colors2 = [], [], []
        if total_ok > 0:
            labels.append("Exitosas");      values.append(total_ok);               colors2.append('#1D9E75')
        if kpis.get("total_timeouts", 0) > 0:
            labels.append("Timeout");       values.append(kpis["total_timeouts"]); colors2.append('#C0392B')
        if otros > 0:
            labels.append("Error Técnico"); values.append(otros);                  colors2.append('#E67E22')
        if values:
            fig2 = go.Figure(go.Pie(
                labels=labels, values=values,
                marker=dict(colors=colors2, line=dict(color='white', width=4)),
                hole=0.65, textinfo='percent',
                textfont=dict(size=13, color='white', family='sans-serif'),
                hovertemplate='<b>%{label}</b><br>%{value:,} transacciones<br>%{percent}<extra></extra>',
                pull=[0.04 if l in ("Error Técnico", "Timeout") else 0 for l in labels],
                sort=False,
            ))
            fig2.add_annotation(
                text=f"<b>{sla_global:.1f}%</b><br>exitosas",
                x=0.5, y=0.5, font=dict(size=18, color='#1a1a2e'),
                showarrow=False, align='center',
            )
            fig2.update_layout(
                title=dict(text="<b>Composición</b> de transacciones",
                           font=dict(size=14, color='#1a1a2e'), x=0),
                height=altura, margin=dict(l=10, r=10, t=60, b=20),
                paper_bgcolor='rgba(0,0,0,0)',
                legend=dict(orientation='v', yanchor='middle', y=0.5,
                            xanchor='left', x=1.02, font=dict(size=12),
                            bgcolor='rgba(0,0,0,0)'),
            )
            st.plotly_chart(fig2, use_container_width=True, key=f"chart_donut_{key_suffix}")


def _render_evolucion(df: pd.DataFrame, label: str, key_suffix: str = ""):
    df_imp = df[df[COL_TRANS].isin(PROCESOS_IMPORTANTES)].copy()
    if df_imp.empty:
        st.info("No hay datos de procesos críticos en el período seleccionado.")
        return

    dias      = (df_imp[COL_TIME].max() - df_imp[COL_TIME].min()).days
    intervalo = '5min' if dias <= 1 else ('30min' if dias <= 7 else '1h')
    df_imp['Intervalo'] = df_imp[COL_TIME].dt.floor(intervalo)
    df_t = df_imp.groupby(['Intervalo', COL_TRANS]).size().reset_index(name='Count')

    procesos_disponibles = [p for p in PROCESOS_IMPORTANTES if p in df_t[COL_TRANS].unique()]

    col_sel, col_modo = st.columns([3, 1])
    with col_sel:
        seleccion = st.multiselect(
            "Procesos a visualizar",
            options=procesos_disponibles,
            default=procesos_disponibles,
            key=f"evol_sel_{key_suffix}"
        )
    with col_modo:
        modo = st.radio(
            "Modo",
            ["📐 Separado", "📈 Combinado"],
            key=f"evol_modo_{key_suffix}",
            horizontal=False
        )

    if not seleccion:
        st.info("Selecciona al menos un proceso.")
        return

    df_plot = df_t[df_t[COL_TRANS].isin(seleccion)]

    if "Separado" in modo:
        n     = len(seleccion)
        ncols = 2 if n > 1 else 1
        nrows = (n + 1) // 2

        fig = make_subplots(
            rows=nrows, cols=ncols,
            subplot_titles=[f"<b>{p}</b>" for p in seleccion],
            vertical_spacing=0.14,
            horizontal_spacing=0.08,
        )

        for idx, proc in enumerate(seleccion):
            row = idx // ncols + 1
            col = idx % ncols + 1
            d   = df_plot[df_plot[COL_TRANS] == proc].sort_values('Intervalo')
            if d.empty:
                continue
            color = COLORES_MEJORADOS.get(proc, '#95A5A6')
            pico  = d['Count'].max()
            media = d['Count'].mean()

            fig.add_trace(go.Scatter(
                x=d['Intervalo'], y=d['Count'],
                name=proc, mode='lines',
                fill='tozeroy',
                line=dict(color=color, width=0),
                fillcolor=color, opacity=0.12,
                showlegend=False, hoverinfo='skip',
            ), row=row, col=col)

            fig.add_trace(go.Scatter(
                x=d['Intervalo'], y=d['Count'],
                name=proc, mode='lines+markers',
                line=dict(color=color, width=2, shape='spline', smoothing=0.6),
                marker=dict(
                    size=[9 if v == pico else 3 for v in d['Count']],
                    color=color,
                    line=dict(color='white', width=1.5),
                    opacity=[1 if v == pico else 0.5 for v in d['Count']],
                ),
                showlegend=False,
                hovertemplate=(
                    f'<b>{proc}</b><br>'
                    '%{x|%d %b %H:%M}<br>'
                    'Transacciones: <b>%{y}</b><extra></extra>'
                ),
            ), row=row, col=col)

            fig.add_hline(
                y=media, line_dash="dot", line_color=color,
                line_width=1.2, opacity=0.5, row=row, col=col,
                annotation_text=f"  prom {media:.0f}",
                annotation_font_size=10, annotation_font_color=color,
                annotation_position="right",
            )

            hora_pico = d.loc[d['Count'].idxmax(), 'Intervalo']
            fig.add_annotation(
                x=hora_pico, y=pico,
                text=f"<b>↑ {pico}</b>",
                showarrow=True, arrowhead=2, arrowsize=1,
                arrowcolor=color, arrowwidth=1.5,
                ax=0, ay=-30,
                font=dict(size=10, color=color),
                bgcolor='white', bordercolor=color,
                borderwidth=1, borderpad=3,
                row=row, col=col,
            )

        altura_total = max(320, nrows * 230)
        fig.update_layout(
            height=altura_total,
            margin=dict(l=20, r=70, t=50, b=30),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='white',
            showlegend=False,
            title=dict(
                text=f"<b>Evolución temporal</b> — {label} · intervalo {intervalo}",
                font=dict(size=14, color='#1a1a2e'), x=0,
            ),
            font=dict(family='sans-serif', size=11, color='#555'),
        )
        fig.update_xaxes(
            showgrid=True, gridcolor='#f5f5f5',
            tickformat='%d %b\n%H:%M', tickfont=dict(size=10),
            zeroline=False,
        )
        fig.update_yaxes(
            showgrid=True, gridcolor='#f5f5f5',
            rangemode='tozero', tickfont=dict(size=10),
            zeroline=True, zerolinecolor='#eee',
        )

        for i, ann in enumerate(fig.layout.annotations):
            if i < len(seleccion):
                proc  = seleccion[i]
                color = COLORES_MEJORADOS.get(proc, '#95A5A6')
                ann.font.color = color
                ann.font.size  = 13

        st.plotly_chart(fig, use_container_width=True, key=f"chart_sub_{key_suffix}")

    else:
        fig = go.Figure()
        for proc in seleccion:
            d     = df_plot[df_plot[COL_TRANS] == proc].sort_values('Intervalo')
            if d.empty:
                continue
            color = COLORES_MEJORADOS.get(proc, '#95A5A6')
            pico  = d['Count'].max()

            fig.add_trace(go.Scatter(
                x=d['Intervalo'], y=d['Count'],
                name=proc,
                mode='lines+markers',
                line=dict(color=color, width=2.5, shape='spline', smoothing=0.6),
                marker=dict(
                    size=[8 if v == pico else 4 for v in d['Count']],
                    color=color,
                    line=dict(color='white', width=1.5),
                ),
                hovertemplate=(
                    f'<b style="color:{color}">{proc}</b><br>'
                    '%{x|%d %b %H:%M}<br>'
                    'Transacciones: <b>%{y}</b><extra></extra>'
                ),
            ))

        fig.update_layout(
            title=dict(
                text=f"<b>Evolución temporal</b> — {label}"
                     f"<br><span style='font-size:12px;color:#888;font-weight:400;'>Intervalo: {intervalo} · Hora Colombia</span>",
                font=dict(size=14, color='#1a1a2e'), x=0,
            ),
            xaxis=dict(
                showgrid=True, gridcolor='#f0f2f5',
                tickformat='%d %b\n%H:%M', tickfont=dict(size=11),
                zeroline=False,
            ),
            yaxis=dict(
                title="Transacciones",
                showgrid=True, gridcolor='#f0f2f5',
                rangemode='tozero',
            ),
            height=500,
            margin=dict(l=20, r=20, t=70, b=120),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='white',
            legend=dict(
                orientation='h',
                yanchor='top',
                y=-0.20,
                xanchor='center',
                x=0.5,
                bgcolor='rgba(255,255,255,0.95)',
                bordercolor='#e8e8e8',
                borderwidth=1,
                font=dict(size=12),
                itemsizing='constant',
                tracegroupgap=10,
            ),
            hovermode='x unified',
            hoverlabel=dict(
                bgcolor='white',
                bordercolor='#ddd',
                font=dict(size=12),
            ),
        )
        st.plotly_chart(fig, use_container_width=True, key=f"chart_timeline_{key_suffix}")

    st.markdown(
        "<div style='font-size:13px;font-weight:700;color:#333;"
        "margin:20px 0 12px;letter-spacing:0.3px;'>📊 Resumen del período</div>",
        unsafe_allow_html=True
    )

    cols_res = st.columns(len(seleccion))
    for i, proc in enumerate(seleccion):
        d = df_t[df_t[COL_TRANS] == proc]
        if not d.empty:
            total     = int(d['Count'].sum())
            pico      = int(d['Count'].max())
            promedio  = round(d['Count'].mean(), 1)
            color     = COLORES_MEJORADOS.get(proc, '#95A5A6')
            hora_pico = d.loc[d['Count'].idxmax(), 'Intervalo']
            hora_str  = hora_pico.strftime('%d %b %H:%M') if hasattr(hora_pico, 'strftime') else ''

            with cols_res[i]:
                st.markdown(
                    f"<div style='border:1px solid #eee;border-top:4px solid {color};"
                    f"border-radius:10px;padding:16px;background:white;"
                    f"box-shadow:0 2px 8px rgba(0,0,0,0.05);'>"
                    f"<div style='font-size:10px;color:{color};font-weight:700;"
                    f"letter-spacing:1px;margin-bottom:8px;'>{proc.upper()}</div>"
                    f"<div style='font-size:32px;font-weight:800;color:#1a1a2e;"
                    f"line-height:1;'>{total:,}</div>"
                    f"<div style='font-size:11px;color:#aaa;margin-top:2px;'>transacciones totales</div>"
                    f"<div style='margin-top:12px;padding-top:12px;border-top:1px solid #f5f5f5;'>"
                    f"<div style='display:flex;justify-content:space-between;margin-bottom:4px;'>"
                    f"<span style='font-size:11px;color:#bbb;'>Pico</span>"
                    f"<span style='font-size:11px;color:#333;font-weight:700;'>{pico} tx</span>"
                    f"</div>"
                    f"<div style='display:flex;justify-content:space-between;margin-bottom:4px;'>"
                    f"<span style='font-size:11px;color:#bbb;'>Promedio</span>"
                    f"<span style='font-size:11px;color:#333;font-weight:700;'>{promedio} tx/{intervalo}</span>"
                    f"</div>"
                    f"<div style='display:flex;justify-content:space-between;'>"
                    f"<span style='font-size:11px;color:#bbb;'>Hora pico</span>"
                    f"<span style='font-size:11px;color:{color};font-weight:700;'>{hora_str}</span>"
                    f"</div>"
                    f"</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )


def _render_top_errores(kpis: dict, key_suffix: str = ""):
    top_err = kpis.get("top_errores", pd.DataFrame())
    if top_err.empty:
        return

    total_tx     = kpis.get("total_tx", 0)
    total_fallas = kpis.get("total_fallas", 0)

    st.markdown("---")
    st.markdown("### 🔴 Análisis de Fallas Técnicas")

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(
            f"<div style='background:#FEE2E2;border-radius:10px;padding:16px;text-align:center;'>"
            f"<div style='font-size:11px;color:#991B1B;font-weight:600;'>TOTAL FALLAS</div>"
            f"<div style='font-size:32px;font-weight:700;color:#991B1B;line-height:1.1;'>{total_fallas:,}</div>"
            f"<div style='font-size:11px;color:#C0392B;'>de {total_tx:,} transacciones</div>"
            f"</div>", unsafe_allow_html=True)
    with m2:
        pct_fallas = (total_fallas / total_tx * 100) if total_tx > 0 else 0
        st.markdown(
            f"<div style='background:#FEF3C7;border-radius:10px;padding:16px;text-align:center;'>"
            f"<div style='font-size:11px;color:#92400E;font-weight:600;'>% DE FALLAS</div>"
            f"<div style='font-size:32px;font-weight:700;color:#92400E;line-height:1.1;'>{pct_fallas:.2f}%</div>"
            f"<div style='font-size:11px;color:#B45309;'>sobre total de transacciones</div>"
            f"</div>", unsafe_allow_html=True)
    with m3:
        top1 = top_err.iloc[0]['Error'] if not top_err.empty else "N/A"
        top1_short = top1.split(":")[0] if ":" in top1 else top1
        st.markdown(
            f"<div style='background:#F3E8FF;border-radius:10px;padding:16px;text-align:center;'>"
            f"<div style='font-size:11px;color:#6B21A8;font-weight:600;'>ERROR PRINCIPAL</div>"
            f"<div style='font-size:32px;font-weight:700;color:#6B21A8;line-height:1.1;'>{top1_short}</div>"
            f"<div style='font-size:11px;color:#7C3AED;'>causa más frecuente</div>"
            f"</div>", unsafe_allow_html=True)

    st.markdown("")

    top_err = top_err.copy()
    top_err['Pct_fallas']  = (top_err['Cantidad'] / total_fallas * 100).round(1) if total_fallas > 0 else 0
    top_err['Pct_total']   = (top_err['Cantidad'] / total_tx * 100).round(2) if total_tx > 0 else 0
    top_err['Error_corto'] = top_err['Error'].apply(lambda x: x[:45] + '...' if len(x) > 45 else x)

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.markdown("**¿Cuál error ocurre más?**")
        st.caption("De cada 100 fallas, ¿cuántas son de este tipo?")
        colors_bar = ['#7F1D1D', '#991B1B', '#C0392B', '#E74C3C', '#F1948A']
        fig1 = go.Figure()
        fig1.add_trace(go.Bar(
            x=top_err['Pct_fallas'], y=top_err['Error_corto'],
            orientation='h', marker_color=colors_bar[:len(top_err)],
            text=[f"{v:.1f}%" for v in top_err['Pct_fallas']], textposition='outside',
            hovertemplate='<b>%{y}</b><br>%{x:.1f}% de las fallas<br>Cantidad: %{customdata:,}<extra></extra>',
            customdata=top_err['Cantidad'],
        ))
        fig1.update_layout(
            height=320, margin=dict(l=10, r=80, t=20, b=20),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(title="% sobre total de fallas", range=[0, 120]),
            yaxis=dict(autorange='reversed'), showlegend=False,
        )
        st.plotly_chart(fig1, use_container_width=True, key=f"chart_err_fallas_{key_suffix}")

    with col_g2:
        st.markdown("**¿Cuánto impactan al total?**")
        st.caption("De cada 100 transacciones totales, ¿cuántas fallan por este error?")
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=top_err['Pct_total'], y=top_err['Error_corto'],
            orientation='h', marker_color='#E67E22',
            text=[f"{v:.2f}%" for v in top_err['Pct_total']], textposition='outside',
            hovertemplate='<b>%{y}</b><br>%{x:.2f}% del total<br>Cantidad: %{customdata:,}<extra></extra>',
            customdata=top_err['Cantidad'],
        ))
        fig2.add_vline(x=0.1, line_dash="dash", line_color="#C0392B",
                       annotation_text="Meta máx 0.1%", annotation_position="top right")
        fig2.update_layout(
            height=320, margin=dict(l=10, r=80, t=20, b=20),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(title="% sobre total de transacciones"),
            yaxis=dict(autorange='reversed'), showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True, key=f"chart_err_total_{key_suffix}")

    st.markdown("**📋 Detalle completo de fallas**")
    df_tabla = top_err[['Error', 'Cantidad', 'Pct_fallas', 'Pct_total']].copy()
    df_tabla.columns = ['Error', 'Cantidad', '% de Fallas', '% del Total']

    def color_pct_fallas(v):
        if v >= 40: return 'background-color:#FEE2E2;color:#991B1B;font-weight:700'
        if v >= 20: return 'background-color:#FEF3C7;color:#92400E'
        return 'background-color:#f9f9f9'

    st.dataframe(
        df_tabla.style
            .map(color_pct_fallas, subset=['% de Fallas'])
            .format({'% de Fallas': '{:.1f}%', '% del Total': '{:.2f}%', 'Cantidad': '{:,}'}),
        use_container_width=True, hide_index=True,
    )

    st.caption(
        f"📌 **Lectura:** '% de Fallas' = proporción del total de fallas ({total_fallas:,}). "
        f"'% del Total' = impacto sobre {total_tx:,} transacciones totales. "
        f"La línea roja marca la meta máxima permitida de 0.1%."
    )

render()