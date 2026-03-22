import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import os
from modulos.gestion_reservas import render_reservas
import time 

# --- CONFIGURACIÓN INICIAL ---
LOGO_PATH = os.path.join("frontend", "logo_restaurante.jpg")
API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Restaurante Don Juan - Gestión", layout="wide", page_icon="🍽️")

# --- FUNCIONES DE APOYO ---
def pie_de_pagina():
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "© 2026 Restaurante Don Juan - Sistema de Gestión Interna.</div>", 
        unsafe_allow_html=True
    )

# --- ESTADO DE SESIÓN ---
if "token" not in st.session_state:
    st.session_state.token = None
if "role" not in st.session_state:
    st.session_state.role = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "reset_u" not in st.session_state: 
    st.session_state.reset_u = 0

# ==========================================
#                PANTALLA DE LOGIN
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
                        st.session_state.user_name = u.split('@')[0]
                        st.success("✅ ¡Bienvenido!")
                        st.rerun()
                    else:
                        st.error("❌ Credenciales incorrectas o cuenta inactiva.")
                except:
                    st.error("📡 Error de conexión con el servidor.")
        pie_de_pagina()
    st.stop() # Detiene la ejecución para que no intente cargar el Dashboard sin login

# ==========================================
#         DASHBOARD PRINCIPAL (LOGUEADO)
# ==========================================
# Si llegamos aquí, es porque hay un token válido
headers = {"Authorization": f"Bearer {st.session_state.token}"}
rol = st.session_state.role

# --- BARRA LATERAL ---
with st.sidebar:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=150)
    st.write(f"### 👋 Hola, {st.session_state.user_name}")
    st.caption(f"Rol: {str(rol).upper()}")
    st.divider()
    if st.button("🚪 Cerrar Sesión", width='stretch'):
        st.session_state.token = None
        st.session_state.role = None
        st.rerun()

# Definición de pestañas según rol
if rol == "admin":
    menu = ["🪑 Mesas", "👥 Clientes", "📅 Reservas", "📋 Auditoría", "⚙️ Usuarios"]
elif rol == "mesero":
    menu = ["🪑 Mesas", "👥 Clientes", "📅 Reservas"]
else:
    menu = ["🔍 Mis Reservas", "👤 Mi Perfil"]

tabs = st.tabs(menu)

# --- PESTAÑA 0: MESAS ---
with tabs[0]:
    if rol in ["admin", "mesero"]:
        st.header("🪑 Estado Real de las Mesas")
        res_t = requests.get(f"{API_URL}/tables/", headers=headers)
        
        if res_t.status_code == 200:
            mesas_list = res_t.json()
            
            # --- SECCIÓN 1: VISTA VISUAL (Tarjetas rápidas) ---
            cols = st.columns(4) 
            for i, mesa in enumerate(mesas_list):
                with cols[i % 4]:
                    # Color e icono según estado
                    emoji = "🔴" if mesa['status'] == 'ocupada' else "🟡" if mesa['status'] == 'reservada' else "🟢"
                    st.metric(label=f"Mesa {mesa['number']}", value=mesa['status'].upper(), delta=emoji, delta_color="normal")
                    
                    # BOTÓN DE ACCIÓN RÁPIDA (Solo aparece si no está libre)
                    if mesa['status'] in ['ocupada', 'reservada']:
                        if st.button(f"🔓 Liberar #{mesa['number']}", key=f"btn_lib_{mesa['id']}"):
                            # Intentamos llamar al PATCH si lo creaste, si no, usa el PUT normal
                            r = requests.patch(f"{API_URL}/tables/{mesa['id']}/release", headers=headers)
                            if r.status_code == 200:
                                st.toast(f"Mesa {mesa['number']} ahora está LIBRE")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("No se pudo liberar. ¿Creaste el endpoint en el Backend?")

            st.divider()
            
            # --- SECCIÓN 2: GESTIÓN Y EDICIÓN (Tu código original) ---
            st.subheader("🔍 Configuración y Edición")
            st.dataframe(pd.DataFrame(mesas_list), width='stretch')
            
            opciones_m = {f"Mesa {m['number']} | Cap: {m['capacity']}": m for m in mesas_list}
            sel_m = st.selectbox("Cargar mesa para modificar:", ["-- Nueva Mesa --"] + list(opciones_m.keys()))
            m_data = opciones_m.get(sel_m, {"id": 0, "number": 1, "capacity": 2, "status": "libre"})

            col1, col2 = st.columns(2)
            with col1:
                with st.form("form_mesas_edit"):
                    st.info("Editando..." if m_data['id'] != 0 else "Creando Nueva")
                    n_num = st.number_input("Número de Mesa", value=int(m_data['number']), min_value=1)
                    n_cap = st.number_input("Capacidad (Personas)", value=int(m_data['capacity']), min_value=1)
                    
                    lista_est = ["libre", "ocupada", "reservada"]
                    idx_est = lista_est.index(m_data['status']) if m_data['status'] in lista_est else 0
                    n_stat = st.selectbox("Cambiar Estado Manualmente", lista_est, index=idx_est)
                    
                    if st.form_submit_button("💾 Guardar Cambios"):
                        payload = {"number": n_num, "capacity": n_cap, "status": n_stat}
                        if m_data['id'] == 0:
                            requests.post(f"{API_URL}/tables/", json=payload, headers=headers)
                        else:
                            requests.put(f"{API_URL}/tables/{m_data['id']}", json=payload, headers=headers)
                        st.rerun()
            
            with col2:
                if rol == "admin" and m_data['id'] != 0:
                    st.subheader("🗑️ Zona de Peligro")
                    if st.button("🔴 Eliminar Mesa Definitivamente") and st.checkbox("Entiendo que esto borrará la mesa"):
                        requests.delete(f"{API_URL}/tables/{m_data['id']}", headers=headers)
                        st.rerun()
