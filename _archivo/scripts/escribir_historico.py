codigo = '''"""
pages/historico_timeouts.py
Historico de Timeouts - Portal NOC ATP
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date, timedelta

from modules.timeout_history import (
    leer_historico, limpiar_historico, HISTORY_FILE
)


def _kpi_col(col, label, dot, df_op, total_g):
    total = len(df_op)
    pct   = round(total / total_g * 100, 1) if total_g > 0 else 0
    top   = df_op["proceso"].value_counts().index[0] if not df_op.empty else "sin datos"
    ult   = df_op["fecha_timeout"].max().strftime("%d/%m %H:%M") if not df_op.empty and pd.notna(df_op["fecha_timeout"].max()) else "sin datos"
    with col:
        st.markdown(
            f"<div style=\\'background:white;border:0.5px solid #e0e0e0;border-radius:10px;padding:16px;\\'>"
            f"<div style=\\'display:flex;align-items:center;gap:8px;margin-bottom:12px;border-bottom:1px solid #f0f0f0;padding-bottom:10px;\\'>"
            f"<div style=\\'width:12px;height:12px;border-radius:50%;background:{dot};\\'></div>"
            f"<span style=\\'font-size:14px;font-weight:700;\\'>{label}</span></div>"
            f"<div style=\\'display:grid;grid-template-columns:1fr 1fr;gap:8px;\\'>"
            f"<div style=\\'background:#FEE2E2;border-radius:8px;padding:10px;text-align:center;\\'>"
            f"<div style=\\'font-size:9px;color:#991B1B;font-weight:700;\\'>TOTAL TIMEOUTS</div>"
            f"<div style=\\'font-size:28px;font-weight:800;color:#991B1B;\\'>{total:,}</div></div>"
            f"<div style=\\'background:#FEF3C7;border-radius:8px;padding:10px;text-align:center;\\'>"
            f"<div style=\\'font-size:9px;color:#92400E;font-weight:700;\\'>% DEL TOTAL</div>"
            f"<div style=\\'font-size:28px;font-weight:800;color:#92400E;\\'>{pct}%</div></div></div>"
            f"<div style=\\'margin-top:8px;background:#f9f9f9;border-radius:8px;padding:8px 10px;\\'>"
            f"<div style=\\'font-size:9px;color:#888;\\'>PROCESO MAS AFECTADO</div>"
            f"<div style=\\'font-size:12px;font-weight:700;color:#333;\\'>{top}</div></div>"
            f"<div style=\\'margin-top:6px;background:#f9f9f9;border-radius:8px;padding:8px 10px;\\'>"
            f"<div style=\\'font-size:9px;color:#888;\\'>ULTIMO EVENTO</div>"
            f"<div style=\\'font-size:12px;font-weight:700;color:#333;\\'>{ult}</div></div></div>",
            unsafe_allow_html=True
        )


def render():
    st.markdown("## Historico de Timeouts - Analisis Avanzado")
    st.caption("Monitoreo detallado de eventos REQUEST_TIME_OUT por operador, proceso y linea de tiempo.")

    with st.expander("Importar historico desde Elasticsearch", expanded=False):
        st.markdown("Trae todos los timeouts pasados directamente desde Elasticsearch.")
        im1, im2, im3 = st.columns(3)
        with im1:
            meses = st.selectbox("Meses atras", [1, 2, 3, 6, 9, 12], index=2, key="imp_meses")
        with im2:
            ops_imp = st.multiselect("Operadores", ["CLARO", "ETB"], default=["CLARO", "ETB"], key="imp_ops")
        with im3:
            st.markdown("<div style=\\'margin-top:28px;\\'>", unsafe_allow_html=True)
            btn_estimar = st.button("Estimar cantidad", use_container_width=True, key="btn_estimar")
            st.markdown("</div>", unsafe_allow_html=True)

        if btn_estimar:
            with st.spinner("Consultando Elasticsearch..."):
                try:
                    from modules.timeout_importer import contar_timeouts_elasticsearch
                    conteo = contar_timeouts_elasticsearch(meses_atras=meses)
                    for op, info in conteo.items():
                        if info.get("ok"):
                            st.info(f"**{op}**: {info[\'total\']:,} timeouts en los ultimos {meses} meses")
                        else:
                            st.warning(f"**{op}**: Error - {info.get(\'error\',\'\')}")
                except Exception as e:
                    st.error(f"Error: {e}")

        st.markdown("---")
        col_imp, col_info = st.columns([1, 2])
        with col_imp:
            btn_importar = st.button("Importar ahora", type="primary", use_container_width=True, key="btn_importar")
        with col_info:
            st.caption(f"CSV actual: {HISTORY_FILE} - {len(leer_historico()):,} eventos guardados")

        if btn_importar:
            if not ops_imp:
                st.warning("Selecciona al menos un operador.")
            else:
                log = st.empty()
                barra = st.progress(0)
                mensajes = []
                def progreso(msg):
                    mensajes.append(msg)
                    log.markdown("\\n".join([f"- {m}" for m in mensajes[-6:]]))
                with st.spinner(f"Importando {meses} meses desde Elasticsearch..."):
                    try:
                        from modules.timeout_importer import importar_historico_elasticsearch
                        barra.progress(10)
                        resumen = importar_historico_elasticsearch(meses_atras=meses, operadores=ops_imp, progress_callback=progreso)
                        barra.progress(100)
                        st.success(f"Importacion completa - {resumen[\'total_nuevos\']:,} nuevos timeouts guardados")
                        for op, info in resumen["por_operador"].items():
                            if "error" in info:
                                st.warning(f"{op}: {info[\'error\']}")
                            else:
                                st.info(f"**{op}**: {info[\'encontrados\']:,} encontrados, {info[\'nuevos\']:,} nuevos")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

    st.markdown("---")
    df = leer_historico()

    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        rango_opciones = {"Ultimas 24h": 1, "Ultimos 7 dias": 7, "Ultimos 30 dias": 30, "Todo": 9999, "Rango personalizado": 0}
        filtro_rango = st.selectbox("Periodo", list(rango_opciones.keys()), index=3, key="hist_rango")
    with fc2:
        filtro_op = st.selectbox("Operador", ["Todos", "CLARO", "ETB"], key="hist_op")
    with fc3:
        procs = ["Todos"] + (sorted(df["proceso"].dropna().unique().tolist()) if not df.empty else [])
        filtro_proc = st.selectbox("Proceso", procs, key="hist_proc")
    with fc4:
        st.markdown("<div style=\\'margin-top:28px;\\'>", unsafe_allow_html=True)
        if st.button("Limpiar historico", use_container_width=True, type="secondary"):
            limpiar_historico()
            st.warning("Historico limpiado.")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    fecha_ini_custom = fecha_fin_custom = None
    if filtro_rango == "Rango personalizado":
        fd1, fd2, _, _ = st.columns(4)
        with fd1:
            fecha_ini_custom = st.date_input("Desde", value=date.today() - timedelta(days=7), key="hist_fi")
        with fd2:
            fecha_fin_custom = st.date_input("Hasta", value=date.today(), key="hist_ff")

    df_f = df.copy()
    dias = rango_opciones.get(filtro_rango, 9999)
    if filtro_rango == "Rango personalizado" and fecha_ini_custom and fecha_fin_custom:
        df_f = df_f[(df_f["fecha_timeout"] >= pd.Timestamp(fecha_ini_custom)) & (df_f["fecha_timeout"] <= pd.Timestamp(fecha_fin_custom) + pd.Timedelta(days=1))]
    elif dias < 9999 and not df_f.empty:
        df_f = df_f[df_f["fecha_timeout"] >= pd.Timestamp.now() - pd.Timedelta(days=dias)]
    if filtro_op != "Todos" and not df_f.empty:
        df_f = df_f[df_f["operador"] == filtro_op]
    if filtro_proc != "Todos" and not df_f.empty:
        df_f = df_f[df_f["proceso"] == filtro_proc]

    df_claro = df_f[df_f["operador"] == "CLARO"] if not df_f.empty else pd.DataFrame()
    df_etb   = df_f[df_f["operador"] == "ETB"]   if not df_f.empty else pd.DataFrame()
    total_g  = len(df_f)

    col_g, col_c, col_e = st.columns(3)
    _kpi_col(col_g, "Global (CLARO + ETB)", "#888",    df_f,     total_g)
    _kpi_col(col_c, "CLARO",                "#e5211d", df_claro, total_g)
    _kpi_col(col_e, "ETB",                  "#1a6ab5", df_etb,   total_g)

    if df_f.empty:
        st.info("Sin datos. Usa el panel de importacion para traer el historico desde Elasticsearch.")
        return

    st.markdown("---")
    st.markdown("### Time Outs por Transacciones")
    g1, g2 = st.columns(2)

    with g1:
        df_proc = df_f.groupby(["proceso", "operador"]).size().reset_index(name="count")
        fig1 = go.Figure()
        for op, color in [("CLARO", "#e5211d"), ("ETB", "#1a6ab5")]:
            d = df_proc[df_proc["operador"] == op]
            if not d.empty:
                fig1.add_trace(go.Bar(x=d["proceso"], y=d["count"], name=op, marker_color=color,
                    text=d["count"], textposition="outside",
                    hovertemplate=f"<b>{op}</b><br>%{{x}}<br>Timeouts: <b>%{{y}}</b><extra></extra>"))
        fig1.update_layout(title=dict(text="<b>Timeouts por Proceso</b>", font=dict(size=13)),
            barmode="group", height=360, margin=dict(l=10,r=10,t=50,b=100),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
            xaxis=dict(tickangle=-30, tickfont=dict(size=10), showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", rangemode="tozero"),
            legend=dict(orientation="h", y=-0.35, x=0.5, xanchor="center"))
        st.plotly_chart(fig1, use_container_width=True, key="graf_proc")

    with g2:
        df_f2 = df_f.copy()
        df_f2["hora"] = df_f2["fecha_timeout"].dt.floor("h")
        df_tl = df_f2.groupby(["hora","operador"]).size().reset_index(name="count")
        fig2 = go.Figure()
        for op, color, rgb in [("CLARO","#e5211d","229,33,29"),("ETB","#1a6ab5","26,106,181")]:
            d = df_tl[df_tl["operador"]==op].sort_values("hora")
            if not d.empty:
                fig2.add_trace(go.Scatter(x=d["hora"], y=d["count"], name=op, mode="lines+markers",
                    line=dict(color=color,width=2.5), marker=dict(color=color,size=7,line=dict(color="white",width=1.5)),
                    fill="tozeroy", fillcolor=f"rgba({rgb},0.08)",
                    hovertemplate=f"<b>{op}</b><br>%{{x|%d/%m %H:%M}}<br>Timeouts: <b>%{{y}}</b><extra></extra>"))
        fig2.update_layout(title=dict(text="<b>Time Outs por Hora</b>", font=dict(size=13)),
            height=360, margin=dict(l=10,r=10,t=50,b=60),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
            xaxis=dict(showgrid=True, gridcolor="#f0f0f0", tickformat="%d/%m\\n%H:%M"),
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0", rangemode="tozero"),
            legend=dict(orientation="h",y=-0.2,x=0.5,xanchor="center"), hovermode="x unified")
        st.plotly_chart(fig2, use_container_width=True, key="graf_hora")

    st.markdown("### Time Outs por Consultas - Detalle por Operador")
    g3, g4 = st.columns(2)
    with g3:
        st.markdown("#### CLARO")
        if df_claro.empty:
            st.info("Sin timeouts CLARO.")
        else:
            top_c = df_claro["proceso"].value_counts().reset_index()
            top_c.columns = ["Proceso","Timeouts"]
            fig3 = go.Figure(go.Bar(x=top_c["Timeouts"], y=top_c["Proceso"], orientation="h",
                marker=dict(color=top_c["Timeouts"], colorscale=[[0,"#FFD0D0"],[1,"#C0392B"]], showscale=False),
                text=top_c["Timeouts"], textposition="outside",
                hovertemplate="<b>%{y}</b><br>Timeouts: <b>%{x}</b><extra></extra>"))
            fig3.update_layout(height=300, margin=dict(l=10,r=60,t=20,b=20),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
                xaxis=dict(showgrid=True,gridcolor="#f0f0f0"), yaxis=dict(autorange="reversed"), showlegend=False)
            st.plotly_chart(fig3, use_container_width=True, key="graf_claro")
    with g4:
        st.markdown("#### ETB")
        if df_etb.empty:
            st.info("Sin timeouts ETB.")
        else:
            top_e = df_etb["proceso"].value_counts().reset_index()
            top_e.columns = ["Proceso","Timeouts"]
            fig4 = go.Figure(go.Bar(x=top_e["Timeouts"], y=top_e["Proceso"], orientation="h",
                marker=dict(color=top_e["Timeouts"], colorscale=[[0,"#DBEAFE"],[1,"#1a6ab5"]], showscale=False),
                text=top_e["Timeouts"], textposition="outside",
                hovertemplate="<b>%{y}</b><br>Timeouts: <b>%{x}</b><extra></extra>"))
            fig4.update_layout(height=300, margin=dict(l=10,r=60,t=20,b=20),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
                xaxis=dict(showgrid=True,gridcolor="#f0f0f0"), yaxis=dict(autorange="reversed"), showlegend=False)
            st.plotly_chart(fig4, use_container_width=True, key="graf_etb")

    st.markdown("---")
    st.markdown("### Registro completo de eventos")
    st.markdown(f"Mostrando **{len(df_f):,}** eventos")

    df_tabla = df_f[["fecha_timeout","operador","proceso","codigo","descripcion","rango_consulta","fecha_deteccion"]].copy()
    df_tabla["fecha_timeout"]   = df_tabla["fecha_timeout"].dt.strftime("%d/%m/%Y %H:%M:%S")
    df_tabla["fecha_deteccion"] = df_tabla["fecha_deteccion"].dt.strftime("%d/%m/%Y %H:%M:%S")
    df_tabla = df_tabla.rename(columns={"fecha_timeout":"Fecha Timeout","operador":"Operador",
        "proceso":"Proceso","codigo":"Codigo","descripcion":"Descripcion",
        "rango_consulta":"Rango","fecha_deteccion":"Detectado el"})

    def color_fila(row):
        op = row.get("Operador","")
        if op == "CLARO": return ["background-color:#FFF5F5"]*len(row)
        if op == "ETB":   return ["background-color:#EFF6FF"]*len(row)
        return [""]*len(row)

    st.dataframe(df_tabla.style.apply(color_fila, axis=1), use_container_width=True, hide_index=True, height=380)

    col_exp, _, _ = st.columns([1,2,2])
    with col_exp:
        st.download_button("Exportar CSV", data=df_f.to_csv(index=False).encode("utf-8"),
            file_name=f"timeouts_{datetime.now().strftime(\'%Y%m%d_%H%M\')}.csv",
            mime="text/csv", use_container_width=True)

    st.caption(f"Archivo: {HISTORY_FILE} - {len(df):,} eventos totales guardados")
'''

with open("pages/historico_timeouts.py", "w", encoding="utf-8") as f:
    f.write(codigo)
print("ok - escrito", len(codigo), "caracteres")