"""
app.py — Landing page del Portal NOC ATP
"""
import streamlit as st
import streamlit.components.v1 as components
import os
import base64
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(
    page_title="Portal NOC ATP — Fiber Colombia",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* Sidebar azul oscuro */
[data-testid="stSidebar"] { background-color: #1a1a2e; }
[data-testid="stSidebar"] * { color: rgba(255,255,255,0.85) !important; }
[data-testid="stSidebar"] img {
    background-color: #1a1a2e !important;
    border-radius: 8px !important;
    padding: 6px !important;
}
/* Ocultar nombre de pagina/archivo y menu default de Streamlit */
[data-testid="stSidebarNav"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }

.alerta-critico { background:#FEF2F2;border-left:4px solid #C0392B;padding:10px 14px;border-radius:6px;margin-bottom:8px; }
.alerta-serio   { background:#FFFBEB;border-left:4px solid #E67E22;padding:10px 14px;border-radius:6px;margin-bottom:8px; }
[data-testid="stMetric"] { background:white;border-radius:8px;padding:12px 16px;border:0.5px solid #e0e0e0; }

.nav-card {
    background: white;
    border-radius: 18px;
    padding: 28px 24px 20px 24px;
    border: 1px solid #f0f0f0;
    box-shadow: 0 4px 20px rgba(0,0,0,0.07);
    display: flex;
    flex-direction: column;
    min-height: 240px;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    cursor: pointer;
}
.nav-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 32px rgba(0,0,0,0.13);
}
.nav-card-icon {
    font-size: 38px;
    margin-bottom: 14px;
    display: block;
    background: #f5f6ff;
    width: 62px; height: 62px;
    line-height: 62px;
    text-align: center;
    border-radius: 16px;
}
.nav-card-title { font-size: 16px; font-weight: 700; color: #1a1a2e; margin-bottom: 8px; }
.nav-card-desc  { font-size: 12.5px; color: #999; line-height: 1.6; flex-grow: 1; }
.nav-card-arrow {
    margin-top: 18px;
    font-size: 12px;
    color: #3C3489;
    font-weight: 700;
    letter-spacing: 0.3px;
    border-top: 1px solid #f3f3f3;
    padding-top: 12px;
}

/* Encabezado Portal NOC ATP */
.portal-header {
    background: #1a1a2e;
    color: white;
    padding: 10px 22px;
    border-radius: 8px;
    margin-bottom: 16px;
    font-weight: 700;
    font-size: 14px;
    letter-spacing: 1px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.portal-header .h-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #e74c3c;
    box-shadow: 0 0 8px #e74c3c;
}
</style>
""", unsafe_allow_html=True)

# Encabezado superior "Portal NOC ATP"
st.markdown(
    "<div class='portal-header'><span class='h-dot'></span>"
    "PORTAL NOC ATP · FIBER COLOMBIA</div>",
    unsafe_allow_html=True
)

# ─── SIDEBAR (sin menu de navegacion, solo logo + tunel) ───────
with st.sidebar:
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "ATP_logo.png")
    st.markdown(
        "<div style='background:#1a1a2e;border-radius:10px;padding:10px 8px;"
        "margin-bottom:4px;text-align:center;'>",
        unsafe_allow_html=True
    )
    if os.path.exists(logo_path):
        st.image(logo_path, width=150)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        "<hr style='border-color:rgba(255,255,255,0.1);margin:10px 0;'>",
        unsafe_allow_html=True
    )

    from modules.timeout_history import leer_historico
    from datetime import datetime
    df_hist = leer_historico()
    total_hist = len(df_hist)

    st.markdown(
        "<div style='font-size:9px;color:rgba(255,255,255,0.3);letter-spacing:1px;"
        "text-transform:uppercase;margin-bottom:6px;'>Conexion</div>",
        unsafe_allow_html=True
    )
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
        st.markdown(
            f"<div style='background:{bg};border-radius:6px;padding:6px 8px;"
            f"font-size:11px;color:{color};text-align:center;margin-top:4px;'>"
            f"{msg}</div>", unsafe_allow_html=True
        )

    st.markdown(
        "<br><div style='font-size:9px;color:rgba(255,255,255,0.2);text-align:center;'>"
        "Portal NOC v1.0 · Gerencia Fibra</div>",
        unsafe_allow_html=True
    )

# ─── HERO CARRUSEL ─────────────────────────────────────────────
carrusel_html = """
<!DOCTYPE html>
<html>
<head>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: transparent; font-family: 'Inter', sans-serif; overflow: hidden; }
  .carousel {
    position: relative; width: 100%; height: 360px;
    border-radius: 16px; overflow: hidden;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    box-shadow: 0 20px 50px -12px rgba(0,0,0,0.5);
  }
  .carousel::before {
    content: ''; position: absolute; inset: 0;
    background:
      radial-gradient(600px 300px at 90% 10%, rgba(231,76,60,0.15), transparent 60%),
      radial-gradient(500px 250px at 10% 90%, rgba(76,243,255,0.06), transparent 60%);
    pointer-events: none; z-index: 1;
  }
  .carousel::after {
    content: ''; position: absolute; inset: 0;
    background-image:
      linear-gradient(rgba(120,130,180,0.05) 1px, transparent 1px),
      linear-gradient(90deg, rgba(120,130,180,0.05) 1px, transparent 1px);
    background-size: 40px 40px;
    mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%);
    pointer-events: none; z-index: 1;
  }
  .slide {
    position: absolute; inset: 0;
    padding: 44px 56px;
    display: flex; flex-direction: column; justify-content: center;
    opacity: 0; visibility: hidden;
    transform: translateX(40px);
    transition: opacity 0.7s ease, transform 0.7s cubic-bezier(0.2,0.7,0.2,1);
    z-index: 2;
  }
  .slide.active { opacity: 1; visibility: visible; transform: translateX(0); }
  .tag {
    display: inline-flex; align-items: center; gap: 8px;
    background: rgba(192,57,43,0.2);
    border: 1px solid rgba(192,57,43,0.4);
    color: #ff6b6b;
    font-size: 11px; font-weight: 700;
    letter-spacing: 2px; text-transform: uppercase;
    padding: 5px 14px; border-radius: 20px;
    width: fit-content; margin-bottom: 18px;
  }
  .tag.purple { background: rgba(60,52,137,0.25); border-color: rgba(120,110,220,0.5); color: #b8aff5; }
  .tag.green  { background: rgba(29,158,117,0.2); border-color: rgba(29,158,117,0.5); color: #6ee7b7; }
  .tag.amber  { background: rgba(230,126,34,0.2); border-color: rgba(230,126,34,0.5); color: #ffb547; }
  .tag .dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: currentColor;
    animation: pulse 1.6s infinite;
  }
  @keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(255,107,107,0.6); }
    100% { box-shadow: 0 0 0 12px rgba(255,107,107,0); }
  }
  .slide h2 {
    font-size: 42px; font-weight: 800; color: white;
    line-height: 1.1; margin-bottom: 14px;
    letter-spacing: -0.02em;
  }
  .slide h2 .red { color: #e74c3c; }
  .slide h2 .purple { color: #8b80f5; }
  .slide h2 .green { color: #4ade80; }
  .slide h2 .amber { color: #ffb547; }
  .slide .desc {
    font-size: 16px; color: rgba(255,255,255,0.7);
    max-width: 540px; line-height: 1.6;
  }
  .s-hero .visual {
    position: absolute; right: 60px; top: 50%;
    transform: translateY(-50%);
    width: 240px; height: 240px;
  }
  .radar-ring {
    position: absolute; top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    border-radius: 50%;
    border: 1px solid rgba(231,76,60,0.2);
  }
  .radar-ring.r1 { width: 80px; height: 80px; }
  .radar-ring.r2 { width: 150px; height: 150px; border-color: rgba(231,76,60,0.13); }
  .radar-ring.r3 { width: 220px; height: 220px; border-color: rgba(231,76,60,0.07); }
  .radar-core {
    position: absolute; top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    width: 12px; height: 12px; border-radius: 50%;
    background: #e74c3c;
    box-shadow: 0 0 25px #e74c3c, 0 0 50px rgba(231,76,60,0.5);
  }
  .radar-sweep {
    position: absolute; top: 50%; left: 50%;
    width: 220px; height: 220px;
    transform: translate(-50%, -50%);
    background: conic-gradient(from 0deg, transparent 0deg, rgba(231,76,60,0.4) 30deg, transparent 60deg);
    border-radius: 50%;
    animation: sweep 4s linear infinite;
  }
  @keyframes sweep { to { transform: translate(-50%, -50%) rotate(360deg); } }
  .module-icon {
    position: absolute; right: 70px; top: 50%;
    transform: translateY(-50%);
    width: 200px; height: 200px;
    border-radius: 32px;
    display: flex; align-items: center; justify-content: center;
    font-size: 100px;
    box-shadow: 0 20px 60px -15px rgba(0,0,0,0.5);
    backdrop-filter: blur(10px);
  }
  .module-icon.dash {
    background: linear-gradient(135deg, rgba(60,52,137,0.4), rgba(60,52,137,0.15));
    border: 1px solid rgba(139,128,245,0.4);
  }
  .module-icon.alert {
    background: linear-gradient(135deg, rgba(192,57,43,0.4), rgba(192,57,43,0.15));
    border: 1px solid rgba(231,76,60,0.4);
    animation: shake 4s ease-in-out infinite;
  }
  @keyframes shake {
    0%, 90%, 100% { transform: translateY(-50%) rotate(0); }
    92% { transform: translateY(-50%) rotate(-8deg); }
    94% { transform: translateY(-50%) rotate(8deg); }
    96% { transform: translateY(-50%) rotate(-5deg); }
    98% { transform: translateY(-50%) rotate(5deg); }
  }
  .module-icon.report {
    background: linear-gradient(135deg, rgba(29,158,117,0.4), rgba(29,158,117,0.15));
    border: 1px solid rgba(74,222,128,0.4);
  }
  .module-icon.history {
    background: linear-gradient(135deg, rgba(230,126,34,0.4), rgba(230,126,34,0.15));
    border: 1px solid rgba(255,181,71,0.4);
  }
  .features {
    margin-top: 18px; display: flex; flex-direction: column; gap: 8px;
    max-width: 540px;
  }
  .feature {
    display: flex; align-items: center; gap: 10px;
    font-size: 13px; color: rgba(255,255,255,0.75);
    font-family: 'JetBrains Mono', monospace;
  }
  .feature::before { content: '▸'; color: #e74c3c; font-size: 14px; }
  .feature.purple::before { color: #8b80f5; }
  .feature.green::before { color: #4ade80; }
  .feature.amber::before { color: #ffb547; }
  .big-stat {
    margin-top: 14px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px; color: rgba(255,255,255,0.5);
    letter-spacing: 2px; text-transform: uppercase;
  }
  .big-stat .num {
    font-family: 'Inter', sans-serif;
    font-size: 56px; font-weight: 800;
    color: #ffb547; letter-spacing: -0.03em;
    display: block; line-height: 1; margin-top: 4px;
  }
  .nav-arrow {
    position: absolute; top: 50%;
    transform: translateY(-50%);
    width: 40px; height: 40px; border-radius: 50%;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    backdrop-filter: blur(10px);
    color: white; font-size: 18px;
    cursor: pointer; z-index: 10;
    display: flex; align-items: center; justify-content: center;
    transition: all 0.2s;
  }
  .nav-arrow:hover {
    background: rgba(231,76,60,0.3);
    border-color: rgba(231,76,60,0.5);
    transform: translateY(-50%) scale(1.08);
  }
  .nav-arrow.prev { left: 16px; }
  .nav-arrow.next { right: 16px; }
  .dots {
    position: absolute; bottom: 18px;
    left: 50%; transform: translateX(-50%);
    display: flex; gap: 8px; z-index: 10;
  }
  .dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: rgba(255,255,255,0.25);
    border: none; cursor: pointer;
    transition: all 0.3s; padding: 0;
  }
  .dot.active {
    width: 26px; border-radius: 4px;
    background: #e74c3c;
    box-shadow: 0 0 10px rgba(231,76,60,0.6);
  }
  .progress {
    position: absolute; bottom: 0; left: 0;
    height: 2px;
    background: linear-gradient(90deg, #e74c3c, #ff6b6b);
    width: 0%; z-index: 10;
    transition: width 0.1s linear;
  }
  .counter {
    position: absolute; top: 20px; right: 24px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px; letter-spacing: 2px;
    color: rgba(255,255,255,0.4); z-index: 10;
  }
  .counter .cur { color: #e74c3c; }
</style>
</head>
<body>
<div class="carousel" id="carousel">
  <div class="counter"><span class="cur" id="cur">01</span> / 05</div>

  <div class="slide s-hero active">
    <div class="tag"><span class="dot"></span>Sistema activo — Andean Telecom Partners</div>
    <h2>Portal NOC<br><span class="red">ATP Fiber Colombia</span></h2>
    <p class="desc">Centro de operaciones de red en tiempo real. Monitoreo de transacciones, alertas automáticas y reportes ejecutivos para la Gerencia de Fibra.</p>
    <div class="visual">
      <div class="radar-ring r3"></div>
      <div class="radar-ring r2"></div>
      <div class="radar-ring r1"></div>
      <div class="radar-sweep"></div>
      <div class="radar-core"></div>
    </div>
  </div>

  <div class="slide s-dash">
    <div class="tag purple"><span class="dot"></span>Módulo · Dashboard KPIs</div>
    <h2>Dashboard <span class="purple">KPIs</span></h2>
    <p class="desc">Métricas en tiempo real de transacciones CLARO y ETB. Visualización de SLA, timeouts, errores técnicos y tendencias operativas.</p>
    <div class="features">
      <div class="feature purple">SLA por operador en tiempo real</div>
      <div class="feature purple">Análisis de timeouts y errores técnicos</div>
      <div class="feature purple">Tendencias horarias y comparativas</div>
    </div>
    <div class="module-icon dash">📊</div>
  </div>

  <div class="slide s-alert">
    <div class="tag"><span class="dot"></span>Módulo · Alertas & Monitoreo</div>
    <h2>Alertas & <span class="red">Monitoreo</span></h2>
    <p class="desc">Monitor automático de timeouts 24/7. Sistema de alertas por correo al equipo NOC cuando se supera el umbral establecido.</p>
    <div class="features">
      <div class="feature">Vigilancia continua 24/7</div>
      <div class="feature">Notificaciones automáticas al NOC</div>
      <div class="feature">Umbrales configurables por operador</div>
    </div>
    <div class="module-icon alert">🚨</div>
  </div>

  <div class="slide s-report">
    <div class="tag green"><span class="dot"></span>Módulo · Reportes Ejecutivos</div>
    <h2>Reportes <span class="green">Ejecutivos</span></h2>
    <p class="desc">Generación de reportes PDF y Excel para presentaciones a gerencia y seguimiento de ANS contractual con CLARO y ETB.</p>
    <div class="features">
      <div class="feature green">Exportación a PDF y Excel</div>
      <div class="feature green">Reportes ejecutivos para gerencia</div>
      <div class="feature green">Seguimiento de ANS contractual</div>
    </div>
    <div class="module-icon report">📄</div>
  </div>

  <div class="slide s-history">
    <div class="tag amber"><span class="dot"></span>Módulo · Histórico Timeouts</div>
    <h2>Histórico <span class="amber">Timeouts</span></h2>
    <p class="desc">Registro histórico completo de todos los timeouts detectados. Análisis de patrones y exportación de datos para auditorías.</p>
    <div class="big-stat">
      Timeouts registrados
      <span class="num">__TOTAL_HIST__</span>
    </div>
    <div class="module-icon history">⏱</div>
  </div>

  <button class="nav-arrow prev" onclick="go(-1)">‹</button>
  <button class="nav-arrow next" onclick="go(1)">›</button>
  <div class="dots">
    <button class="dot active" onclick="goTo(0)"></button>
    <button class="dot" onclick="goTo(1)"></button>
    <button class="dot" onclick="goTo(2)"></button>
    <button class="dot" onclick="goTo(3)"></button>
    <button class="dot" onclick="goTo(4)"></button>
  </div>
  <div class="progress" id="progress"></div>
</div>
<script>
  const slides = document.querySelectorAll('.slide');
  const dots = document.querySelectorAll('.dot');
  const carousel = document.getElementById('carousel');
  const progress = document.getElementById('progress');
  const cur = document.getElementById('cur');
  let idx = 0;
  const total = slides.length;
  const DUR = 6000;
  let start = Date.now();
  let paused = false;
  function render() {
    slides.forEach((s, i) => s.classList.toggle('active', i === idx));
    dots.forEach((d, i) => d.classList.toggle('active', i === idx));
    cur.textContent = String(idx + 1).padStart(2, '0');
    start = Date.now();
  }
  function go(delta) { idx = (idx + delta + total) % total; render(); }
  function goTo(i) { idx = i; render(); }
  function tick() {
    if (!paused) {
      const elapsed = Date.now() - start;
      const pct = Math.min((elapsed / DUR) * 100, 100);
      progress.style.width = pct + '%';
      if (elapsed >= DUR) { go(1); progress.style.width = '0%'; }
    }
    requestAnimationFrame(tick);
  }
  carousel.addEventListener('mouseenter', () => { paused = true; });
  carousel.addEventListener('mouseleave', () => {
    paused = false;
    start = Date.now() - (parseFloat(progress.style.width || 0) / 100) * DUR;
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') go(-1);
    if (e.key === 'ArrowRight') go(1);
  });
  tick();
</script>
</body>
</html>
"""

carrusel_html = carrusel_html.replace("__TOTAL_HIST__", f"{total_hist:,}")
components.html(carrusel_html, height=380, scrolling=False)

# ─── LOGOS OPERADORES — BÚSQUEDA ROBUSTA EN MÚLTIPLES RUTAS ────
def _buscar_logo(nombre):
    """Busca el archivo de logo en varias rutas posibles."""
    _abs  = os.path.dirname(os.path.abspath(__file__))
    _rel  = os.path.dirname(__file__)
    _cwd  = os.getcwd()
    candidatos = [
        # mismo directorio que app.py
        os.path.join(_abs, nombre),
        os.path.join(_rel, nombre),
        # subcarpeta assets (más común en proyectos Streamlit)
        os.path.join(_abs,  "assets", nombre),
        os.path.join(_rel,  "assets", nombre),
        os.path.join(_cwd,  "assets", nombre),
        # subcarpeta images / static
        os.path.join(_abs,  "images", nombre),
        os.path.join(_abs,  "static", nombre),
        # directorio de trabajo actual
        os.path.join(_cwd,  nombre),
        nombre,
    ]
    for ruta in candidatos:
        try:
            if os.path.exists(ruta):
                return ruta
        except Exception:
            continue
    return None

def _img_b64(path, mime):
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{data}"

# SVG fallback solo si de verdad no se encuentran los archivos
_claro_fallback = """
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 200' width='80' height='80'>
  <circle cx='100' cy='100' r='80' fill='#C0392B'/>
  <text x='100' y='115' text-anchor='middle' font-family='Arial Black, sans-serif'
        font-size='42' font-weight='900' fill='white' font-style='italic'>claro</text>
</svg>
"""
_etb_fallback = """
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 200' width='80' height='80'>
  <circle cx='100' cy='100' r='80' fill='#1a6ab5'/>
  <text x='100' y='118' text-anchor='middle' font-family='Arial Black, sans-serif'
        font-size='52' font-weight='900' fill='white'>eTb</text>
</svg>
"""

_claro_path = _buscar_logo("claro.jpg")
_etb_path   = _buscar_logo("etb.png")



if _claro_path:
    claro_html = f"<img src='{_img_b64(_claro_path, 'image/jpeg')}' style='height:80px;object-fit:contain;display:block;margin:auto;'>"
else:
    claro_html = f"<div style='display:flex;justify-content:center;'>{_claro_fallback}</div>"

if _etb_path:
    etb_html = f"<img src='{_img_b64(_etb_path, 'image/png')}' style='height:80px;object-fit:contain;display:block;margin:auto;'>"
else:
    etb_html = f"<div style='display:flex;justify-content:center;'>{_etb_fallback}</div>"

st.markdown(f"""
<div style='display:flex;gap:32px;align-items:center;margin:8px 0 28px 0;flex-wrap:wrap;'>
    <div style='background:white;border-radius:16px;padding:20px 40px;
                box-shadow:0 4px 16px rgba(0,0,0,0.08);text-align:center;min-width:160px;'>
        {claro_html}
        <p style='color:#C0392B;font-weight:700;font-size:13px;margin:10px 0 0 0;
                  letter-spacing:1px;text-transform:uppercase;'>CLARO</p>
    </div>
    <div style='background:white;border-radius:16px;padding:20px 40px;
                box-shadow:0 4px 16px rgba(0,0,0,0.08);text-align:center;min-width:160px;'>
        {etb_html}
        <p style='color:#1a6ab5;font-weight:700;font-size:13px;margin:10px 0 0 0;
                  letter-spacing:1px;text-transform:uppercase;'>ETB</p>
    </div>
    <div style='color:#888;font-size:13px;'>
        <span style='font-size:22px;font-weight:800;color:#1a1a2e;'>{total_hist:,}</span>
        <span style='display:block;font-size:11px;color:#aaa;'>timeouts registrados</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("### 🧭 Accede a cada módulo")
st.caption("Haz clic en cualquier módulo para acceder directamente.")
st.markdown("<br>", unsafe_allow_html=True)

# ─── TARJETAS (CUBICULOS) ──────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)

cards = [
    (c1, "📊", "Dashboard KPIs",
     "Métricas en tiempo real de transacciones CLARO y ETB. SLA, timeouts, errores técnicos y tendencias.",
     "→ Ir al Dashboard", "btn_dash", "pages/dashboard.py", "📊 Abrir Dashboard",
     "#3C3489", "#EEEEFF"),
    (c2, "🚨", "Alertas & Monitoreo",
     "Monitor automático de timeouts 24/7. Alertas por correo al equipo NOC cuando se supera el umbral.",
     "→ Ir a Alertas", "btn_alert", "pages/alertas.py", "🚨 Abrir Alertas",
     "#C0392B", "#FFF0F0"),
    (c3, "📄", "Reportes Ejecutivos",
     "Generación de reportes PDF y Excel para presentaciones a gerencia y seguimiento de ANS contractual.",
     "→ Ir a Reportes", "btn_rep", "pages/reportes.py", "📄 Abrir Reportes",
     "#1D9E75", "#EDFAF5"),
    (c4, "⏱", "Histórico Timeouts",
     "Registro histórico de todos los timeouts detectados. Análisis de patrones y exportación de datos.",
     "→ Ir al Histórico", "btn_hist", "pages/historico_timeouts.py", "⏱ Abrir Histórico",
     "#E67E22", "#FFF8EE"),
]

for col, icon, title, desc, arrow, key, page, btn_label, color, bg in cards:
    with col:
        st.markdown(f"""
        <div class="nav-card" style="border-top: 4px solid {color};">
            <span class="nav-card-icon" style="background:{bg};">{icon}</span>
            <div class="nav-card-title">{title}</div>
            <div class="nav-card-desc">{desc}</div>
            <div class="nav-card-arrow" style="color:{color};">{arrow}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(btn_label, use_container_width=True, key=key):
            st.switch_page(page)

# ─── PIE ───────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align:center;font-size:12px;color:#bbb;padding:16px 0;'>"
    "Portal NOC ATP v1.0 · Andean Telecom Partners · Gerencia Fibra Colombia"
    "</div>", unsafe_allow_html=True
)