import base64, os

with open(os.path.join("assets", "ATPLOGIN.png"), "rb") as f:
    LOGO_B64 = base64.b64encode(f.read()).decode()

content = """import streamlit as st
import hashlib, hmac

USUARIOS = {
    "admin":   "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",
    "noc":     "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
    "gerencia":"ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f",
}
ROLES = {
    "admin":   "Administrador",
    "noc":     "Operador NOC",
    "gerencia":"Gerencia Fibra",
}

def _hash(p): return hashlib.sha256(p.encode()).hexdigest()
def hash_password(p): return _hash(p)
def _verificar(u, p):
    if u not in USUARIOS: return False
    return hmac.compare_digest(USUARIOS[u], _hash(p))

CSS = \"\"\"<style>
@import url(https://fonts.googleapis.com/css2?family=Rajdhani:wght@600;700&family=DM+Sans:wght@300;400;500&display=swap);
#MainMenu,footer,header{visibility:hidden}
.block-container{padding:0!important;max-width:100%!important}
section[data-testid="stSidebar"]{display:none!important}
.stApp{background:#060911;min-height:100vh}
.bg{position:fixed;inset:0;z-index:0;
  background:radial-gradient(ellipse 70% 50% at 50% 0%,rgba(180,20,20,.22) 0%,transparent 65%),
  radial-gradient(ellipse 50% 40% at 100% 100%,rgba(20,40,120,.18) 0%,transparent 60%),
  repeating-linear-gradient(0deg,transparent,transparent 60px,rgba(255,255,255,.012) 60px,rgba(255,255,255,.012) 61px),
  #060911}
.card{position:relative;z-index:1;width:420px;margin:0 auto;
  background:rgba(10,14,26,.96);border:1px solid rgba(255,255,255,.07);
  border-radius:20px;padding:44px 40px 36px;
  box-shadow:0 0 0 1px rgba(180,20,20,.12),0 50px 100px rgba(0,0,0,.7)}
.card::before{content:"";position:absolute;top:0;left:8%;right:8%;height:2px;border-radius:2px;
  background:linear-gradient(90deg,transparent,#dc2626 30%,#ef4444 50%,#dc2626 70%,transparent)}
.logo{text-align:center;margin-bottom:20px}
.logo img{width:190px;filter:drop-shadow(0 0 28px rgba(220,38,38,.4))}
.badge{display:flex;justify-content:center;margin-bottom:26px}
.badge span{display:inline-flex;align-items:center;gap:7px;
  background:rgba(220,38,38,.08);border:1px solid rgba(220,38,38,.2);
  border-radius:100px;padding:5px 16px;font-size:10px;letter-spacing:2px;
  color:#f87171;text-transform:uppercase;font-weight:600}
.dot{width:6px;height:6px;border-radius:50%;background:#dc2626;
  animation:blink 2s ease-in-out infinite;display:inline-block}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.4}}
div[data-testid="stTextInput"] input{
  background:rgba(255,255,255,.03)!important;border:1px solid rgba(255,255,255,.09)!important;
  border-radius:10px!important;color:#e2e8f0!important;font-size:14px!important;padding:12px 14px!important}
div[data-testid="stTextInput"] input:focus{
  border-color:rgba(220,38,38,.5)!important;box-shadow:0 0 0 3px rgba(220,38,38,.12)!important}
div[data-testid="stTextInput"] label{
  font-size:10px!important;font-weight:600!important;color:#475569!important;
  letter-spacing:1.5px!important;text-transform:uppercase!important}
div[data-testid="stButton"] button{
  width:100%!important;background:linear-gradient(135deg,#dc2626,#991b1b)!important;
  color:white!important;border:none!important;border-radius:10px!important;padding:13px!important;
  font-family:Rajdhani,sans-serif!important;font-size:14px!important;font-weight:700!important;
  letter-spacing:3px!important;text-transform:uppercase!important;margin-top:10px!important;
  box-shadow:0 8px 32px rgba(220,38,38,.4)!important}
div[data-testid="stButton"] button:hover{
  background:linear-gradient(135deg,#ef4444,#dc2626)!important;
  box-shadow:0 12px 40px rgba(220,38,38,.55)!important;transform:translateY(-1px)!important}
.foot{text-align:center;font-size:10px;color:#1e293b;margin-top:22px;letter-spacing:1px;text-transform:uppercase}
</style><div class="bg"></div>\"\"\"

LOGO_HTML = '<div class="logo"><img src="data:image/png;base64,""" + LOGO_B64 + """"/></div>'

def mostrar_login():
    if st.session_state.get("autenticado"):
        return True
    st.markdown(CSS, unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown(
            '<div class="card">' + LOGO_HTML +
            '<div class="badge"><span><div class="dot"></div>Acceso Restringido</span></div></div>',
            unsafe_allow_html=True)
        st.markdown("<div style='height:330px'></div>", unsafe_allow_html=True)
        usuario  = st.text_input("Usuario",    placeholder="Ingresa tu usuario", key="login_user")
        password = st.text_input("Contrasena", placeholder="Contrasena",         type="password", key="login_pass")
        if st.button("INGRESAR AL PORTAL", use_container_width=True):
            if _verificar(usuario.strip().lower(), password):
                st.session_state["autenticado"] = True
                st.session_state["usuario"]     = usuario.strip().lower()
                st.session_state["rol"]         = ROLES.get(usuario.strip().lower(), "Usuario")
                st.rerun()
            else:
                st.error("Usuario o contrasena incorrectos.")
        st.markdown("<div class='foot'>Portal NOC v1.0 - Andean Telecom Partners</div>", unsafe_allow_html=True)
    return False

def cerrar_sesion():
    u = st.session_state.get("usuario","")
    r = st.session_state.get("rol","")
    st.sidebar.markdown(f"<div style='font-size:11px;color:#64748b'><span style='color:#dc2626'>&#9679;</span> {u} &middot; {r}</div>", unsafe_allow_html=True)
    if st.sidebar.button("Cerrar sesion"):
        for k in ["autenticado","usuario","rol"]: st.session_state.pop(k,None)
        st.rerun()
"""

with open("login.py", "w", encoding="utf-8") as f:
    f.write(content)
print("OK")
