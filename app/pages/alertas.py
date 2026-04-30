"""
pages/alertas.py
Panel de Alertas & Monitoreo — motor de detección + acciones Teams/JIRA
NUEVO: Monitor de timeouts 24/7 — alerta si 3+ timeouts en 30 min
NUEVO: Gráfica de fallas en tiempo, franja horaria COT mejorada, SLA profesional
FIX: Filtro fecha/hora, nombres en español, gráficas con más espacio
FIX: df.get() reemplazado por acceso directo a columna Es_Exito_Tecnico
FIX: Zona horaria COT→UTC corregida en rango personalizado
FIX: Session state se limpia al cambiar operador o rango
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import time
from datetime import datetime, timedelta, date, time as dtime
from dotenv import load_dotenv

load_dotenv()


def _icono_nivel(nivel):
    return {"CRÍTICO": "🔴", "SERIO": "🟠", "MEDIO": "🟡", "BAJO": "🟢"}.get(nivel, "⚪")


def _verificar_y_alertar_timeouts(umbral: int = 3, ventana_min: int = 30):
    from modules.timeout_history import leer_historico
    from modules.notificaciones import enviar_alerta_timeouts
    try:
        df_hist = leer_historico()
        if df_hist.empty:
            return {"ok": True, "timeouts": 0, "alerta": False, "msg": "Sin datos en histórico"}
        ahora  = datetime.now()
        desde  = ahora - timedelta(minutes=ventana_min)
        df_rec = df_hist[df_hist["fecha_timeout"] >= pd.Timestamp(desde)]
        total  = len(df_rec)
        if total >= umbral:
            detalle = []
            for _, row in df_rec.head(10).iterrows():
                detalle.append({
                    "timestamp":     str(row.get("fecha_timeout", ""))[:19],
                    "proceso":       row.get("proceso", "—"),
                    "time_taken_ms": row.get("time_taken_ms", 0),
                })
            ops          = df_rec["operador"].unique().tolist()
            operador_str = " + ".join(ops) if ops else "CLARO + ETB"
            res = enviar_alerta_timeouts(
                operador=operador_str, total_timeouts=total,
                ventana_min=ventana_min, detalle_timeouts=detalle,
            )
            return {"ok": res["ok"], "timeouts": total, "alerta": True,
                    "msg": res["msg"], "detalle": detalle, "operador": operador_str}
        return {"ok": True, "timeouts": total, "alerta": False,
                "msg": f"{total} timeouts en últimos {ventana_min} min — bajo el umbral ({umbral})"}
    except Exception as e:
        return {"ok": False, "timeouts": 0, "alerta": False, "msg": f"Error: {e}"}


def _render_sla_profesional(kpis: dict, disp: dict):
    sla          = kpis["sla_global"]
    total_tx     = kpis["total_tx"]
    total_ok     = total_tx - kpis["total_fallas"]
    total_fallas = kpis["total_fallas"]
    total_to     = kpis["total_timeouts"]
    pct_to       = kpis["pct_timeout"]
    pct_err      = kpis["pct_error"]
    cumple       = sla >= 99.9
    color_sla    = "#166534" if sla >= 99.9 else ("#92400E" if sla >= 95 else "#991B1B")
    minutos_ind  = disp["horas_inactividad"] * 60

    st.markdown("### 📊 Estado del Nivel de Servicio (ANS)")
    st.caption("Análisis de disponibilidad y calidad de servicio vs compromisos contractuales con Tecnotree")

    col_gauge, col_kpis = st.columns([1, 2])

    with col_gauge:
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=sla,
            number={"suffix": "%", "font": {"size": 36, "color": color_sla}},
            delta={"reference": 99.9, "valueformat": ".2f",
                   "increasing": {"color": "#166534"},
                   "decreasing": {"color": "#991B1B"}},
            gauge={
                "axis": {"range": [95, 100], "tickwidth": 1,
                         "tickcolor": "#888", "tickformat": ".1f"},
                "bar":  {"color": color_sla, "thickness": 0.3},
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": "#eee",
                "steps": [
                    {"range": [95, 99],    "color": "#FEE2E2"},
                    {"range": [99, 99.9],  "color": "#FEF3C7"},
                    {"range": [99.9, 100], "color": "#DCFCE7"},
                ],
                "threshold": {
                    "line": {"color": "#3C3489", "width": 3},
                    "thickness": 0.75,
                    "value": 99.9,
                },
            },
            title={"text": "SLA Actual<br><span style='font-size:12px;color:#888;'>Meta contractual: 99.9%</span>",
                   "font": {"size": 14}},
        ))
        fig_gauge.update_layout(
            height=260, margin=dict(l=20, r=20, t=40, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_gauge, use_container_width=True, key="gauge_sla")

        badge_txt = "✅ CUMPLE ANS" if cumple else "❌ INCUMPLE ANS"
        badge_bg  = "#DCFCE7" if cumple else "#FEE2E2"
        badge_col = "#166534" if cumple else "#991B1B"
        st.markdown(
            f"<div style='background:{badge_bg};border-radius:8px;padding:10px;"
            f"text-align:center;border:1px solid {badge_col}20;'>"
            f"<div style='font-size:14px;font-weight:800;color:{badge_col};'>{badge_txt}</div>"
            f"<div style='font-size:11px;color:{badge_col};opacity:0.8;margin-top:2px;'>"
            f"Meta: 99.9% · Actual: {sla:.3f}%</div>"
            f"</div>", unsafe_allow_html=True)

    with col_kpis:
        k1, k2 = st.columns(2)
        k3, k4 = st.columns(2)
        with k1:
            st.markdown(
                f"<div style='background:#f0f4ff;border-radius:10px;padding:14px;border-left:4px solid #3C3489;'>"
                f"<div style='font-size:10px;color:#3C3489;font-weight:700;letter-spacing:1px;'>📦 TOTAL TX</div>"
                f"<div style='font-size:28px;font-weight:800;color:#1a1a2e;line-height:1.1;'>{total_tx:,}</div>"
                f"<div style='font-size:11px;color:#888;'>transacciones en el período</div>"
                f"</div>", unsafe_allow_html=True)
        with k2:
            st.markdown(
                f"<div style='background:#DCFCE7;border-radius:10px;padding:14px;border-left:4px solid #166534;'>"
                f"<div style='font-size:10px;color:#166534;font-weight:700;letter-spacing:1px;'>✅ EXITOSAS</div>"
                f"<div style='font-size:28px;font-weight:800;color:#166534;line-height:1.1;'>{total_ok:,}</div>"
                f"<div style='font-size:11px;color:#166534;opacity:0.8;'>{total_ok/total_tx*100:.2f}% del total</div>"
                f"</div>", unsafe_allow_html=True)
        with k3:
            st.markdown(
                f"<div style='background:#FEE2E2;border-radius:10px;padding:14px;border-left:4px solid #991B1B;'>"
                f"<div style='font-size:10px;color:#991B1B;font-weight:700;letter-spacing:1px;'>❌ FALLAS</div>"
                f"<div style='font-size:28px;font-weight:800;color:#991B1B;line-height:1.1;'>{total_fallas:,}</div>"
                f"<div style='font-size:11px;color:#991B1B;opacity:0.8;'>{pct_err:.2f}% del total</div>"
                f"</div>", unsafe_allow_html=True)
        with k4:
            to_col = "#991B1B" if pct_to > 0 else "#166534"
            to_bg  = "#FEE2E2" if pct_to > 0 else "#DCFCE7"
            st.markdown(
                f"<div style='background:{to_bg};border-radius:10px;padding:14px;border-left:4px solid {to_col};'>"
                f"<div style='font-size:10px;color:{to_col};font-weight:700;letter-spacing:1px;'>⏱ TIMEOUTS</div>"
                f"<div style='font-size:28px;font-weight:800;color:{to_col};line-height:1.1;'>{total_to:,}</div>"
                f"<div style='font-size:11px;color:{to_col};opacity:0.8;'>{pct_to:.2f}% del total</div>"
                f"</div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-top:12px;'>", unsafe_allow_html=True)
        max_ind   = 43.2
        ind_color = "#166534" if minutos_ind <= max_ind else "#991B1B"
        pct_usado = min(minutos_ind / max_ind * 100, 100)
        st.markdown(
            f"<div style='background:#f9f9f9;border-radius:10px;padding:14px;border:1px solid #eee;'>"
            f"<div style='display:flex;justify-content:space-between;margin-bottom:8px;'>"
            f"<span style='font-size:11px;font-weight:700;color:#333;'>📅 Inactividad mensual estimada</span>"
            f"<span style='font-size:11px;color:{ind_color};font-weight:700;'>"
            f"{minutos_ind:.1f} min / {max_ind} min máx ANS</span>"
            f"</div>"
            f"<div style='background:#e0e0e0;border-radius:4px;height:12px;overflow:hidden;'>"
            f"<div style='background:{ind_color};width:{pct_usado:.1f}%;height:100%;border-radius:4px;'></div>"
            f"</div>"
            f"<div style='display:flex;justify-content:space-between;margin-top:6px;'>"
            f"<span style='font-size:10px;color:#888;'>0 min</span>"
            f"<span style='font-size:10px;color:{ind_color};font-weight:600;'>"
            f"{'✅ Dentro del límite' if minutos_ind <= max_ind else '❌ Excede límite ANS'}</span>"
            f"<span style='font-size:10px;color:#888;'>43.2 min (ANS máx)</span>"
            f"</div></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("📋 Ver tabla ANS contractual completa", expanded=False):
        ans_data = {
            "Criticidad":          ["🔴 CRÍTICO",   "🟠 SERIO",    "🟡 MEDIO",    "🟢 BAJO"],
            "T. Respuesta":        ["15 min",        "15 min",      "8 horas",     "24 horas"],
            "T. Restablecimiento": ["3 horas",       "8 horas",     "5 días",      "30 días"],
            "Solución Definitiva": ["2 días cal.",   "7 días cal.", "30 días cal.", "90 días cal."],
            "Umbral Plan Mejora":  ["≥ 2 / mes",    "≥ 4 / mes",   "≥ 4 / mes",   "N/A"],
            "Descripción": [
                "Interrupción total del servicio",
                "Degradación severa del servicio",
                "Falla parcial o degradación leve",
                "Incidencia menor sin impacto operativo",
            ],
        }
        df_ans = pd.DataFrame(ans_data)

        def color_ans(row):
            if "CRÍTICO" in row["Criticidad"]: return ["background-color:#FEE2E2"] * len(row)
            if "SERIO"   in row["Criticidad"]: return ["background-color:#FEF3C7"] * len(row)
            if "MEDIO"   in row["Criticidad"]: return ["background-color:#FFFBEB"] * len(row)
            return ["background-color:#F0FFF4"] * len(row)

        st.dataframe(df_ans.style.apply(color_ans, axis=1),
                     use_container_width=True, hide_index=True)
        st.caption("ANS Tecnotree: Disponibilidad mínima mensual ≥ 99.9% — máximo 43.2 min de inactividad en 30 días")


def _render_fallas_tiempo(df: pd.DataFrame, kpis: dict):
    from modules.data_processor import COL_TIME, COL_TRANS

    st.markdown("### 📈 Comportamiento de Fallas en el Tiempo")
    st.caption("Evolución temporal de fallas técnicas por proceso — hora Colombia (COT)")

    if df.empty or COL_TIME not in df.columns:
        st.info("Sin datos para graficar.")
        return

    # ✅ FIX 1: acceso directo a columna en lugar de df.get()
    if "Es_Exito_Tecnico" not in df.columns:
        st.warning("⚠️ No se encontró la columna Es_Exito_Tecnico en los datos.")
        return

    df_f = df[~df["Es_Exito_Tecnico"]].copy()
    if df_f.empty:
        st.success("✅ No se detectaron fallas en el período analizado.")
        return

    dias      = (df[COL_TIME].max() - df[COL_TIME].min()).days
    intervalo = "5min" if dias <= 1 else ("30min" if dias <= 3 else "1h")
    df_f["Intervalo"] = df_f[COL_TIME].dt.floor(intervalo)

    df_total = df_f.groupby("Intervalo").size().reset_index(name="Fallas")

    # ✅ FIX 1: acceso directo a columna en lugar de df.get()
    df_ok = df[df["Es_Exito_Tecnico"]].copy()
    df_ok["Intervalo"] = df_ok[COL_TIME].dt.floor(intervalo)
    df_ok_t   = df_ok.groupby("Intervalo").size().reset_index(name="Exitosas")
    df_merged = df_total.merge(df_ok_t, on="Intervalo", how="outer").fillna(0)
    df_merged["Total"]     = df_merged["Fallas"] + df_merged["Exitosas"]
    df_merged["Pct_Falla"] = (df_merged["Fallas"] / df_merged["Total"] * 100).round(2)

    fig1 = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.65, 0.35], vertical_spacing=0.10,
        subplot_titles=["Volumen de fallas vs transacciones exitosas",
                        "% de fallas sobre el total"]
    )
    fig1.add_trace(go.Bar(
        x=df_merged["Intervalo"], y=df_merged["Exitosas"],
        name="Exitosas", marker_color="#1D9E75", opacity=0.7,
        hovertemplate="<b>Exitosas</b><br>%{x|%d/%m %H:%M}<br>%{y:,}<extra></extra>",
    ), row=1, col=1)
    fig1.add_trace(go.Bar(
        x=df_merged["Intervalo"], y=df_merged["Fallas"],
        name="Fallas", marker_color="#C0392B",
        hovertemplate="<b>Fallas</b><br>%{x|%d/%m %H:%M}<br>%{y:,}<extra></extra>",
    ), row=1, col=1)
    fig1.add_trace(go.Scatter(
        x=df_merged["Intervalo"], y=df_merged["Pct_Falla"],
        name="% Fallas", mode="lines+markers",
        line=dict(color="#E67E22", width=2.5),
        marker=dict(size=6, color="#E67E22"),
        fill="tozeroy", fillcolor="rgba(230,126,34,0.1)",
        hovertemplate="<b>% Fallas</b><br>%{x|%d/%m %H:%M}<br>%{y:.2f}%<extra></extra>",
    ), row=2, col=1)
    fig1.add_hline(y=0.1, line_dash="dash", line_color="#C0392B",
                   line_width=1.5, row=2, col=1,
                   annotation_text="Meta máx 0.1%",
                   annotation_font_size=10,
                   annotation_position="right")
    fig1.update_layout(
        height=560, barmode="stack",
        margin=dict(l=10, r=100, t=60, b=40),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
        legend=dict(orientation="h", y=-0.06, x=0.5, xanchor="center",
                    font=dict(size=12), bgcolor="rgba(255,255,255,0.8)"),
        hovermode="x unified",
    )
    fig1.update_xaxes(showgrid=True, gridcolor="#f0f0f0",
                      tickformat="%d/%m\n%H:%M", tickfont=dict(size=10),
                      tickangle=0)
    fig1.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    st.plotly_chart(fig1, use_container_width=True, key="graf_fallas_tiempo")

    st.markdown("<div style='margin-top:24px;'>", unsafe_allow_html=True)
    st.markdown("#### Fallas por proceso — evolución temporal")
    top_procesos = df_f[COL_TRANS].value_counts().head(5).index.tolist()
    df_proc_t = (df_f[df_f[COL_TRANS].isin(top_procesos)]
                 .groupby(["Intervalo", COL_TRANS]).size()
                 .reset_index(name="Fallas"))
    COLORES_F = ["#C0392B", "#E67E22", "#9B59B6", "#3498DB", "#1ABC9C"]
    fig2 = go.Figure()
    for i, proc in enumerate(top_procesos):
        d = df_proc_t[df_proc_t[COL_TRANS] == proc]
        if d.empty:
            continue
        fig2.add_trace(go.Scatter(
            x=d["Intervalo"], y=d["Fallas"],
            name=proc, mode="lines+markers",
            line=dict(color=COLORES_F[i % len(COLORES_F)], width=2.5, shape="spline"),
            marker=dict(size=6),
            hovertemplate=f"<b>{proc}</b><br>%{{x|%d/%m %H:%M}}<br>Fallas: <b>%{{y}}</b><extra></extra>",
        ))
    fig2.update_layout(
        height=380,
        margin=dict(l=10, r=20, t=20, b=100),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="#f0f0f0",
                   tickformat="%d/%m\n%H:%M", tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0", rangemode="tozero",
                   title="Cantidad de fallas"),
        legend=dict(orientation="h", y=-0.28, x=0.5, xanchor="center",
                    font=dict(size=11), bgcolor="rgba(255,255,255,0.8)"),
        hovermode="x unified",
    )
    st.plotly_chart(fig2, use_container_width=True, key="graf_fallas_proceso")
    st.markdown("</div>", unsafe_allow_html=True)


def _render_franja_horaria(df: pd.DataFrame):
    from modules.data_processor import COL_TIME, COL_TRANS

    st.markdown("### 🕐 Distribución de Fallas por Hora — Colombia (COT)")
    st.caption("Análisis de patrones horarios para identificar ventanas críticas de operación")

    if df.empty or COL_TIME not in df.columns:
        st.info("Sin datos.")
        return

    # ✅ FIX 1: acceso directo a columna en lugar de df.get()
    if "Es_Exito_Tecnico" not in df.columns:
        st.warning("⚠️ No se encontró la columna Es_Exito_Tecnico en los datos.")
        return

    df_f = df[~df["Es_Exito_Tecnico"]].copy()
    if df_f.empty:
        st.success("✅ Sin fallas en el período.")
        return

    df_f["Hora"] = df_f[COL_TIME].dt.hour

    # ── Mapa de Calor ─────────────────────────────────────────
    st.markdown("#### 🌡️ Mapa de Calor — Fallas por hora y proceso")
    top5    = df_f[COL_TRANS].value_counts().head(5).index.tolist()
    df_heat = (df_f[df_f[COL_TRANS].isin(top5)]
               .groupby(["Hora", COL_TRANS]).size()
               .reset_index(name="Fallas"))
    pivot = df_heat.pivot(index=COL_TRANS, columns="Hora", values="Fallas").fillna(0)
    for h in range(24):
        if h not in pivot.columns:
            pivot[h] = 0
    pivot = pivot[sorted(pivot.columns)]

    fig_heat = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[f"{h:02d}:00" for h in pivot.columns],
        y=pivot.index.tolist(),
        colorscale=[
            [0.0, "#f0f4ff"], [0.3, "#FEF3C7"],
            [0.6, "#FBBF24"], [0.8, "#EF4444"], [1.0, "#7F1D1D"],
        ],
        hovertemplate="<b>%{y}</b><br>Hora: %{x}<br>Fallas: <b>%{z:.0f}</b><extra></extra>",
        showscale=True,
        colorbar=dict(title=dict(text="Fallas", side="right"),
                      thickness=15, len=0.9, tickfont=dict(size=11)),
    ))
    fig_heat.update_layout(
        height=max(280, len(top5) * 60),
        margin=dict(l=10, r=80, t=20, b=60),
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(size=10), title=dict(text="Hora Colombia (COT)", font=dict(size=11)),
                   tickangle=-45),
        yaxis=dict(tickfont=dict(size=11), automargin=True),
    )
    st.plotly_chart(fig_heat, use_container_width=True, key="heatmap_hora")

    # ── Barras por hora ───────────────────────────────────────
    st.markdown("<div style='margin-top:24px;'>", unsafe_allow_html=True)
    st.markdown("#### 📊 Fallas por hora del día")
    hora_counts = df_f.groupby("Hora").size().reset_index(name="Fallas")
    horas_completas = pd.DataFrame({"Hora": range(24)})
    hora_counts = horas_completas.merge(hora_counts, on="Hora", how="left").fillna(0)
    hora_counts["Fallas"] = hora_counts["Fallas"].astype(int)
    hora_counts["Franja"] = hora_counts["Hora"].apply(
        lambda h: "Madrugada" if h < 6
        else ("Mañana" if h < 12 else ("Tarde" if h < 18 else "Noche"))
    )
    colores_franja = {
        "Madrugada": "#6366f1", "Mañana": "#F59E0B",
        "Tarde":     "#EF4444", "Noche":  "#1a1a2e",
    }
    hora_counts["Color"] = hora_counts["Franja"].map(colores_franja)

    fig_bar = go.Figure(go.Bar(
        x=hora_counts["Hora"],
        y=hora_counts["Fallas"],
        marker_color=hora_counts["Color"].tolist(),
        text=hora_counts["Fallas"].apply(lambda x: str(x) if x > 0 else ""),
        textposition="outside",
        textfont=dict(size=10),
        hovertemplate="<b>%{x}:00 COT</b><br>Fallas: <b>%{y}</b><extra></extra>",
    ))
    fig_bar.update_layout(
        height=340,
        margin=dict(l=10, r=10, t=20, b=60),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
        xaxis=dict(tickmode="linear", dtick=1, title=dict(text="Hora Colombia (COT)", font=dict(size=11)),
                   showgrid=False, tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0", rangemode="tozero",
                   title=dict(text="Cantidad de fallas", font=dict(size=11))),
        showlegend=False,
    )
    for franja, color in colores_franja.items():
        fig_bar.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers",
            marker=dict(size=10, color=color, symbol="square"),
            name=franja, showlegend=True,
        ))
    fig_bar.update_layout(
        legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center", font=dict(size=11))
    )
    st.plotly_chart(fig_bar, use_container_width=True, key="bar_hora")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Cards por franja ─────────────────────────────────────
    st.markdown("<div style='margin-top:16px;'>", unsafe_allow_html=True)
    franjas = {
        "🌙 Madrugada\n00:00 – 05:59": (0, 5),
        "🌅 Mañana\n06:00 – 11:59":    (6, 11),
        "☀️ Tarde\n12:00 – 17:59":     (12, 17),
        "🌆 Noche\n18:00 – 23:59":     (18, 23),
    }
    total_fallas = len(df_f)
    f1, f2, f3, f4 = st.columns(4)

    for col, (label, (h_ini, h_fin)) in zip([f1, f2, f3, f4], franjas.items()):
        cnt     = len(df_f[(df_f["Hora"] >= h_ini) & (df_f["Hora"] <= h_fin)])
        pct     = round(cnt / total_fallas * 100, 1) if total_fallas > 0 else 0
        es_pico = cnt == max(
            len(df_f[(df_f["Hora"] >= a) & (df_f["Hora"] <= b)])
            for _, (a, b) in franjas.items()
        )
        bg    = "#FEE2E2" if es_pico else "#f9f9f9"
        color = "#991B1B" if es_pico else "#555"
        borde = "border:2px solid #991B1B;" if es_pico else "border:1px solid #eee;"
        pico_badge = "<div style='font-size:9px;color:#991B1B;font-weight:700;margin-top:4px;'>⚠️ FRANJA CRÍTICA</div>" if es_pico else ""
        lineas = label.split("\n")
        with col:
            st.markdown(
                f"<div style='background:{bg};border-radius:10px;padding:14px;{borde}text-align:center;'>"
                f"<div style='font-size:14px;font-weight:700;color:{color};'>{lineas[0]}</div>"
                f"<div style='font-size:10px;color:#888;margin-bottom:8px;'>{lineas[1]}</div>"
                f"<div style='font-size:28px;font-weight:800;color:{color};'>{cnt:,}</div>"
                f"<div style='font-size:11px;color:{color};opacity:0.8;'>{pct}% del total</div>"
                f"{pico_badge}"
                f"</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render():
    from modules.data_processor import (
        procesar_dataframe, calcular_kpis, evaluar_alertas,
        calcular_disponibilidad_mensual, COL_TIME, COL_CODE,
        FALLAS_TECNICAS, COL_TRANS, CODIGOS_FALLA_KIBANA
    )
    from modules.kibana_client import (
        obtener_transacciones_raw, obtener_transacciones_custom, verificar_conexion
    )
    from modules.notificaciones import enviar_alerta_teams, crear_ticket_jira

    st.markdown("## 🚨 Alertas & Monitoreo ANS")

    # ─── MONITOR 24/7 ─────────────────────────────────────────
    st.markdown("### 🕐 Monitor Automático de Timeouts — 24/7")
    with st.container():
        st.markdown(
            "<div style='background:#1a1a2e;border-radius:10px;padding:16px 20px;margin-bottom:16px;'>"
            "<div style='color:white;font-size:13px;font-weight:600;margin-bottom:4px;'>"
            "⚡ MONITOR EN TIEMPO REAL — Alerta si ≥ 3 timeouts en 30 minutos</div>"
            "<div style='color:#aaa;font-size:12px;'>"
            "Consulta el histórico cada 30 min · Envía correo automático al equipo NOC · Activo 24/7"
            "</div></div>", unsafe_allow_html=True)

        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1:
            umbral_to = st.number_input("⚠️ Umbral timeouts", min_value=1, max_value=20,
                                        value=3, step=1, key="mon_umbral")
        with mc2:
            ventana_min = st.selectbox("🕐 Ventana", [15, 30, 60], index=1, key="mon_ventana")
        with mc3:
            intervalo_check = st.selectbox("🔁 Revisar cada",
                                           ["30 minutos", "15 minutos", "1 hora"],
                                           key="mon_intervalo")
            intervalo_seg = {"30 minutos": 1800, "15 minutos": 900, "1 hora": 3600}[intervalo_check]
        with mc4:
            st.markdown("<div style='margin-top:28px;'>", unsafe_allow_html=True)
            monitor_activo = st.toggle("🟢 Monitor activo",
                                       value=st.session_state.get("mon_activo", False),
                                       key="mon_toggle")
            st.markdown("</div>", unsafe_allow_html=True)

        if monitor_activo:
            st.session_state.mon_activo = True
            ultimo_check = st.session_state.get("mon_ultimo_check", 0)
            ahora_ts     = time.time()
            tiempo_desde = ahora_ts - ultimo_check
            prox_check   = max(0, intervalo_seg - tiempo_desde)

            e1, e2, e3 = st.columns(3)
            with e1:
                st.markdown(
                    "<div style='background:#DCFCE7;border-radius:8px;padding:10px;text-align:center;'>"
                    "<div style='font-size:10px;color:#166534;font-weight:700;'>ESTADO</div>"
                    "<div style='font-size:16px;font-weight:800;color:#166534;'>🟢 ACTIVO</div>"
                    "</div>", unsafe_allow_html=True)
            with e2:
                ultimo_str = (datetime.fromtimestamp(ultimo_check).strftime("%H:%M:%S")
                              if ultimo_check > 0 else "Pendiente")
                st.markdown(
                    f"<div style='background:#f0f4ff;border-radius:8px;padding:10px;text-align:center;'>"
                    f"<div style='font-size:10px;color:#3C3489;font-weight:700;'>ÚLTIMA REVISIÓN</div>"
                    f"<div style='font-size:16px;font-weight:800;color:#3C3489;'>{ultimo_str}</div>"
                    f"</div>", unsafe_allow_html=True)
            with e3:
                st.markdown(
                    f"<div style='background:#FEF3C7;border-radius:8px;padding:10px;text-align:center;'>"
                    f"<div style='font-size:10px;color:#92400E;font-weight:700;'>PRÓXIMA REVISIÓN</div>"
                    f"<div style='font-size:16px;font-weight:800;color:#92400E;'>"
                    f"en {int(prox_check//60)}m {int(prox_check%60)}s</div>"
                    f"</div>", unsafe_allow_html=True)

            if tiempo_desde >= intervalo_seg or ultimo_check == 0:
                with st.spinner("🔍 Verificando timeouts..."):
                    resultado = _verificar_y_alertar_timeouts(umbral_to, ventana_min)
                    st.session_state.mon_ultimo_check = ahora_ts
                    if "mon_historial" not in st.session_state:
                        st.session_state.mon_historial = []
                    st.session_state.mon_historial.insert(0, {
                        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                        "timeouts":  resultado["timeouts"],
                        "alerta":    resultado["alerta"],
                        "msg":       resultado["msg"],
                    })
                    st.session_state.mon_historial = st.session_state.mon_historial[:48]
                if resultado["alerta"]:
                    st.error(f"🚨 **ALERTA** — {resultado['timeouts']} timeouts — correo enviado ✅")
                else:
                    st.success(f"✅ {resultado['msg']}")
            time.sleep(1)
            st.rerun()
        else:
            st.session_state.mon_activo = False
            st.markdown(
                "<div style='background:#f9f9f9;border-radius:8px;padding:12px;"
                "text-align:center;border:1px dashed #ccc;'>"
                "<span style='color:#888;font-size:13px;'>⏸ Monitor pausado</span>"
                "</div>", unsafe_allow_html=True)

        col_b1, col_b2, _ = st.columns([1, 1, 3])
        with col_b1:
            if st.button("🔍 Verificar ahora", key="mon_check_manual", type="primary"):
                with st.spinner("Verificando..."):
                    resultado = _verificar_y_alertar_timeouts(umbral_to, ventana_min)
                    st.session_state.mon_ultimo_check = time.time()
                    if "mon_historial" not in st.session_state:
                        st.session_state.mon_historial = []
                    st.session_state.mon_historial.insert(0, {
                        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                        "timeouts":  resultado["timeouts"],
                        "alerta":    resultado["alerta"],
                        "msg":       resultado["msg"],
                    })
                if resultado["alerta"]:
                    st.error(f"🚨 {resultado['timeouts']} timeouts — correo enviado ✅")
                else:
                    st.success(f"✅ {resultado['msg']}")
        with col_b2:
            if st.button("🗑️ Limpiar historial", key="mon_limpiar"):
                st.session_state.mon_historial = []
                st.rerun()

        if st.session_state.get("mon_historial"):
            st.markdown("#### 📋 Historial de revisiones")
            df_hm = pd.DataFrame(st.session_state.mon_historial)
            df_hm["Estado"] = df_hm["alerta"].apply(
                lambda x: "🚨 ALERTA ENVIADA" if x else "✅ Normal")
            df_hm = df_hm[["timestamp", "timeouts", "Estado", "msg"]]
            df_hm.columns = ["Hora revisión", "Timeouts", "Estado", "Detalle"]

            def color_hist(row):
                if row["Estado"].startswith("🚨"):
                    return ["background-color:#FEE2E2"] * len(row)
                return ["background-color:#DCFCE7"] * len(row)

            st.dataframe(df_hm.style.apply(color_hist, axis=1),
                         use_container_width=True, hide_index=True, height=220)

    st.markdown("---")

    # ─── UMBRALES ─────────────────────────────────────────────
    with st.expander("⚙️ Configurar umbrales de alerta", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            umbral_sla = st.number_input("SLA mínimo (%)", 80.0, 100.0,
                                         float(os.getenv("UMBRAL_SLA_CRITICO", 95.0)), 0.1, key="al_sla")
        with c2:
            umbral_to_kpi = st.number_input("Timeout máximo (%)", 1.0, 50.0,
                                            float(os.getenv("UMBRAL_TIMEOUT_PCT", 5.0)), 0.5, key="al_to")
        with c3:
            umbral_err = st.number_input("Error masivo (%)", 1.0, 50.0,
                                         float(os.getenv("UMBRAL_ERROR_MASIVO_PCT", 10.0)), 0.5, key="al_err")

    st.markdown("---")

    # ─── FUENTE DE DATOS CON FECHA/HORA ───────────────────────
    st.markdown("<div style='background:#f8f9fa;border-radius:10px;padding:14px 18px;margin-bottom:16px;'>",
                unsafe_allow_html=True)

    c_op, c_rango, c_fuente = st.columns([1, 2, 1])
    with c_op:
        operador = st.selectbox("🏢 Operador", ["Ambos", "CLARO", "ETB"], key="al_op")
    with c_rango:
        rango_label = st.selectbox(
            "🕐 Ventana de análisis",
            ["Última hora", "Últimas 6 horas", "Últimas 24 horas",
             "Últimos 7 días", "📅 Rango personalizado"],
            index=2, key="al_rango")
    with c_fuente:
        fuente = st.radio("Fuente", ["🔌 En vivo", "📂 CSV"], key="al_fuente", horizontal=True)

    # ✅ FIX 3: limpiar session state al cambiar operador o rango
    if "al_op_prev" not in st.session_state:
        st.session_state.al_op_prev = operador
    if "al_rango_prev" not in st.session_state:
        st.session_state.al_rango_prev = rango_label

    if (st.session_state.al_op_prev != operador or
            st.session_state.al_rango_prev != rango_label):
        st.session_state.pop("al_df", None)
        st.session_state.al_op_prev = operador
        st.session_state.al_rango_prev = rango_label

    # Rango personalizado con fecha y hora
    fecha_ini_iso = None
    fecha_fin_iso = None

    if rango_label == "📅 Rango personalizado":
        fd1, fd2, fd3, fd4 = st.columns(4)
        with fd1:
            fecha_ini = st.date_input("📅 Desde (fecha)",
                                      value=date.today() - timedelta(days=1),
                                      key="al_fecha_ini")
        with fd2:
            hora_ini = st.time_input("🕐 Hora inicio",
                                     value=dtime(0, 0),
                                     key="al_hora_ini")
        with fd3:
            fecha_fin = st.date_input("📅 Hasta (fecha)",
                                      value=date.today(),
                                      key="al_fecha_fin")
        with fd4:
            hora_fin = st.time_input("🕐 Hora fin",
                                     value=dtime(23, 59),
                                     key="al_hora_fin")

        dt_ini = datetime.combine(fecha_ini, hora_ini)
        dt_fin = datetime.combine(fecha_fin, hora_fin)

        # ✅ FIX 2: convertir COT → UTC antes de enviar a Kibana (COT = UTC-5)
        COT_A_UTC = timedelta(hours=5)
        fecha_ini_iso = (dt_ini + COT_A_UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        fecha_fin_iso = (dt_fin + COT_A_UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        st.caption(
            f"🔍 Analizando: **{dt_ini.strftime('%d/%m/%Y %H:%M')} COT** "
            f"→ **{dt_fin.strftime('%d/%m/%Y %H:%M')} COT** "
            f"(enviado a Kibana como UTC: {(dt_ini + COT_A_UTC).strftime('%H:%M')} → "
            f"{(dt_fin + COT_A_UTC).strftime('%H:%M')})"
        )

    rango_map = {
        "Última hora":      "now-1h",
        "Últimas 6 horas":  "now-6h",
        "Últimas 24 horas": "now-24h",
        "Últimos 7 días":   "now-7d",
    }

    st.markdown("<div style='margin-top:10px;'>", unsafe_allow_html=True)
    col_btn, _ = st.columns([1, 4])
    with col_btn:
        analizar = st.button("🔄 Analizar Ahora", type="primary", key="al_btn")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    df = pd.DataFrame()

    if "🔌" in fuente:
        if analizar:
            cx = verificar_conexion()
            if not cx["ok"]:
                st.error(f"Sin conexión: {cx['msg']}")
                return
            with st.spinner("Analizando..."):
                if rango_label == "📅 Rango personalizado" and fecha_ini_iso and fecha_fin_iso:
                    df_raw, err = obtener_transacciones_custom(operador, fecha_ini_iso, fecha_fin_iso)
                else:
                    df_raw, err = obtener_transacciones_raw(operador, rango_map[rango_label])
                if err:
                    st.error(err)
                    return
                if not df_raw.empty:
                    df = procesar_dataframe(df_raw)
                    st.session_state.al_df = df
                else:
                    st.warning("Sin datos para el período seleccionado.")
                    return
        elif "al_df" in st.session_state:
            df = st.session_state.al_df
    else:
        arc = st.file_uploader("CSV de Kibana", type=["csv"], key="al_csv")
        if arc:
            df = procesar_dataframe(pd.read_csv(arc, encoding="latin-1"))
            st.session_state.al_df = df
        elif "al_df" in st.session_state:
            df = st.session_state.al_df

    if df.empty:
        st.info("👆 Selecciona fuente y analiza para ver el panel de alertas.")
        return

    kpis    = calcular_kpis(df)
    alertas = evaluar_alertas(kpis, umbral_sla, umbral_to_kpi, umbral_err)
    disp    = calcular_disponibilidad_mensual(df)

    # ─── SLA PROFESIONAL ──────────────────────────────────────
    _render_sla_profesional(kpis, disp)

    st.markdown("---")

    # ─── ALERTAS DETECTADAS ───────────────────────────────────
    st.markdown("### 🚨 Alertas Detectadas")
    criticos = sum(1 for a in alertas if a["nivel"] == "CRÍTICO")

    r1, r2, r3, r4 = st.columns(4)
    with r1:
        st.metric("SLA Actual", f"{kpis['sla_global']:.2f}%",
                  delta=f"{kpis['sla_global']-99.9:+.2f}% vs ANS",
                  delta_color="normal" if kpis['sla_global'] >= 99.9 else "inverse")
    with r2:
        st.metric("Timeouts", f"{kpis['pct_timeout']:.2f}%",
                  delta=f"{kpis['total_timeouts']:,} eventos")
    with r3:
        st.metric("Error Técnico", f"{kpis['pct_error']:.2f}%",
                  delta=f"{kpis['total_fallas']:,} fallas")
    with r4:
        st.metric("Alertas Activas", len(alertas),
                  delta=f"{criticos} críticas" if criticos else "Sin críticas")

    st.markdown("<div style='margin-top:12px;'>", unsafe_allow_html=True)
    if not alertas:
        st.markdown(
            "<div style='background:#DCFCE7;border-radius:10px;padding:16px;border-left:5px solid #166534;'>"
            "<strong style='color:#166534;'>✅ Sin alertas activas</strong> — "
            "<span style='color:#555;'>La operación está dentro de los umbrales definidos.</span>"
            "</div>", unsafe_allow_html=True)
    else:
        for idx, alerta in enumerate(alertas):
            nivel   = alerta["nivel"]
            icono   = _icono_nivel(nivel)
            css_cls = "alerta-critico" if nivel == "CRÍTICO" else "alerta-serio"
            st.markdown(
                f"<div class='{css_cls}'>"
                f"<strong>{icono} [{nivel}]</strong> &nbsp;"
                f"<strong>{alerta['titulo']}</strong><br>"
                f"<span style='font-size:13px;color:#555;'>{alerta['descripcion']}</span><br>"
                f"<span style='font-size:11px;color:#888;'>Detectado: {alerta['timestamp']}</span>"
                f"</div>", unsafe_allow_html=True)

            col_t, col_j, col_sp = st.columns([1, 1, 6])
            with col_t:
                if st.button(f"📣 Teams", key=f"teams_{idx}"):
                    with st.spinner("Enviando..."):
                        res = enviar_alerta_teams(alerta, operador, kpis)
                    st.success(res["msg"]) if res["ok"] else st.warning(res["msg"])
            with col_j:
                if nivel == "CRÍTICO" and st.button(f"🎫 JIRA", key=f"jira_{idx}"):
                    with st.spinner("Creando ticket..."):
                        res = crear_ticket_jira(alerta, operador, kpis)
                    if res["ok"]:
                        st.success(res["msg"])
                        if res.get("url"):
                            st.markdown(f"[🔗 Ver ticket {res['key']}]({res['url']})")
                    else:
                        st.warning(res["msg"])
            st.markdown("")

        st.markdown("### ⚡ Acciones Masivas")
        cm1, cm2 = st.columns(2)
        with cm1:
            if st.button("📣 Notificar TODAS a Teams", type="primary"):
                for a in alertas:
                    res = enviar_alerta_teams(a, operador, kpis)
                    st.write(f"{'✅' if res['ok'] else '❌'} {res['msg']}")
        with cm2:
            criticas = [a for a in alertas if a["nivel"] == "CRÍTICO"]
            if criticas and st.button(f"🎫 Crear {len(criticas)} tickets JIRA", type="primary"):
                for a in criticas:
                    res = crear_ticket_jira(a, operador, kpis)
                    msg = f"{'✅' if res['ok'] else '❌'} {res['msg']}"
                    if res.get("url"):
                        msg += f" — [{res['key']}]({res['url']})"
                    st.markdown(msg)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # ─── GRÁFICA FALLAS EN EL TIEMPO ──────────────────────────
    _render_fallas_tiempo(df, kpis)

    st.markdown("---")

    # ─── MAPA DE CALOR Y FRANJA HORARIA ───────────────────────
    _render_franja_horaria(df)