import time

import streamlit as st

from lib.db import COMPLEJAS_FILE, query
from lib.sqlfiles import leer_bloques
from lib.ui import encabezado, requiere_base

encabezado("Consultas complejas", "sql/04_consultas_complejas.sql · el dashboard lee y corre el archivo tal cual",
           "Proponga al menos 6 consultas complejas en las que se utilicen operaciones avanzadas "
           "(Join, exist, not exist, in, etc.)")
requiere_base()

bloques = leer_bloques(COMPLEJAS_FILE)
st.markdown(" · ".join(f"**{b.codigo}** {b.usa}" for b in bloques))

for b in bloques:
    with st.expander(f"**{b.codigo}** — {b.titulo}", expanded=b.codigo == "Q1"):
        if b.usa:
            st.caption(f"Usa: {b.usa}")
        izq, der = st.columns([2, 3])
        izq.code(b.sql, language="sql")
        t0 = time.perf_counter()
        try:
            df = query(b.sql)
            der.dataframe(df, hide_index=True, width="stretch", height=360)
            der.caption(f"{len(df)} filas · {1000 * (time.perf_counter() - t0):.0f} ms")
        except Exception as e:  # noqa: BLE001
            der.error(str(e))

st.divider()
st.subheader("Consulta libre")
st.caption("Para responder preguntas del profe en vivo. Corre en modo solo lectura.")
sql = st.text_area("SQL", "select ca.nombre, count(*) from jugador j\njoin plantel pl on pl.dni_jugador = j.dni_jugador\n"
                   "join torneo t on t.id_torneo = pl.id_torneo\njoin categoria ca on ca.id_categoria = t.id_categoria\n"
                   "where t.nombre = 'Apertura'\ngroup by ca.nombre order by 1", height=150)
if st.button("Ejecutar", type="primary"):
    from lib.db import connect, _rows_to_df
    try:
        with connect() as conn:
            conn.read_only = True
            st.dataframe(_rows_to_df(conn.execute(sql)), hide_index=True, width="stretch")
    except Exception as e:  # noqa: BLE001
        st.error(str(e))
