import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import os
from modulos.gestion_reservas import render_reservas
import time as python_time 

# --- CONFIGURACIÓN INICIAL ---
LOGO_PATH = os.path.join("frontend", "logo_restaurante.jpg")
API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Restaurante Don José - Gestión", layout="wide", page_icon="🍽️")

# --- 1. INICIALIZACIÓN DEL ESTADO ---
if "token" not in st.session_state:
    st.session_state.token = None
if "role" not in st.session_state:
    st.session_state.role = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "reset_u" not in st.session_state: 
    st.session_state.reset_u = 0

# --- 2. CONTROL DE NAVEGACIÓN ---
if st.session_state.token is not None:
    with st.sidebar:
        if st.button("⚠️ Recordatorio: Cierre Sesión antes de salir", width='stretch'):
            st.warning("Use el botón 'Cerrar Sesión' al final de la barra lateral.")

def pie_de_pagina():
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "© 2026 Restaurante Don José - Sistema de Gestión Interna.</div>", 
        unsafe_allow_html=True
    )

# ==========================================
#                 PANTALLA DE LOGIN
# ==========================================
if st.session_state.token is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=200)
        st.title("🔐 Acceso al Sistema")
        
        with st.form("login_form"):
            u = st.text_input("Correo electrónico", placeholder="ejemplo@correo.com")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                try:
                    res = requests.post(f"{API_URL}/users/login", data={"username": u, "password": p})
                    if res.status_code == 200:
                        d = res.json()
                        st.session_state.token = d["access_token"]
                        st.session_state.role = d["role"]
                        st.session_state.user_id = d.get("user_id") 
                        st.session_state.user_name = u.split('@')[0]
                        st.success("✅ ¡Bienvenido!")
                        st.rerun()
                    else:
                        st.error("❌ Credenciales incorrectas.")
                except:
                    st.error("📡 Error de conexión con el servidor.")
        pie_de_pagina()
    st.stop() 

# ==========================================
#          DASHBOARD PRINCIPAL
# ==========================================
headers = {"Authorization": f"Bearer {st.session_state.token}"}
rol = st.session_state.role

