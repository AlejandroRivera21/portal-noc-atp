"""
app.py — Landing page del Portal NOC ATP
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

st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #1a1a2e; }
[data-testid="stSidebar"] * { color: rgba(255,255,255,0.85) !important; }
[data-testid="stSidebar"] button p { color: white !important; font-size: 13px !important; }
[data-testid="stSidebar"] button {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
}
[data-testid="stSidebar"] button:hover {
    background: rgba(255,255,255,0.12) !important;
}
[data-testid="stSidebar"] img {
    background-color: #1a1a2e !important;
    border-radius: 8px !important;
    padding: 6px !important;
}
[data-testid="stMetric"] { background:white;border-radius:8px;padding:12px 16px;border:0.5px solid #e0e0e0; }
#MainMenu, footer { visibility: hidden; }
.landing-hero {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 16px;
    padding: 56px 48px;
    margin-bottom: 32px;
}
.nav-card {
    background: white;
    border-radius: 14px;
    padding: 28px 24px;
    border: 1px solid #eee;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    min-height: 220px;
}
.nav-card-icon { font-size: 36px; margin-bottom: 14px; display: block; }
.nav-card-title { font-size: 17px; font-weight: 700; color: #1a1a2e; margin-bottom: 6px; }
.nav-card-desc  { font-size: 13px; color: #888; line-height: 1.5; }
.nav-card-arrow { margin-top: 16px; font-size: 12px; color: #3C3489; font-weight: 600; }
.logo-box {
    background: white;
    border-radius: 12px;
    padding: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    height: 120px;
}
</style>
""", unsafe_allow_html=True)

# ─── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    logo_path = os.path.join(os.path.dirname(__file__), "ATP_logo.png")
    st.markdown("<div style='background:#1a1a2e;border-radius:10px;padding:10px 8px;text-align:center;'>", unsafe_allow_html=True)
    if os.path.exists(logo_path):
        st.image(logo_path, width=150)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:rgba(255,255,255,0.1);margin:10px 0;'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:9px;color:rgba(255,255,255,0.3);letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;'>Navegacion</div>", unsafe_allow_html=True)

    pages = {
        "🏠 Inicio":              "app.py",
        "📊 Dashboard KPIs":      "pages/dashboard.py",
        "🚨 Alertas & Monitoreo": "pages/alertas.py",
        "📄 Reportes Ejecutivos": "pages/reportes.py",
        "⏱ Historico Timeouts":  "pages/historico_timeouts.py",
    }
    for label, path in pages.items():
        if st.button(label, use_container_width=True, key=f"app_nav_{label}"):
            st.switch_page(path)

    from modules.timeout_history import leer_historico
    from datetime import datetime
    df_hist = leer_historico()
    total_hist = len(df_hist)
    if total_hist > 0:
        st.markdown(
            f"<div style='background:rgba(192,57,43,0.15);border:1px solid rgba(192,57,43,0.3);"
            f"border-radius:6px;padding:6px 10px;margin-top:8px;font-size:11px;"
            f"color:#ff6b6b;text-align:center;'>⏱ <b>{total_hist:,}</b> timeouts registrados</div>",
            unsafe_allow_html=True
        )

    st.markdown("<hr style='border-color:rgba(255,255,255,0.1);margin:12px 0;'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:9px;color:rgba(255,255,255,0.3);letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;'>Conexion</div>", unsafe_allow_html=True)

    if st.button("🔌 Verificar Tunel", use_container_width=True, key="app_tunel"):
        from modules.kibana_client import verificar_conexion
        with st.spinner("Verificando..."):
            cx = verificar_conexion()
        ahora = datetime.now().strftime("%H:%M:%S")
        if cx["ok"]:
            st.session_state["tunel_msg"] = ("ok", f"✅ Conectado ({ahora})")
        else:
            st.session_state["tunel_msg"] = ("err", f"❌ Sin conexion ({ahora})")

    if "tunel_msg" in st.session_state:
        tipo, msg = st.session_state["tunel_msg"]
        color = "#1D9E75" if tipo == "ok" else "#C0392B"
        bg    = "rgba(29,158,117,0.1)" if tipo == "ok" else "rgba(192,57,43,0.1)"
        st.markdown(f"<div style='background:{bg};border-radius:6px;padding:6px 8px;font-size:11px;color:{color};text-align:center;margin-top:4px;'>{msg}</div>", unsafe_allow_html=True)

    st.markdown("<br><div style='font-size:9px;color:rgba(255,255,255,0.2);text-align:center;'>Portal NOC v1.0 · Gerencia Fibra</div>", unsafe_allow_html=True)

