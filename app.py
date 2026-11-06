"""Dashboard de la Liga de Basquet Formativo de Parana - TP Final Base de Datos.

Correr con:   streamlit run app.py
Integrantes:  Tomiozzo Franco y Schmidt Gonzalo
"""
import streamlit as st

from lib import db

st.set_page_config(page_title="Liga de Básquet Formativo · TP Final BD", page_icon="🏀", layout="wide")

paginas = {
    "Presentación": [
        st.Page("views/inicio.py", title="Inicio", icon="🏀", default=True),
        st.Page("views/modelo.py", title="Modelo de datos", icon="🗂️"),
    ],
    "La liga": [
        st.Page("views/posiciones.py", title="Posiciones y playoff", icon="🏆"),
        st.Page("views/jugadores.py", title="Jugadores", icon="⛹️"),
        st.Page("views/arbitros.py", title="Árbitros y calendario", icon="🧑‍⚖️"),
    ],
    "Consigna Parte 2": [
        st.Page("views/consultas.py", title="Consultas complejas", icon="🔎"),
        st.Page("views/algebra.py", title="Álgebra relacional", icon="🌳"),
        st.Page("views/controles.py", title="Controles de integridad", icon="✅"),
        st.Page("views/estadistica.py", title="Análisis estadístico", icon="📈"),
    ],
    "Código": [
        st.Page("views/grafo.py", title="Grafo del código", icon="🕸️"),
    ],
}
nav = st.navigation(paginas)

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    cfg = db.get_config()
    ok, msg = db.ping()
    st.markdown(f"**Base:** `{cfg['dbname']}` @ `{cfg['host']}:{cfg['port']}`")
    st.markdown("🟢 Conectado" if ok else "🔴 Sin conexión")
    with st.expander("Conexión a PostgreSQL", expanded=not ok):
        with st.form("conexion"):
            host = st.text_input("Host", cfg["host"])
            port = st.number_input("Puerto", value=int(cfg["port"]), step=1)
            dbname = st.text_input("Base", cfg["dbname"])
            user = st.text_input("Usuario", cfg["user"])
            password = st.text_input("Contraseña", cfg["password"], type="password")
            if st.form_submit_button("Conectar"):
                st.session_state.pg = dict(host=host, port=int(port), dbname=dbname, user=user, password=password)
                st.cache_data.clear()
                st.rerun()
        st.caption("Crea la base si no existe y corre `01_ddl` y `02_dml` de la carpeta *PARTE 2*.")
        if st.button("Crear / recargar base", width="stretch"):
            barra = st.progress(0.0, "Arrancando…")
            try:
                db.crear_y_cargar(lambda i, f: barra.progress((i + 0.5) / 2, f"Corriendo {f}…"))
                barra.progress(1.0, "Listo")
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(str(e))
    if ok and st.button("Refrescar datos", width="stretch"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption("TP Final · Base de Datos · FIUNER\n\nTomiozzo Franco · Schmidt Gonzalo")

nav.run()
