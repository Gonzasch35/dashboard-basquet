"""Corre los controles de 03_controles.sql y demuestra que la base se defiende.

Todo lo que "rompe" datos corre dentro de una transaccion que se deshace
(rollback): la base queda exactamente igual.
"""
import time

import pandas as pd
import streamlit as st

from lib.db import CONTROLES_FILE, query, run_in_rollback
from lib.sqlfiles import leer_bloques
from lib.ui import encabezado, requiere_base

encabezado("Controles de integridad",
           "sql/03_controles.sql · cada control busca las filas que ROMPEN una regla: 0 filas = la regla se cumple",
           """
Hay reglas que la base hace cumplir sola (PK, FK, UNIQUE, CHECK) y otras que miran varias filas o
varias tablas a la vez: esas las revisa un **control**, una consulta que busca los datos que rompen la regla.
Si el control devuelve **0 filas**, la regla se cumple.

En la versión final, **C3, C6 y C9** (equipo, torneo y pase de la misma categoría) ya los frena el DDL con
FK compuestas que comparten `id_categoria`; se dejan como doble chequeo y tienen que dar siempre 0 filas.
""")
requiere_base()

bloques = leer_bloques(CONTROLES_FILE)
controles = [b for b in bloques if b.codigo.startswith("C")]
ejemplos = [b for b in bloques if b.codigo.startswith("E")]
por_codigo = {b.codigo: b for b in bloques}

# C3, C6 y C9 traen en el titulo la nota "Ahora lo FRENA el DDL ..." (03_controles.sql):
# se saca del titulo para que la tabla no quede enorme y se marca con 🛡️
NOTA_DDL = " Ahora lo FRENA el DDL"
frena_ddl = set()
for b in bloques:
    if NOTA_DDL in b.titulo:
        b.titulo = b.titulo.split(NOTA_DDL)[0].strip()
        frena_ddl.add(b.codigo)

tab_ctrl, tab_trucho, tab_ej = st.tabs(["Correr los controles", "¿La base se defiende?", "Consultas de ejemplo"])

# ------------------------------------------------------------------ controles
with tab_ctrl:
    filas = []
    t0 = time.perf_counter()
    for b in controles:
        try:
            n = len(query(b.sql))
            err = ""
        except Exception as e:  # noqa: BLE001
            n, err = -1, str(e)
        informativo = b.codigo == "C30"
        estado = "ℹ️ informativo" if informativo else ("✅ 0 filas" if n == 0 else ("⚠️ error" if n < 0 else f"❌ {n} filas"))
        regla = ("🛡️ " if b.codigo in frena_ddl else "") + b.titulo
        filas.append(dict(control=b.codigo, seccion=b.seccion.title(), regla=regla, resultado=estado, filas=n, error=err))
    res = pd.DataFrame(filas)
    reglas = res[res.control != "C30"]
    ok = int((reglas.filas == 0).sum())
    c = st.columns(3)
    c[0].metric("Controles", len(reglas))
    c[1].metric("Se cumplen", f"{ok} / {len(reglas)}")
    c[2].metric("Tiempo total", f"{1000 * (time.perf_counter() - t0):.0f} ms")
    if ok == len(reglas):
        st.success("Todas las reglas se cumplen: los 29 controles devuelven 0 filas.")
    else:
        st.error("Hay controles que encontraron filas que rompen la regla.")
    # anchos fijos (en px): con width="stretch" el espacio sobrante se repartia parejo y "resultado"
    # quedaba ancha mientras "regla" se cortaba. "regla" mide lo justo para el titulo mas largo.
    st.dataframe(res[["control", "seccion", "regla", "resultado"]], hide_index=True, width="content", height=560,
                 column_config={
                     "control": st.column_config.TextColumn(width=65),
                     "seccion": st.column_config.TextColumn("sección", width=190),
                     "regla": st.column_config.TextColumn(width=800),
                     "resultado": st.column_config.TextColumn(width=110),
                 })
    st.caption("🛡️ = regla que ya frena el DDL (FK compuestas que comparten `id_categoria`); "
               "el control queda como doble chequeo y tiene que dar siempre 0 filas.")

    sel = st.selectbox("Ver el SQL de un control", [b.codigo for b in controles],
                       format_func=lambda k: f"{k} — {por_codigo[k].titulo}")
    st.code(por_codigo[sel].sql, language="sql")
    if sel == "C30":
        st.dataframe(query(por_codigo[sel].sql), hide_index=True)