# --- BARRA LATERAL ---
with st.sidebar:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=150)
    st.write(f"### 👋 Hola, {st.session_state.user_name}")
    st.caption(f"Rol: {str(rol).upper()}")
    st.divider()
    if st.button("🚪 Cerrar Sesión", width='stretch', type="primary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# --- DEFINICIÓN DE MENÚ SEGÚN ROL ---
if rol == "admin":
    menu = ["🪑 Mesas", "👥 Clientes", "📅 Reservas", "📋 Auditoría", "⚙️ Usuarios"]
elif rol == "mesero":
    menu = ["🪑 Mesas", "👥 Clientes", "📅 Reservas"]
else:
    menu = ["🔍 Mis Reservas", "👤 Mi Perfil"]

tabs = st.tabs(menu)

# --- PESTAÑA 0: MESAS (STAFF) o MIS RESERVAS (CLIENTE) ---
with tabs[0]:
    if rol in ["admin", "mesero"]:
        st.header("🪑 Estado de las Mesas")
        
        # 1. Obtener datos frescos de XAMPP
        res_t = requests.get(f"{API_URL}/tables/", headers=headers)
        res_r_check = requests.get(f"{API_URL}/reservations/", headers=headers)
        
        if res_t.status_code == 200:
            mesas_list = res_t.json()
            reservas_raw = res_r_check.json() if res_r_check.status_code == 200 else []
            
            # --- BLOQUE DE COHERENCIA AUTOMÁTICA (Sincronización al entrar) ---
            # Este bloque corrige las mesas 2 y 3 que mencionaste
            for m in mesas_list:
                # Buscamos si tiene reserva confirmada en la DB
                tiene_reserva = any(r['table_id'] == m['id'] and r['status'] == 'confirmada' for r in reservas_raw)
                
                # Caso A: XAMPP dice LIBRE pero hay RESERVA CONFIRMADA -> Forzamos estado a 'reservada'
                if tiene_reserva and m['status'] == 'libre':
                    # Nota: Usamos la ruta /tables/{id} con PUT ya que tu router tiene update_table
                    requests.put(f"{API_URL}/tables/{m['id']}", json={"status": "reservada"}, headers=headers)
                    m['status'] = 'reservada' # Actualización visual inmediata
                
                # Caso B: XAMPP dice RESERVADA pero NO hay reserva activa -> Liberamos mesa
                elif not tiene_reserva and m['status'] == 'reservada':
                    requests.patch(f"{API_URL}/tables/{m['id']}/release", headers=headers)
                    m['status'] = 'libre'

            # 2. Mostrar Métricas (Ahora ya vendrán coherentes)
            cols = st.columns(4) 
            for i, mesa in enumerate(mesas_list):
                with cols[i % 4]:
                    emoji = "🔴" if mesa['status'] == 'ocupada' else "🟡" if mesa['status'] == 'reservada' else "🟢"
                    st.metric(label=f"Mesa {mesa['number']}", value=mesa['status'].upper(), delta=emoji)
                    
                    if mesa['status'] in ['ocupada', 'reservada']:
                        if st.button(f"🔓 Liberar #{mesa['number']}", key=f"btn_lib_{mesa['id']}"):
                            # VALIDACIÓN DE SEGURIDAD (No permite liberar si hay reserva activa)
                            activas = [r for r in reservas_raw if r['table_id'] == mesa['id'] and r['status'] == 'confirmada']
                            if activas:
                                st.error(f"Acción bloqueada: La mesa {mesa['number']} tiene una reserva activa. Gestiónela en Reservas.")
                            else:
                                r = requests.patch(f"{API_URL}/tables/{mesa['id']}/release", headers=headers)
                                if r.status_code == 200:
                                    st.toast(f"Mesa {mesa['number']} LIBRE")
                                    python_time.sleep(0.5)
                                    st.rerun()

            st.divider()
            st.subheader("📋 Listado de Mesas")
            st.dataframe(pd.DataFrame(mesas_list), width='stretch')
            
            if rol == "admin":
                with st.expander("➕ Agregar Nueva Mesa"):
                    with st.form("new_table"):
                        n_num = st.number_input("Número", min_value=1)
                        n_cap = st.number_input("Capacidad", min_value=1)
                        if st.form_submit_button("Guardar Mesa"):
                            requests.post(f"{API_URL}/tables/", json={"number":n_num, "capacity":n_cap}, headers=headers)
                            st.rerun()
    else:
        # --- VISTA PARA CLIENTES ---
        st.header("🔍 Mis Reservas")
        res_r = requests.get(f"{API_URL}/reservations/", headers=headers)
        if res_r.status_code == 200:
            data = res_r.json()
            if data:
                st.info("A continuación se detallan tus reservaciones en el sistema.")
                st.dataframe(pd.DataFrame(data), width='stretch')
            else:
                st.info("No se encontraron reservas registradas a tu nombre.")
                
# --- PESTAÑA 1: CLIENTES (STAFF) o MI PERFIL (CLIENTE) ---
with tabs[1]:
    if rol in ["admin", "mesero"]:
        st.header("👥 Gestión de Clientes")
        res_c = requests.get(f"{API_URL}/customers/", headers=headers)
        if res_c.status_code == 200:
            c_list = res_c.json()
            st.dataframe(pd.DataFrame(c_list), width='stretch')
            st.divider()
            
            opciones_c = {f"{c['full_name']} | ID: {c['id']}": c for c in c_list}
            sel_c = st.selectbox("Seleccionar Cliente para editar:", ["-- Seleccionar --"] + list(opciones_c.keys()))
            c_sel = opciones_c.get(sel_c, {"id": 0, "full_name": "", "phone": "", "whatsapp": "", "address": ""})
            
            if c_sel['id'] != 0:
                with st.form("staff_edit_customer"):
                    f_name = st.text_input("Nombre", value=c_sel['full_name'])
                    f_phone = st.text_input("Teléfono", value=c_sel['phone'])
                    f_ws = st.text_input("WhatsApp", value=c_sel['whatsapp'])
                    f_dir = st.text_input("Dirección", value=c_sel.get('address',''))
                    if st.form_submit_button("💾 Guardar cambios"):
                        payload = {"full_name": f_name, "phone": f_phone, "whatsapp": f_ws, "address": f_dir}
                        requests.put(f"{API_URL}/customers/{c_sel['id']}", json=payload, headers=headers)
                        st.rerun()
    else:
        st.header("👤 Mi Perfil")
        res_c = requests.get(f"{API_URL}/customers/", headers=headers)
        mi_ficha = {"id": 0, "full_name": st.session_state.user_name, "phone": "", "whatsapp": "", "address": ""}
        if res_c.status_code == 200:
            mi_ficha = next((c for c in res_c.json() if c.get('user_id') == st.session_state.user_id), mi_ficha)

        with st.form("perfil_cliente_self"):
            st.info("Aquí puedes completar tus datos personales.")
            fn = st.text_input("Nombre Completo", value=mi_ficha['full_name'])
            ph = st.text_input("Teléfono", value=mi_ficha['phone'])
            ws = st.text_input("WhatsApp", value=mi_ficha['whatsapp'])
            ad = st.text_input("Dirección", value=mi_ficha.get('address',''))
            
            if st.form_submit_button("💾 Actualizar mis datos"):
                payload = {"full_name": fn, "phone": ph, "whatsapp": ws, "address": ad, "user_id": st.session_state.user_id}
                if mi_ficha['id'] != 0:
                    requests.put(f"{API_URL}/customers/{mi_ficha['id']}", json=payload, headers=headers)
                else:
                    requests.post(f"{API_URL}/customers/", json=payload, headers=headers)
                st.success("¡Perfil actualizado con éxito!")
                python_time.sleep(1)
                st.rerun()

# --- PESTAÑAS EXCLUSIVAS PARA STAFF ---
if len(tabs) > 2:
    with tabs[2]:
        render_reservas(API_URL, headers, rol)

if len(tabs) > 3 and rol == "admin":
    with tabs[3]:
        st.header("📋 Auditoría de XAMPP")
        if st.button("🔄 Consultar Logs"):
            res_l = requests.get(f"{API_URL}/reservations/logs", headers=headers)
            if res_l.status_code == 200:
                st.dataframe(pd.DataFrame(res_l.json()), width='stretch')

if len(tabs) > 4 and rol == "admin":
    with tabs[4]:
        st.header("⚙️ Gestión de Usuarios")
        res_u = requests.get(f"{API_URL}/users/", headers=headers)
        if res_u.status_code == 200:
            u_list = res_u.json()
            st.dataframe(pd.DataFrame(u_list), width='stretch')
            st.divider()
            op_u = {f"{u['username']}": u for u in u_list}
            sel_u = st.selectbox("Editar Usuario:", ["-- Nuevo --"] + list(op_u.keys()))
            u_dat = op_u.get(sel_u, {"id": 0, "email": "", "username": "", "role": "cliente"})
            with st.form("edit_user"):
                un = st.text_input("Username", value=u_dat['username'])
                em = st.text_input("Email", value=u_dat['email'])
                ro = st.selectbox("Rol", ["admin", "mesero", "cliente"], index=["admin", "mesero", "cliente"].index(u_dat['role']))
                if st.form_submit_button("💾 Guardar Usuario"):
                    payload = {"username": un, "email": em, "role": ro, "is_active": True}
                    if u_dat['id'] == 0:
                        payload["password"] = "123456"
                        requests.post(f"{API_URL}/users/", json=payload, headers=headers)
                    else:
                        requests.put(f"{API_URL}/users/{u_dat['id']}", json=payload, headers=headers)
                    st.rerun()

pie_de_pagina()