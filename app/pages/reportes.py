"""
pages/reportes.py
Generacion del Reporte Ejecutivo HTML — diseno gerencial.
Con historial de reportes guardados en OneDrive Corporativo ATP y buscador.
"""
import streamlit as st
import pandas as pd
import os
import concurrent.futures
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIG DE PAGINA (titulo de la pestaña del navegador) ────
st.set_page_config(
    page_title="Portal NOC ATP — Reportes Ejecutivos",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── SIDEBAR COMPARTIDO (azul, con botones de navegacion + tunel) ───
from modules.styles import sidebar_comun
sidebar_comun(mostrar_timeouts=False)

from modules.data_processor import (
    procesar_dataframe, calcular_kpis, evaluar_alertas, COL_TIME
)
from modules.kibana_client import (
    obtener_transacciones_raw, obtener_transacciones_custom, verificar_conexion
)
from modules.report_generator import generar_html_ejecutivo

CARPETA_REPORTES = r"C:\Users\MartinRivera\OneDrive - Andean Telecom Partners\Reportes_NOC_ATP"

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


def _asegurar_carpeta():
    os.makedirs(CARPETA_REPORTES, exist_ok=True)


def _nombre_archivo(operador: str, df: pd.DataFrame) -> str:
    if COL_TIME in df.columns and not df.empty:
        inicio = df[COL_TIME].min().strftime('%d-%m-%Y')
        fin    = df[COL_TIME].max().strftime('%d-%m-%Y')
        ts     = datetime.now().strftime('%H%M')
        return f"Reporte_{operador}_{inicio}_al_{fin}_{ts}.html"
    ts = datetime.now().strftime('%d-%m-%Y_%H%M')
    return f"Reporte_{operador}_{ts}.html"


def _guardar_reporte(html: str, nombre: str):
    _asegurar_carpeta()
    ruta = os.path.join(CARPETA_REPORTES, nombre)
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(html)
    return ruta


def _listar_reportes():
    _asegurar_carpeta()
    archivos = [
        f for f in os.listdir(CARPETA_REPORTES)
        if f.startswith("Reporte_") and f.endswith(".html")
    ]
    archivos_con_fecha = []
    for archivo in archivos:
        ruta = os.path.join(CARPETA_REPORTES, archivo)
        fecha_mod = os.path.getmtime(ruta)
        archivos_con_fecha.append((archivo, fecha_mod))
    archivos_con_fecha.sort(key=lambda x: x[1], reverse=True)
    return archivos_con_fecha


def _cargar_operador_custom(operador: str, rango_es: str,
                             fecha_ini_iso=None, fecha_fin_iso=None):
    """Carga datos soportando rango personalizado."""
    try:
        if rango_es == "custom" and fecha_ini_iso and fecha_fin_iso:
            df_raw, err = obtener_transacciones_custom(
                operador, fecha_ini_iso, fecha_fin_iso)
        else:
            df_raw, err = obtener_transacciones_raw(operador, rango_es)
        if err or df_raw.empty:
            return operador, pd.DataFrame(), err or "Sin datos"
        return operador, procesar_dataframe(df_raw), None
    except Exception as e:
        return operador, pd.DataFrame(), str(e)


def _cargar_ambos_paralelo(rango_es: str,
                            fecha_ini_iso=None, fecha_fin_iso=None):
    """Carga CLARO + ETB en paralelo soportando rango personalizado."""
    resultado = {"CLARO": pd.DataFrame(), "ETB": pd.DataFrame(), "errors": {}}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(
                _cargar_operador_custom, op, rango_es,
                fecha_ini_iso, fecha_fin_iso
            ): op
            for op in ["CLARO", "ETB"]
        }
        for future in concurrent.futures.as_completed(futures):
            op, df, err = future.result()
            resultado[op] = df
            if err:
                resultado["errors"][op] = err
    return resultado


