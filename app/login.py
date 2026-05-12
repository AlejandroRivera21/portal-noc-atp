import streamlit as st
import base64, os
from db import verificar_usuario, init_db

init_db()

def _logo_b64():
    path = os.path.join(os.path.dirname(__file__), "assets", "ATPLOGIN.png")
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

CSS = """<style>
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
</style><div class="bg"></div>"""

def mostrar_login():
    if st.session_state.get("autenticado"):
        return True
    try:
        logo = _logo_b64()
        LOGO_HTML = f'<div class="logo"><img src="data:image/png;base64,{logo}"/></div>'
    except:
        LOGO_HTML = '<div class="logo"><h2 style="color:white">ATP</h2></div>'

    st.markdown(CSS, unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown(
            f'<div class="card">{LOGO_HTML}'
            '<div class="badge"><span><div class="dot"></div>Acceso Restringido</span></div></div>',
            unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        usuario  = st.text_input("Usuario",    placeholder="Ingresa tu usuario", key="login_user")
        password = st.text_input("Contrasena", placeholder="Contrasena",         type="password", key="login_pass")
        if st.button("INGRESAR AL PORTAL", use_container_width=True):
            user = verificar_usuario(usuario, password)
            if user:
                st.session_state["autenticado"] = True
                st.session_state["usuario"]     = user["username"]
                st.session_state["nombre"]      = user["nombre"]
                st.session_state["rol"]         = user["rol"]
                st.session_state["user_id"]     = user["id"]
                st.rerun()
            else:
                st.error("Usuario o contrasena incorrectos.")
        st.markdown("<div class='foot'>Portal NOC v1.0 - Andean Telecom Partners</div>", unsafe_allow_html=True)
    return False

def cerrar_sesion():
    pass  # Manejado por sidebar_comun() en modules/styles.py

def solo_admin():
    return st.session_state.get("rol") == "administrador"

def es_operador():
    return st.session_state.get("rol") in ["administrador","operador"]

def es_usuario():
    return st.session_state.get("autenticado", False)
