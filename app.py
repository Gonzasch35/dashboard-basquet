"""Dashboard de la Liga de Basquet Formativo de Parana - temporada 2026.

Correr con:   streamlit run app.py
Integrantes:  Tomiozzo Franco y Schmidt Gonzalo
"""
import streamlit as st

from lib import db, ui

st.set_page_config(page_title="Liga de Básquet Formativo 2026", page_icon="🏀", layout="wide",
                   menu_items={"Get help": None, "Report a bug": None, "About": None})

paginas = {
    "Presentación": [
        st.Page("views/inicio.py", title="Inicio", icon="🏀", default=True),
        st.Page("views/modelo.py", title="Cómo se guardan los datos", icon="🗂️"),
    ],
    "Temporada 2026": [
        st.Page("views/posiciones.py", title="Posiciones y playoff", icon="🏆"),
        st.Page("views/jugadores.py", title="Jugadores", icon="⛹️"),
        st.Page("views/arbitros.py", title="Árbitros y calendario", icon="🧑‍⚖️"),
    ],
    "Análisis": [
        st.Page("views/controles.py", title="Controles de integridad", icon="✅"),
        st.Page("views/estadistica.py", title="Análisis estadístico", icon="📈"),
    ],
}
# "top" = menu arriba (cada seccion es un desplegable); "sidebar" = menu en la barra lateral
NAV_POSICION = "sidebar"
nav = st.navigation(paginas, position=NAV_POSICION)

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### 🏀 Temporada **2026**")
    st.caption("Todos los datos que se muestran son de la temporada 2026 (Apertura y Clausura).")
    st.toggle("🔍 Letra grande (para proyectar)", key="letra_grande",
              help="Agranda el texto de las páginas y de los gráficos para que se lea desde lejos.")
    cfg = db.get_config()
    ok, msg = db.ping()
    st.markdown(("🟢 Conectado a la base" if ok else "🔴 Sin conexión a la base") +
                f"  \n`{cfg['dbname']}` @ `{cfg['host']}:{cfg['port']}`")
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
        st.caption("Si la base no existe o está vacía, este botón la crea y carga los datos de 2026.")
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

ui.estilos()  # modo oscuro + efectos (despues del toggle de letra grande)
nav.run()