def render():
    st.markdown("## 📄 Reportes Ejecutivos")
    st.caption("Genera el reporte gerencial HTML — listo para distribuir a gerencia y operadores.")

    tab_nuevo, tab_historial = st.tabs([
        "📊 Generar Nuevo Reporte",
        "📁 Historial de Reportes"
    ])

    # ═══════════════════════════════════════════════════════════
    # TAB 1 — GENERAR NUEVO REPORTE
    # ═══════════════════════════════════════════════════════════
    with tab_nuevo:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            operador = st.selectbox(
                "Operador",
                ["CLARO", "ETB", "Ambos (CLARO + ETB)"],
                key="rp_op"
            )
        with c2:
            rango_label = st.selectbox(
                "Período del reporte",
                list(RANGOS_RAPIDOS.keys()),
                index=7,
                key="rp_rango"
            )
        with c3:
            fuente = st.radio(
                "Fuente de datos",
                ["🔌 En vivo", "📂 CSV"],
                key="rp_fuente", horizontal=True
            )

        rango_es      = RANGOS_RAPIDOS[rango_label]
        fecha_ini_iso = None
        fecha_fin_iso = None

        # ── RANGO PERSONALIZADO ───────────────────────────────
        if rango_es == "custom":
            st.markdown("#### 📅 Selecciona el rango de fechas")
            cf1, cf2, cf3, cf4 = st.columns(4)
            with cf1:
                fecha_ini = st.date_input(
                    "Fecha inicio",
                    value=date.today() - timedelta(days=1),
                    key="rp_fecha_ini"
                )
            with cf2:
                hora_ini = st.time_input(
                    "Hora inicio",
                    value=datetime.strptime("00:00", "%H:%M").time(),
                    key="rp_hora_ini"
                )
            with cf3:
                fecha_fin = st.date_input(
                    "Fecha fin",
                    value=date.today(),
                    key="rp_fecha_fin"
                )
            with cf4:
                hora_fin = st.time_input(
                    "Hora fin",
                    value=datetime.strptime("23:59", "%H:%M").time(),
                    key="rp_hora_fin"
                )
            fecha_ini_iso = f"{fecha_ini}T{hora_ini.strftime('%H:%M:%S')}.000Z"
            fecha_fin_iso = f"{fecha_fin}T{hora_fin.strftime('%H:%M:%S')}.000Z"

        # Nombre limpio para el reporte
        op_label = "CLARO" if operador == "CLARO" else ("ETB" if operador == "ETB" else "CLARO_ETB")
        es_ambos = "Ambos" in operador

        df = pd.DataFrame()

        # ── FUENTE EN VIVO ────────────────────────────────────
        if "🔌" in fuente:
            if st.button("⚙️ Generar Reporte desde ES", type="primary", key="rp_btn_es"):
                cx = verificar_conexion()
                if not cx["ok"]:
                    st.error(f"Sin conexión al túnel: {cx['msg']}")
                    st.info("Usa la fuente CSV o levanta el túnel SSH primero.")
                else:
                    if es_ambos:
                        # ── AMBOS: CLARO + ETB en paralelo ───
                        with st.spinner("Obteniendo datos CLARO + ETB en paralelo..."):
                            resultado = _cargar_ambos_paralelo(
                                rango_es, fecha_ini_iso, fecha_fin_iso)

                        df_claro = resultado.get("CLARO", pd.DataFrame())
                        df_etb   = resultado.get("ETB",   pd.DataFrame())
                        errors   = resultado.get("errors", {})

                        col_c, col_e = st.columns(2)
                        with col_c:
                            if not df_claro.empty:
                                st.success(f"✅ CLARO: {len(df_claro):,} registros")
                            elif "CLARO" in errors:
                                st.error(f"❌ CLARO: {errors['CLARO']}")
                            else:
                                st.warning("⚠️ CLARO: Sin datos")
                        with col_e:
                            if not df_etb.empty:
                                st.success(f"✅ ETB: {len(df_etb):,} registros")
                            elif "ETB" in errors:
                                st.error(f"❌ ETB: {errors['ETB']}")
                            else:
                                st.warning("⚠️ ETB: Sin datos")

                        dfs = [d for d in [df_claro, df_etb] if not d.empty]
                        if dfs:
                            df = pd.concat(dfs, ignore_index=True)
                            st.info(f"📊 Total combinado: **{len(df):,} registros** (CLARO + ETB)")
                        else:
                            st.warning("Sin datos para ningún operador.")

                    else:
                        # ── OPERADOR ÚNICO ────────────────────
                        with st.spinner(f"Obteniendo datos — {operador} / {rango_label}..."):
                            if rango_es == "custom" and fecha_ini_iso and fecha_fin_iso:
                                df_raw, err = obtener_transacciones_custom(
                                    operador, fecha_ini_iso, fecha_fin_iso)
                            else:
                                df_raw, err = obtener_transacciones_raw(operador, rango_es)

                            if err:
                                st.error(err)
                            elif df_raw.empty:
                                st.warning("Sin datos para el período seleccionado.")
                            else:
                                df = procesar_dataframe(df_raw)
                                st.success(f"✅ {operador}: {len(df):,} registros")

                    if not df.empty:
                        st.session_state.rp_df       = df
                        st.session_state.rp_operador = op_label

            elif "rp_df" in st.session_state:
                df       = st.session_state.rp_df
                op_label = st.session_state.get("rp_operador", op_label)

        # ── FUENTE CSV ────────────────────────────────────────
        else:
            if es_ambos:
                st.markdown("**Carga un CSV por operador:**")
                col_csv1, col_csv2 = st.columns(2)
                with col_csv1:
                    arc_claro = st.file_uploader("📂 CSV CLARO", type=["csv"], key="rp_csv_claro")
                with col_csv2:
                    arc_etb = st.file_uploader("📂 CSV ETB", type=["csv"], key="rp_csv_etb")

                dfs = []
                if arc_claro:
                    dfs.append(procesar_dataframe(pd.read_csv(arc_claro, encoding='latin-1')))
                    st.success("✅ CLARO CSV cargado")
                if arc_etb:
                    dfs.append(procesar_dataframe(pd.read_csv(arc_etb, encoding='latin-1')))
                    st.success("✅ ETB CSV cargado")
                if dfs:
                    df = pd.concat(dfs, ignore_index=True)
                    st.info(f"📊 Total combinado: **{len(df):,} registros**")
                    st.session_state.rp_df       = df
                    st.session_state.rp_operador = op_label
            else:
                arc = st.file_uploader(
                    f"📂 Cargar CSV de {operador}",
                    type=["csv"], key="rp_csv"
                )
                if arc:
                    df       = procesar_dataframe(pd.read_csv(arc, encoding='latin-1'))
                    st.session_state.rp_df       = df
                    st.session_state.rp_operador = op_label
                    st.success(f"✅ {operador}: {len(df):,} registros")

                    if COL_TIME in df.columns and not df.empty:
                        min_d = df[COL_TIME].min().date()
                        max_d = df[COL_TIME].max().date()
                        rango_csv = st.date_input(
                            "Filtrar período", [min_d, max_d], key="rp_fechas"
                        )
                        if len(rango_csv) == 2:
                            df = df[
                                (df[COL_TIME].dt.date >= rango_csv[0]) &
                                (df[COL_TIME].dt.date <= rango_csv[1])
                            ]
                            st.session_state.rp_df = df

            if df.empty and "rp_df" in st.session_state:
                df       = st.session_state.rp_df
                op_label = st.session_state.get("rp_operador", op_label)

        if df.empty:
            st.info("👆 Selecciona la fuente de datos y genera el reporte.")
            return

        # ── VISTA PREVIA DE KPIs ──────────────────────────────
        kpis       = calcular_kpis(df)
        umbral_sla = float(os.getenv("UMBRAL_SLA_CRITICO", 95.0))
        umbral_to  = float(os.getenv("UMBRAL_TIMEOUT_PCT", 5.0))
        umbral_err = float(os.getenv("UMBRAL_ERROR_MASIVO_PCT", 10.0))
        alertas    = evaluar_alertas(kpis, umbral_sla, umbral_to, umbral_err)

        periodo_str = (
            f"{df[COL_TIME].min().strftime('%d/%m/%Y %H:%M')} — "
            f"{df[COL_TIME].max().strftime('%d/%m/%Y %H:%M')}"
            if COL_TIME in df.columns and not df.empty else rango_label
        )

        st.markdown("### Vista previa de KPIs")

        # Desglose por operador si es Ambos
        if es_ambos and 'requestrequestrelatedpartyname' in df.columns:
            st.markdown("**Desglose por operador:**")
            col_c, col_e = st.columns(2)
            for col_ui, op_name, dot in [(col_c, "CLARO", "🔴"), (col_e, "ETB", "🔵")]:
                df_op = df[df['requestrequestrelatedpartyname'] == op_name]
                if not df_op.empty:
                    k_op   = calcular_kpis(df_op)
                    sla_op = k_op["sla_global"]
                    color  = "#166534" if sla_op >= 99.9 else ("#92400E" if sla_op >= 95 else "#991B1B")
                    bg     = "#DCFCE7" if sla_op >= 99.9 else ("#FEF3C7" if sla_op >= 95 else "#FEE2E2")
                    with col_ui:
                        st.markdown(
                            f"<div style='background:{bg};border-radius:10px;padding:14px;'>"
                            f"<div style='font-size:13px;font-weight:700;color:{color};'>"
                            f"{dot} {op_name}</div>"
                            f"<div style='font-size:11px;color:{color};margin-top:4px;'>"
                            f"Total: <b>{k_op['total_tx']:,}</b> · "
                            f"Éxito: <b>{sla_op:.2f}%</b> · "
                            f"Fallas: <b>{k_op['total_fallas']:,}</b>"
                            f"</div></div>",
                            unsafe_allow_html=True
                        )
            st.markdown("")

        # KPIs globales
        k1, k2, k3, k4 = st.columns(4)
        sla = kpis["sla_global"]
        with k1:
            st.metric("Total TX", f"{kpis['total_tx']:,}")
        with k2:
            st.metric(
                "SLA Global", f"{sla:.2f}%",
                delta="✅ Cumple ANS" if sla >= 99.9 else "⚠️ Incumple ANS",
                delta_color="normal" if sla >= 99.9 else "inverse"
            )
        with k3:
            st.metric("% Error",   f"{kpis['pct_error']:.2f}%")
        with k4:
            st.metric("% Timeout", f"{kpis['pct_timeout']:.2f}%")

        for a in alertas:
            css = "alerta-critico" if a["nivel"] == "CRÍTICO" else "alerta-serio"
            st.markdown(
                f"<div class='{css}'>⚠️ <strong>[{a['nivel']}]</strong> "
                f"{a['titulo']} — {a['descripcion']}</div>",
                unsafe_allow_html=True
            )

        op_display = "CLARO + ETB" if es_ambos else operador
        st.markdown(f"**Período:** {periodo_str} | **Operador:** {op_display}")
        st.markdown("---")

        # ── GENERAR Y DESCARGAR ───────────────────────────────
        col_gen, col_dl = st.columns(2)

        with col_gen:
            if st.button("🎯 Generar Reporte Ejecutivo", type="primary", key="rp_gen"):
                with st.spinner("Generando reporte ejecutivo..."):
                    html   = generar_html_ejecutivo(df, kpis, op_display, periodo_str, alertas)
                    nombre = _nombre_archivo(op_label, df)
                    _guardar_reporte(html, nombre)
                    st.session_state.rp_html        = html
                    st.session_state.rp_html_nombre = nombre
                st.success(f"✅ Reporte guardado en OneDrive ATP: **{nombre}**")

        with col_dl:
            if "rp_html" in st.session_state:
                st.download_button(
                    label="📑 Descargar Reporte HTML",
                    data=st.session_state.rp_html,
                    file_name=st.session_state.rp_html_nombre,
                    mime="text/html",
                    type="primary",
                    key="rp_dl"
                )

        if "rp_html" in st.session_state:
            st.markdown("### 👁 Vista Previa")
            st.components.v1.html(st.session_state.rp_html, height=900, scrolling=True)

    # ═══════════════════════════════════════════════════════════
    # TAB 2 — HISTORIAL DE REPORTES
    # ═══════════════════════════════════════════════════════════
    with tab_historial:
        st.markdown("### 📁 Historial de Reportes Guardados")
        st.caption(f"☁️ OneDrive ATP: {CARPETA_REPORTES}")

        col_buscar, col_filtro = st.columns([2, 1])
        with col_buscar:
            busqueda = st.text_input(
                "🔍 Buscar reporte",
                placeholder="Escribe fecha, operador o nombre...",
                key="rp_busqueda"
            )
        with col_filtro:
            filtro_op = st.selectbox(
                "Filtrar por operador",
                ["Todos", "CLARO", "ETB", "CLARO_ETB"],
                key="rp_filtro_op"
            )

        if st.button("🔄 Refrescar historial", key="rp_refresh"):
            st.rerun()

        st.markdown("---")

        reportes = _listar_reportes()

        if not reportes:
            st.info("📭 No hay reportes guardados aún. Genera tu primer reporte.")
        else:
            reportes_filtrados = []
            for nombre, fecha_mod in reportes:
                if filtro_op != "Todos" and filtro_op.upper() not in nombre.upper():
                    continue
                if busqueda and busqueda.lower() not in nombre.lower():
                    continue
                reportes_filtrados.append((nombre, fecha_mod))

            if not reportes_filtrados:
                st.warning("No se encontraron reportes con ese criterio.")
            else:
                st.markdown(f"**{len(reportes_filtrados)} reporte(s) encontrado(s)**")
                st.markdown("")

                for nombre, fecha_mod in reportes_filtrados:
                    ruta      = os.path.join(CARPETA_REPORTES, nombre)
                    fecha_str = datetime.fromtimestamp(fecha_mod).strftime('%d/%m/%Y %H:%M')

                    if "CLARO_ETB" in nombre:
                        color_op = "#6B21A8"
                        emoji_op = "🟣"
                    elif "CLARO" in nombre:
                        color_op = "#C0392B"
                        emoji_op = "🔴"
                    elif "ETB" in nombre:
                        color_op = "#1a6ab5"
                        emoji_op = "🔵"
                    else:
                        color_op = "#888"
                        emoji_op = "⚫"

                    st.markdown(
                        f"<div style='background:white;border:0.5px solid #e0e0e0;"
                        f"border-left:4px solid {color_op};"
                        f"border-radius:8px;padding:12px 16px;margin-bottom:4px;'>"
                        f"<span style='font-size:14px;font-weight:600;'>{emoji_op} {nombre}</span><br>"
                        f"<span style='font-size:12px;color:#888;'>📅 {fecha_str} &nbsp;|&nbsp; "
                        f"☁️ OneDrive ATP</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                    col_ver, col_desc, col_del = st.columns([1, 1, 1])

                    with col_ver:
                        if st.button("👁 Ver", key=f"ver_{nombre}"):
                            with open(ruta, 'r', encoding='utf-8') as f:
                                st.session_state[f"preview_{nombre}"] = f.read()

                    with col_desc:
                        with open(ruta, 'r', encoding='utf-8') as f:
                            contenido = f.read()
                        st.download_button(
                            label="📑 Descargar",
                            data=contenido,
                            file_name=nombre,
                            mime="text/html",
                            key=f"dl_{nombre}"
                        )

                    with col_del:
                        if st.button("🗑 Eliminar", key=f"del_{nombre}"):
                            os.remove(ruta)
                            st.success(f"Eliminado: {nombre}")
                            st.rerun()

                    if f"preview_{nombre}" in st.session_state:
                        st.markdown(f"**Vista previa: {nombre}**")
                        st.components.v1.html(
                            st.session_state[f"preview_{nombre}"],
                            height=800, scrolling=True
                        )
                        if st.button("❌ Cerrar vista previa", key=f"cerrar_{nombre}"):
                            del st.session_state[f"preview_{nombre}"]
                            st.rerun()

                    st.markdown("")

            st.markdown("---")
            st.markdown("### 📊 Resumen del historial")
            total = len(reportes)
            claro = sum(1 for n, _ in reportes if "CLARO_ETB" not in n and "CLARO" in n)
            etb   = sum(1 for n, _ in reportes if "ETB" in n and "CLARO" not in n)
            ambos = sum(1 for n, _ in reportes if "CLARO_ETB" in n)

            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("Total en OneDrive ATP", total)
            with c2: st.metric("Reportes CLARO",        claro)
            with c3: st.metric("Reportes ETB",          etb)
            with c4: st.metric("Reportes CLARO + ETB",  ambos)

render()