# --- PESTAÑA 1: CLIENTES ---
if rol in ["admin", "mesero"]:
    with tabs[1]:
        st.header("👥 Gestión de Clientes")
        res_c = requests.get(f"{API_URL}/customers/", headers=headers)
        if res_c.status_code == 200:
            c_list = res_c.json()
            st.dataframe(pd.DataFrame(c_list), width='stretch')
            st.divider()
            opciones_c = {f"{c['full_name']} | 📱 {c.get('phone','')}": c for c in c_list}
            sel_c = st.selectbox("Busca por nombre o teléfono:", ["-- Seleccionar --"] + list(opciones_c.keys()))
            c_sel = opciones_c.get(sel_c, {"id": 0, "full_name": "", "phone": "", "whatsapp": "", "address": "", "user_id": 0})
            c1, c2 = st.columns(2)
            with c1:
                if c_sel['id'] != 0:
                    with st.form("form_cliente"):
                        f_name = st.text_input("Nombre Completo", value=c_sel['full_name'])
                        f_phone = st.text_input("Teléfono", value=c_sel['phone'])
                        f_ws = st.text_input("WhatsApp", value=c_sel['whatsapp'])
                        f_dir = st.text_input("Dirección", value=c_sel.get('address',''))
                        if st.form_submit_button("💾 Actualizar Ficha"):
                            p = {"full_name": f_name, "phone": f_phone, "whatsapp": f_ws, "address": f_dir}
                            requests.put(f"{API_URL}/customers/{c_sel['id']}", json=p, headers=headers)
                            st.rerun()

# --- PESTAÑA 2: RESERVAS ---
with tabs[2]:
    if rol in ["admin", "mesero"]:
        render_reservas(API_URL, headers, rol)
    else:
        st.header("👤 Mi Perfil")
        st.info("Completa tus datos para agilizar tus reservas.")

# --- PESTAÑA 3: AUDITORÍA ---
if rol == "admin":
    with tabs[3]:
        st.header("📋 Auditoría de XAMPP")
        if st.button("🔄 Consultar Logs Recientes", key="btn_logs_final"):
            res_l = requests.get(f"{API_URL}/reservations/logs", headers=headers)
            if res_l.status_code == 200:
                st.dataframe(pd.DataFrame(res_l.json()), width='stretch')

# --- PESTAÑA 4: USUARIOS ---
if rol == "admin":
    with tabs[4]:
        st.header("⚙️ Gestión de Usuarios")
        res_u = requests.get(f"{API_URL}/users/", headers=headers)
        if res_u.status_code == 200:
            u_list = res_u.json()
            st.dataframe(pd.DataFrame(u_list), width='stretch')
            st.divider()

            op_u = {f"{u['username']} ({u['email']})": u for u in u_list}
            sel_u = st.selectbox("Seleccionar Usuario:", ["-- Nuevo --"] + list(op_u.keys()), key=f"sb_u_{st.session_state.reset_u}")
            
            u_dat = op_u.get(sel_u, {"id": 0, "email": "", "username": "", "role": "cliente", "is_active": True})

            with st.form(f"f_u_{u_dat['id']}"):
                u_email = st.text_input("Email", value=u_dat['email'])
                u_name = st.text_input("Username", value=u_dat['username'])
                u_role = st.selectbox("Rol", ["admin", "mesero", "cliente"], index=0)
                
                if st.form_submit_button("💾 Guardar y Limpiar Filtro"):
                    payload = {"email": u_email, "username": u_name, "role": u_role, "is_active": True}
                    if u_dat['id'] == 0:
                        payload["password"] = "123456"
                        r = requests.post(f"{API_URL}/users/", json=payload, headers=headers)
                    else:
                        r = requests.put(f"{API_URL}/users/{u_dat['id']}", json=payload, headers=headers)
                    
                    if r.status_code in [200, 201]:
                        st.success("✅ Actualizado en XAMPP")
                        st.session_state.reset_u += 1 
                        time.sleep(1)
                        st.rerun()

pie_de_pagina()