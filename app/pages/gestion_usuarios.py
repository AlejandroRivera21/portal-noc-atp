import streamlit as st
from login import solo_admin
from modules.styles import sidebar_comun
from db import listar_usuarios, crear_usuario, actualizar_usuario, cambiar_password, eliminar_usuario

def render():
    sidebar_comun()
    if not solo_admin():
        st.error("Acceso restringido. Solo administradores.")
        st.stop()

    st.markdown("""
    <style>
    .user-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 16px; padding: 28px 32px; margin-bottom: 28px;
        border-left: 4px solid #dc2626;
        display: flex; align-items: center; gap: 16px;
    }
    .user-header h1 { color: white; font-size: 24px; font-weight: 700;
        margin: 0; letter-spacing: 0.5px; }
    .user-header p { color: rgba(255,255,255,0.5); font-size: 13px; margin: 4px 0 0; }
    .role-badge {
        display: inline-block; padding: 3px 10px; border-radius: 20px;
        font-size: 11px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
    }
    .badge-admin { background: rgba(220,38,38,0.15); color: #f87171; border: 1px solid rgba(220,38,38,0.3); }
    .badge-operador { background: rgba(59,130,246,0.15); color: #93c5fd; border: 1px solid rgba(59,130,246,0.3); }
    .badge-usuario { background: rgba(34,197,94,0.15); color: #86efac; border: 1px solid rgba(34,197,94,0.3); }
    .user-card {
        background: white; border-radius: 12px; padding: 18px 22px;
        border: 1px solid #f0f0f0; margin-bottom: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        display: flex; align-items: center; justify-content: space-between;
    }
    .user-avatar {
        width: 42px; height: 42px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 18px; font-weight: 700; color: white; margin-right: 14px;
    }
    .stat-card {
        background: white; border-radius: 12px; padding: 20px;
        border: 1px solid #f0f0f0; text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .stat-num { font-size: 32px; font-weight: 800; color: #1a1a2e; }
    .stat-label { font-size: 12px; color: #999; margin-top: 4px; text-transform: uppercase; letter-spacing: 1px; }
    </style>

    <div class="user-header">
        <div style="font-size:36px;">👥</div>
        <div>
            <h1>Gestión de Usuarios</h1>
            <p>Portal NOC ATP · Administración de accesos y roles</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    usuarios = listar_usuarios()
    total = len(usuarios)
    admins = sum(1 for u in usuarios if u["rol"] == "administrador")
    operadores = sum(1 for u in usuarios if u["rol"] == "operador")
    viewers = sum(1 for u in usuarios if u["rol"] == "usuario")
    activos = sum(1 for u in usuarios if u["activo"])

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='stat-card'><div class='stat-num' style='color:#1a1a2e'>{total}</div><div class='stat-label'>Total usuarios</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='stat-card'><div class='stat-num' style='color:#dc2626'>{admins}</div><div class='stat-label'>Administradores</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='stat-card'><div class='stat-num' style='color:#3b82f6'>{operadores}</div><div class='stat-label'>Operadores</div></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='stat-card'><div class='stat-num' style='color:#22c55e'>{activos}</div><div class='stat-label'>Activos</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["👤 Usuarios registrados", "➕ Crear nuevo usuario"])

    with tab1:
        for u in usuarios:
            rol_color = {"administrador": "#dc2626", "operador": "#3b82f6", "usuario": "#22c55e"}.get(u["rol"], "#999")
            badge_class = {"administrador": "badge-admin", "operador": "badge-operador", "usuario": "badge-usuario"}.get(u["rol"], "")
            activo_icon = "🟢" if u["activo"] else "🔴"

            with st.expander(f"{activo_icon}  {u['nombre']}  —  @{u['username']}"):
                st.markdown(f"""
                <div style='display:flex;align-items:center;gap:12px;margin-bottom:16px;
                            padding:12px 16px;background:#f8f9fa;border-radius:10px;'>
                    <div style='width:46px;height:46px;border-radius:50%;background:{rol_color};
                                display:flex;align-items:center;justify-content:center;
                                color:white;font-size:20px;font-weight:700;'>
                        {u['nombre'][0].upper()}
                    </div>
                    <div>
                        <div style='font-weight:700;font-size:15px;color:#1a1a2e;'>{u['nombre']}</div>
                        <div style='font-size:12px;color:#888;'>@{u['username']} · {u['email'] or 'Sin email'}</div>
                    </div>
                    <div style='margin-left:auto;'>
                        <span class='role-badge {badge_class}'>{u['rol']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col1, col2 = st.columns(2)
                with col1:
                    nombre = st.text_input("Nombre completo", value=u["nombre"], key=f"nom_{u['id']}")
                    email  = st.text_input("Email",           value=u["email"] or "", key=f"eml_{u['id']}")
                with col2:
                    rol    = st.selectbox("Rol", ["administrador","operador","usuario"],
                                          index=["administrador","operador","usuario"].index(u["rol"]),
                                          key=f"rol_{u['id']}")
                    activo = st.toggle("Usuario activo", value=bool(u["activo"]), key=f"act_{u['id']}")

                nueva_pass = st.text_input("Nueva contrasena (dejar vacio para no cambiar)",
                                           type="password", key=f"pwd_{u['id']}")

                col3, col4 = st.columns([2,1])
                with col3:
                    if st.button("💾 Guardar cambios", key=f"save_{u['id']}", use_container_width=True):
                        actualizar_usuario(u["id"], nombre, email, rol, int(activo))
                        if nueva_pass:
                            cambiar_password(u["id"], nueva_pass)
                        st.success("✅ Usuario actualizado correctamente.")
                        st.rerun()
                with col4:
                    if u["username"] != st.session_state.get("usuario"):
                        if st.button("🗑 Eliminar", key=f"del_{u['id']}", use_container_width=True):
                            eliminar_usuario(u["id"])
                            st.warning("Usuario eliminado.")
                            st.rerun()

    with tab2:
        st.markdown("""
        <div style='background:#f8f9fa;border-radius:12px;padding:24px 28px;margin-bottom:20px;
                    border-left:4px solid #3b82f6;'>
            <div style='font-weight:700;font-size:16px;color:#1a1a2e;margin-bottom:4px;'>Nuevo usuario</div>
            <div style='font-size:13px;color:#888;'>Completa los campos para crear una nueva cuenta de acceso.</div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            nu = st.text_input("Usuario",       key="nu_user",  placeholder="ej: jperez")
            nn = st.text_input("Nombre completo", key="nu_nom", placeholder="ej: Juan Perez")
        with col2:
            ne = st.text_input("Email",         key="nu_email", placeholder="ej: juan@atp.com")
            nr = st.selectbox("Rol", ["administrador","operador","usuario"], key="nu_rol")

        np = st.text_input("Contrasena", type="password", key="nu_pass", placeholder="Minimo 6 caracteres")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Crear usuario", use_container_width=True):
            if nu and np and nn:
                ok, msg = crear_usuario(nu, np, nn, ne, nr)
                if ok:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
            else:
                st.warning("⚠️ Usuario, nombre y contrasena son obligatorios.")

render()
