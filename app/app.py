"""
app.py — Punto de entrada del Portal NOC ATP
"""
import streamlit as st
import os
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(
    page_title="Portal NOC — ATP Fiber Colombia",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS GLOBAL ────────────────────────────────────────────────
st.markdown("""
<style>
/* Sidebar */
[data-testid="stSidebar"] { background-color: #1a1a2e; }
[data-testid="stSidebar"] * { color: rgba(255,255,255,0.85) !important; }
[data-testid="stSidebar"] .stRadio label { color: rgba(255,255,255,0.75) !important; }

/* Forzar fondo blanco al logo para que se vea bien en sidebar oscuro */
[data-testid="stSidebar"] img {
    background-color: white !important;
    border-radius: 8px !important;
    padding: 6px !important;
}

/* Alertas personalizadas */
.alerta-critico {
    background: #FEF2F2; border-left: 4px solid #C0392B;
    padding: 10px 14px; border-radius: 6px; margin-bottom: 8px;
}
.alerta-serio {
    background: #FFFBEB; border-left: 4px solid #E67E22;
    padding: 10px 14px; border-radius: 6px; margin-bottom: 8px;
}
.alerta-ok {
    background: #F0FDF4; border-left: 4px solid #1D9E75;
    padding: 10px 14px; border-radius: 6px; margin-bottom: 8px;
}

/* KPI cards */
[data-testid="stMetric"] {
    background: white;
    border-radius: 8px;
    padding: 12px 16px;
    border: 0.5px solid #e0e0e0;
}

/* Ocultar menú Streamlit */
#MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    # Logo ATP real
    logo_path = os.path.join(os.path.dirname(__file__), "ATP_logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=160)
    else:
        st.markdown("""
        <div style="display:flex;align-items:center;gap:10px;padding:4px 0 16px;">
            <div>
                <div style="font-size:13px;font-weight:600;color:white;">Portal NOC</div>
                <div style="font-size:10px;color:rgba(255,255,255,0.4);">ATP Fiber Colombia</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color:rgba(255,255,255,0.1);margin:12px 0;'>", unsafe_allow_html=True)

    st.markdown(
        "<div style='font-size:9px;color:rgba(255,255,255,0.3);letter-spacing:1px;"
        "text-transform:uppercase;margin-bottom:6px;'>Navegación</div>",
        unsafe_allow_html=True
    )

    pagina = st.radio(
        "página",
        [
            "📊 Dashboard KPIs",
            "🚨 Alertas & Monitoreo",
            "📄 Reportes Ejecutivos",
            "⏱ Histórico Timeouts",       # ← NUEVA SECCIÓN
        ],
        label_visibility="collapsed"
    )

    # Badge contador de timeouts en sidebar
    from modules.timeout_history import leer_historico
    df_hist = leer_historico()
    total_hist = len(df_hist)
    if total_hist > 0:
        st.markdown(
            f"<div style='background:rgba(192,57,43,0.15);border:1px solid rgba(192,57,43,0.3);"
            f"border-radius:6px;padding:6px 10px;margin-top:4px;font-size:11px;"
            f"color:#ff6b6b;text-align:center;'>"
            f"⏱ <b>{total_hist:,}</b> timeouts registrados"
            f"</div>",
            unsafe_allow_html=True
        )

    st.markdown("<hr style='border-color:rgba(255,255,255,0.1);margin:12px 0;'>", unsafe_allow_html=True)

    # Estado del túnel
    st.markdown(
        "<div style='font-size:9px;color:rgba(255,255,255,0.3);letter-spacing:1px;"
        "text-transform:uppercase;margin-bottom:6px;'>Conexión</div>",
        unsafe_allow_html=True
    )

    if st.button("🔌 Verificar Túnel", use_container_width=True):
        from modules.kibana_client import verificar_conexion
        with st.spinner("Verificando..."):
            cx = verificar_conexion()
        if cx["ok"]:
            st.success(cx["msg"])
        else:
            st.error(cx["msg"])

    st.markdown(
        "<br><div style='font-size:9px;color:rgba(255,255,255,0.2);text-align:center;'>"
        "Portal NOC v1.0 · Gerencia Fibra</div>",
        unsafe_allow_html=True
    )

# ─── ENRUTADOR ─────────────────────────────────────────────────
if "Dashboard" in pagina:
    from pages.dashboard import render
    render()
elif "Alertas" in pagina:
    from pages.alertas import render
    render()
elif "Reportes" in pagina:
    from pages.reportes import render
    render()
elif "Histórico" in pagina:
    from pages.historico_timeouts import render
    render()