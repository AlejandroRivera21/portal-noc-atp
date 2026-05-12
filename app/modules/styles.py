"""
modules/styles.py
CSS global + sidebar compartido para TODAS las paginas del Portal NOC ATP.

USO en cada pagina (dashboard.py, alertas.py, reportes.py, historico_timeouts.py):

    import streamlit as st
    st.set_page_config(
        page_title="Portal NOC ATP — Dashboard KPIs",   # <-- ajusta el nombre
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    from modules.styles import sidebar_comun
    sidebar_comun(mostrar_timeouts=False)   # True solo en historico_timeouts.py

    # ... resto de tu codigo intacto
"""
import streamlit as st
import os
from datetime import datetime


def aplicar_estilos():
    """CSS global: sidebar azul, ocultar menu nativo, cajas de alerta."""
    st.markdown("""
    <style>
    /* Sidebar azul oscuro en TODAS las paginas */
    [data-testid="stSidebar"] { background-color: #1a1a2e; }
    [data-testid="stSidebar"] * { color: rgba(255,255,255,0.85) !important; }
    [data-testid="stSidebar"] button p {
        color: white !important;
        font-size: 13px !important;
    }
    [data-testid="stSidebar"] button {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        text-align: left !important;
    }
    [data-testid="stSidebar"] button:hover {
        background: rgba(255,255,255,0.12) !important;
        border: 1px solid rgba(255,255,255,0.25) !important;
    }
    [data-testid="stSidebar"] img {
        background-color: #1a1a2e !important;
        border-radius: 8px !important;
        padding: 6px !important;
    }

    /* OCULTAR el menu de navegacion automatico de Streamlit
       (los nombres de archivo: app, alertas, dashboard, etc.) */
    [data-testid="stSidebarNav"] { display: none !important; }
    div[data-testid="stSidebarNav"] { display: none !important; }
    section[data-testid="stSidebar"] > div:first-child > div:first-child > div:nth-child(1) ul {
        display: none !important;
    }

    header[data-testid="stHeader"] { background: transparent; }
    #MainMenu, footer { visibility: hidden; }

    /* Cajas de alertas */
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
    [data-testid="stMetric"] {
        background: white;
        border-radius: 8px;
        padding: 12px 16px;
        border: 0.5px solid #e0e0e0;
    }
    [data-testid="stSidebar"] [data-testid="baseButton-primary"] {
        background: rgba(220,38,38,0.12) !important;
        border: 1px solid rgba(220,38,38,0.45) !important;
        color: #f87171 !important;
    }
    [data-testid="stSidebar"] [data-testid="baseButton-primary"]:hover {
        background: rgba(220,38,38,0.28) !important;
        border-color: rgba(220,38,38,0.7) !important;
        color: #fca5a5 !important;
    }
    </style>
    """, unsafe_allow_html=True)