# ─── HERO ──────────────────────────────────────────────────────
st.markdown("""
<div class="landing-hero">
    <div style='display:inline-block;background:rgba(192,57,43,0.2);border:1px solid rgba(192,57,43,0.4);
    color:#ff6b6b;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;
    padding:4px 12px;border-radius:20px;margin-bottom:16px;'>🔴 Sistema Activo — Andean Telecom Partners</div>
    <div style='font-size:40px;font-weight:800;color:white;line-height:1.15;margin-bottom:12px;'>
        Portal NOC<br><span style='color:#e74c3c;'>ATP Fiber Colombia</span>
    </div>
    <div style='font-size:16px;color:rgba(255,255,255,0.6);max-width:500px;line-height:1.6;'>
        Centro de operaciones de red en tiempo real. Monitoreo de transacciones,
        alertas automáticas y reportes ejecutivos para la Gerencia de Fibra.
    </div>
</div>
""", unsafe_allow_html=True)

# ─── LOGOS OPERADORES ──────────────────────────────────────────
st.markdown("### 📡 Operadores monitoreados")
col_claro, col_etb, col_space = st.columns([1, 1, 2])
with col_claro:
    claro_path = os.path.join(os.path.dirname(__file__), "claro.jpg")
    if os.path.exists(claro_path):
        st.markdown("<div class='logo-box'>", unsafe_allow_html=True)
        st.image(claro_path, width=160)
        st.markdown("</div>", unsafe_allow_html=True)
with col_etb:
    etb_path = os.path.join(os.path.dirname(__file__), "etb.png")
    if os.path.exists(etb_path):
        st.markdown("<div class='logo-box'>", unsafe_allow_html=True)
        st.image(etb_path, width=140)
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("### 🧭 Accede a cada módulo")
st.caption("Usa el menú lateral o haz clic en cualquier módulo para navegar directamente.")
st.markdown("<br>", unsafe_allow_html=True)

# ─── TARJETAS ──────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)

cards = [
    (c1, "📊", "Dashboard KPIs",
     "Métricas en tiempo real de transacciones CLARO y ETB. SLA, timeouts, errores técnicos y tendencias.",
     "→ Ir al Dashboard", "btn_dash", "pages/dashboard.py", "📊 Abrir Dashboard"),
    (c2, "🚨", "Alertas & Monitoreo",
     "Monitor automático de timeouts 24/7. Alertas por correo al equipo NOC cuando se supera el umbral.",
     "→ Ir a Alertas", "btn_alert", "pages/alertas.py", "🚨 Abrir Alertas"),
    (c3, "📄", "Reportes Ejecutivos",
     "Generación de reportes para presentaciones a gerencia y seguimiento de ANS contractual.",
     "→ Ir a Reportes", "btn_rep", "pages/reportes.py", "📄 Abrir Reportes"),
    (c4, "⏱", "Histórico Timeouts",
     "Registro histórico de todos los timeouts detectados. Análisis de patrones y exportación de datos.",
     "→ Ir al Histórico", "btn_hist", "pages/historico_timeouts.py", "⏱ Abrir Histórico"),
]

for col, icon, title, desc, arrow, key, page, btn_label in cards:
    with col:
        st.markdown(f"""
        <div class="nav-card">
            <span class="nav-card-icon">{icon}</span>
            <div class="nav-card-title">{title}</div>
            <div class="nav-card-desc">{desc}</div>
            <div class="nav-card-arrow">{arrow}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(btn_label, use_container_width=True, key=key):
            st.switch_page(page)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align:center;font-size:12px;color:#bbb;padding:16px 0;'>"
    "Portal NOC v1.0 · Andean Telecom Partners · Gerencia Fibra Colombia"
    "</div>", unsafe_allow_html=True
)