# ------------------------------------------------------------------ datos truchos
UNO_NORMAL = "(select min(id_partido) from partido where id_equipo_ausente is null and fase = 'Regular' and fecha_original is null)"
UNA_EST = "(select id_partido, dni_jugador from estadistica order by id_partido, dni_jugador limit 1)"

FRENADOS_POR_DDL = {
    "Un equipo juega contra sí mismo":
        f"update partido set id_equipo_visitante = id_equipo_local where id_partido = {UNO_NORMAL}",
    "Un partido termina empatado":
        f"update partido set puntos_visitante = puntos_local where id_partido = {UNO_NORMAL}",
    "Sumarle un triple a un jugador sin cambiar sus puntos":
        f"update estadistica set triples = triples + 1 where (id_partido, dni_jugador) = {UNA_EST}",
    "Un jugador con 6 faltas":
        f"update estadistica set faltas = 6 where (id_partido, dni_jugador) = {UNA_EST}",
    "Ponerle a un equipo el entrenador de OTRO club (FK compuesta)":
        "update equipo set dni_entrenador = (select en.dni_entrenador from entrenador en "
        "where en.id_club <> equipo.id_club limit 1) where id_equipo = 1",
    "Cargar puntos de un jugador del visitante como si fuera del local (FK compuesta a plantel)":
        "insert into estadistica (id_partido, dni_jugador, id_equipo, id_torneo) "
        "select p.id_partido, pl.dni_jugador, p.id_equipo_local, p.id_torneo from partido p "
        "join plantel pl on pl.id_torneo = p.id_torneo and pl.id_equipo = p.id_equipo_visitante "
        "where p.id_equipo_ausente is null and not exists (select 1 from estadistica e "
        "where e.id_partido = p.id_partido and e.dni_jugador = pl.dni_jugador) limit 1",
    "Un partido de fase regular a las 15:00":
        f"update partido set hora = '15:00' where id_partido = {UNO_NORMAL}",
    "Marcar W.O. un partido que no terminó 20 a 0":
        f"update partido set id_equipo_ausente = id_equipo_local where id_partido = {UNO_NORMAL}",
    "Dorsal 25 (solo se permite del 4 al 19)":
        "update plantel set numero_camiseta = 25 where (id_equipo, dni_jugador, id_torneo) = "
        "(select id_equipo, dni_jugador, id_torneo from plantel limit 1)",
    "Dos árbitros principales en el mismo partido":
        "update arbitro_partido set rol = 'Principal' where rol = 'Auxiliar' "
        "and id_partido = (select min(id_partido) from partido)",
    "Un torneo que termina antes de empezar":
        "update torneo set fecha_fin = fecha_inicio - 1 where id_torneo = 1",
    "Un pase de un equipo a sí mismo":
        "update pase set id_equipo_destino = id_equipo_origen where id_pase = (select min(id_pase) from pase)",
    "Borrar un club que tiene equipos":
        "delete from club where id_club = 1",
    "Meter un equipo U15 en un partido del torneo U13 (FK compuesta con categoría, ex C9)":
        "update partido set id_equipo_visitante = (select min(id_equipo) from equipo where id_categoria = 2) "
        "where id_partido = (select min(id_partido) from partido where id_categoria = 1)",
    "Anotar un jugador de un equipo U15 en el torneo U17 (FK compuesta con categoría, ex C3)":
        "insert into plantel (id_equipo, dni_jugador, id_torneo, id_categoria, numero_camiseta) "
        "select pl.id_equipo, pl.dni_jugador, (select min(id_torneo) from torneo where id_categoria = 3), 2, 4 "
        "from plantel pl where pl.id_categoria = 2 limit 1",
    "Un pase de un equipo U13 a uno U15 (FK compuesta con categoría, ex C6)":
        "update pase set id_equipo_destino = (select min(id_equipo) from equipo where id_categoria = 2) "
        "where id_pase = (select min(id_pase) from pase where id_categoria = 1)",
    "Cargar una segunda final en el mismo torneo (índice único parcial)":
        "insert into partido (id_torneo, id_categoria, fase, fecha, hora, id_cancha, id_equipo_local, id_equipo_visitante) "
        "select id_torneo, id_categoria, 'Final', fecha + 7, hora, id_cancha, id_equipo_local, id_equipo_visitante "
        "from partido where fase = 'Final' limit 1",
    "Un jugador de 2,50 m":
        "update jugador set altura_cm = 250 where dni_jugador = (select min(dni_jugador) from jugador)",
}