def sidebar_comun(mostrar_timeouts=False):
    """
    Sidebar compartido para TODAS las paginas.

    - Logo ATP
    - Botones de navegacion: Inicio, Dashboard, Alertas, Reportes, Historico
    - Badge timeouts SOLO si mostrar_timeouts=True (usar en historico_timeouts.py)
    - Boton Verificar Tunel (en TODAS las paginas)
    """
    aplicar_estilos()

    with st.sidebar:
        # ── Logo ATP con fondo azul oscuro ───────────────────────
        logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "ATPLOGIN.png")
        st.markdown(
            "<div style='background:#1a1a2e;border-radius:10px;"
            "padding:10px 8px;margin-bottom:4px;text-align:center;'>",
            unsafe_allow_html=True
        )
        if os.path.exists(logo_path):
            st.image(logo_path, width=150)
        else:
            st.markdown(
                "<div style='font-size:18px;font-weight:800;color:white;'>Portal NOC</div>"
                "<div style='font-size:11px;color:rgba(255,255,255,0.4);'>ATP Fiber Colombia</div>",
                unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            "<hr style='border-color:rgba(255,255,255,0.1);margin:10px 0;'>",
            unsafe_allow_html=True
        )

        # ── Navegacion ──────────────────────────────────────────
        st.markdown(
            "<div style='font-size:9px;color:rgba(255,255,255,0.3);letter-spacing:1px;"
            "text-transform:uppercase;margin-bottom:8px;'>Navegacion</div>",
            unsafe_allow_html=True
        )

        pages = {
            "🏠 Inicio":              "app.py",
            "📊 Dashboard KPIs":      "pages/dashboard.py",
            "🚨 Alertas & Monitoreo": "pages/alertas.py",
            "📄 Reportes Ejecutivos": "pages/reportes.py",
            "⏱ Historico Timeouts":  "pages/historico_timeouts.py",
        }
        for label, path in pages.items():
            if st.button(label, use_container_width=True, key=f"nav_{label}"):
                st.switch_page(path)

        # ── Badge timeouts SOLO en historico_timeouts ────────────
        if mostrar_timeouts:
            try:
                from modules.timeout_history import leer_historico
                df_hist = leer_historico()
                total_hist = len(df_hist)
                if total_hist > 0:
                    st.markdown(
                        f"<div style='background:rgba(192,57,43,0.15);"
                        f"border:1px solid rgba(192,57,43,0.3);"
                        f"border-radius:6px;padding:6px 10px;margin-top:8px;"
                        f"font-size:11px;color:#ff6b6b;text-align:center;'>"
                        f"⏱ <b>{total_hist:,}</b> timeouts registrados"
                        f"</div>",
                        unsafe_allow_html=True
                    )
            except Exception:
                pass

        st.markdown(
            "<hr style='border-color:rgba(255,255,255,0.1);margin:12px 0;'>",
            unsafe_allow_html=True
        )

        # ── Verificar Tunel (en TODAS las paginas) ───────────────
        st.markdown(
            "<div style='font-size:9px;color:rgba(255,255,255,0.3);letter-spacing:1px;"
            "text-transform:uppercase;margin-bottom:6px;'>Conexion</div>",
            unsafe_allow_html=True
        )

        if st.button("🔌 Verificar Tunel", use_container_width=True, key="nav_tunel"):
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
            st.markdown(
                f"<div style='background:{bg};border-radius:6px;padding:6px 8px;"
                f"font-size:11px;color:{color};text-align:center;margin-top:4px;'>"
                f"{msg}</div>",
                unsafe_allow_html=True
            )

        st.markdown(
            "<hr style='border-color:rgba(255,255,255,0.08);margin:16px 0 10px;'>",
            unsafe_allow_html=True
        )

        u   = st.session_state.get("nombre", st.session_state.get("usuario", ""))
        r   = st.session_state.get("rol", "")
        ini = "".join([w[0].upper() for w in u.replace("_", " ").split()[:2]]) if u else "?"

        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;padding:4px 2px 8px;'>"
            f"<div style='width:34px;height:34px;border-radius:50%;"
            f"background:rgba(220,38,38,0.15);border:1px solid rgba(220,38,38,0.3);"
            f"display:flex;align-items:center;justify-content:center;"
            f"font-size:13px;font-weight:700;color:#ef4444;flex-shrink:0;'>{ini}</div>"
            f"<div>"
            f"<div style='font-size:12px;font-weight:600;color:rgba(255,255,255,0.85);'>{u}</div>"
            f"<div style='font-size:10px;color:rgba(255,255,255,0.3);letter-spacing:0.5px;'>{r}</div>"
            f"</div></div>",
            unsafe_allow_html=True
        )
        if st.button("⏻  Cerrar sesion", use_container_width=True, key="nav_logout", type="primary"):
            for k in ["autenticado", "usuario", "nombre", "rol", "user_id"]:
                st.session_state.pop(k, None)
            st.rerun()

        st.markdown(
            "<div style='font-size:9px;color:rgba(255,255,255,0.15);"
            "text-align:center;margin-top:6px;'>Portal NOC v1.0 · Gerencia Fibra</div>",
            unsafe_allow_html=True
        )