DETECTADOS_POR_CONTROL = {
    "Bajarle el nivel ENEBA a un entrenador de U19": (
        "C1", "update entrenador set nivel_eneba = 1 where dni_entrenador = "
              "(select dni_entrenador from equipo where id_categoria = 4 order by id_equipo limit 1)"),
    "Sumar 3 puntos (un triple) a un jugador sin cambiar el resultado del partido": (
        "C29", f"update estadistica set triples = triples + 1, puntos = puntos + 3 "
               f"where (id_partido, dni_jugador) = {UNA_EST}"),
    "Borrar un pase y dejar el intercambio por la mitad": (
        "C5", "delete from pase where id_pase = (select min(id_pase) from pase)"),
    "Poner un árbitro Aspirante en un partido de U19": (
        "C22", "update arbitro_partido set dni_arbitro = (select min(dni_arbitro) from arbitro "
               "where categoria_arbitro = 'Aspirante') where rol = 'Auxiliar' and id_partido = "
               "(select min(p.id_partido) from partido p join torneo t on t.id_torneo = p.id_torneo "
               "where t.id_categoria = 4)"),
    "Sacar las estadísticas de un partido jugado": (
        "C14", f"delete from estadistica where id_partido = {UNO_NORMAL}"),
}

with tab_trucho:
    st.markdown("Todo corre dentro de `begin … rollback`: **la base no cambia**.")
    a, b = st.columns(2)
    with a:
        st.subheader("1 · Lo frena el DDL")
        st.caption("PK, FK (simples y compuestas), UNIQUE y CHECK: la base directamente no deja guardarlo.")
        caso = st.selectbox("Dato trucho", list(FRENADOS_POR_DDL))
        sql = FRENADOS_POR_DDL[caso]
        st.code(sql, language="sql")
        if st.button("Intentar guardarlo", type="primary", key="ddl"):
            r = run_in_rollback([sql])
            if r["ok"]:
                st.warning(f"No saltó ninguna restricción ({r['rowcount']} filas afectadas).")
            else:
                st.success(f"🛑 La base lo rechazó · restricción **`{r['constraint'] or '—'}`** (SQLSTATE {r['sqlstate']})")
                st.code(r["error"], language="text")
    with b:
        st.subheader("2 · Lo detecta un control")
        st.caption("Reglas que miran otras filas u otras tablas: un CHECK no alcanza, las encuentra el control.")
        caso2 = st.selectbox("Dato trucho", list(DETECTADOS_POR_CONTROL))
        cod, sql2 = DETECTADOS_POR_CONTROL[caso2]
        st.code(sql2, language="sql")
        st.caption(f"Después corre **{cod}** — {por_codigo[cod].titulo}")
        if st.button("Romper y correr el control", type="primary", key="ctrl"):
            r = run_in_rollback([sql2], check_sql=por_codigo[cod].sql)
            if not r["ok"]:
                st.error(r["error"])
            elif len(r["check"]):
                st.success(f"🔎 {cod} lo encontró: {len(r['check'])} fila(s) que rompen la regla. (Ya se deshizo.)")
                st.dataframe(r["check"], hide_index=True, width="stretch")
            else:
                st.warning(f"{cod} devolvió 0 filas.")

# ------------------------------------------------------------------ ejemplos
with tab_ej:
    for b in ejemplos:
        with st.expander(f"**{b.codigo}** — {b.titulo}", expanded=b.codigo == "E3"):
            st.code(b.sql, language="sql")
            st.dataframe(query(b.sql), hide_index=True, width="stretch")
