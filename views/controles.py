"""Corre los controles de 03_controles.sql y demuestra que la base se defiende.

Todo lo que "rompe" datos corre dentro de una transaccion que se deshace
(rollback): la base queda exactamente igual.
"""
import html
import re
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

# ---- piezas para que la demo se entienda: que paso, por que, y prueba de que la base quedo igual
TIPO_ERROR = {  # SQLSTATE -> (nombre de la regla, explicacion en criollo)
    "23514": ("CHECK", "El dato no cumple una condición escrita en la propia tabla (un rango o una regla sobre el valor)."),
    "23503": ("FK · clave foránea", "El dato apunta a algo que no existe o que no le corresponde, o se quiso borrar "
                                    "algo que otras filas todavía usan."),
    "23505": ("UNIQUE · no se repite", "Ese valor ya está cargado y la regla dice que no puede haber dos iguales."),
    "23502": ("NOT NULL", "Falta un dato obligatorio."),
}


def tabla_de(sql: str) -> str | None:
    """La tabla que toca la sentencia (update x / insert into x / delete from x)."""
    m = re.match(r"\s*(?:update|insert\s+into|delete\s+from)\s+(\w+)", sql, re.I)
    return m.group(1) if m else None


def definicion(nombre: str | None) -> str | None:
    """Como esta escrita la regla en la base (constraint o indice unico parcial)."""
    if not nombre:
        return None
    d = query("select pg_get_constraintdef(oid) as d from pg_constraint where conname = %s limit 1", (nombre,))
    if len(d):
        return d.d.iloc[0]
    d = query("select indexdef as d from pg_indexes where indexname = %s limit 1", (nombre,))
    return d.d.iloc[0] if len(d) else None


def tarjeta(clase: str, icono: str, titulo: str, que: str, chips: list[tuple[str, bool]],
            regla_titulo: str = "", regla: str | None = None, tabla: str | None = None, r: dict | None = None):
    chips_html = "".join(f'<span class="chip{" fuerte" if f else ""}">{html.escape(c)}</span>' for c, f in chips)
    regla_html = (f'<div class="regla">{html.escape(regla_titulo)}</div><code class="def">{html.escape(regla)}</code>'
                  if regla else "")
    igual = ""
    if tabla and r and r["antes"] is not None:
        igual = (f'<div class="igual">↩️ Rollback hecho · <code>{html.escape(tabla)}</code> tenía <b>{miles(r["antes"])}</b> '
                 f'filas y sigue con <b>{miles(r["despues"])}</b>: la base quedó exactamente igual.</div>')
    st.markdown(f'<div class="resultado {clase}"><div class="icono">{icono}</div>'
                f'<div class="titulo">{titulo}</div><div class="que">{html.escape(que)}</div>'
                f'<div class="chips">{chips_html}</div>{regla_html}{igual}</div>', unsafe_allow_html=True)


def paso(status, texto: str, pausa: float = 0.45):
    """Una linea del paso a paso, con una pausa corta para que se pueda seguir en vivo."""
    status.write(texto)
    time.sleep(pausa)


def miles(n: int) -> str:
    return f"{int(n):,}".replace(",", ".")


def marcador(lugar, clave: str, total: int, verbo: str):
    """Se dibuja al final (en un st.empty de arriba) para que ya cuente el intento recien hecho."""
    hechos = len(st.session_state.get(clave, set()))
    lugar.markdown(f'<div class="marcador"><span>Probaste <b>{hechos}</b> de <b>{total}</b> · {verbo}</span>'
                f'<div class="barra"><span style="width:{100 * hechos / total:.0f}%"></span></div></div>',
                unsafe_allow_html=True)


def anotar(clave: str, caso: str, total: int, mensaje: str):
    probados = st.session_state.setdefault(clave, set())
    nuevo = caso not in probados
    probados.add(caso)
    if nuevo and len(probados) == total:
        st.balloons()
        st.toast(mensaje, icon="🏆")


def mostrar_ddl(caso: str, r: dict, tabla: str | None):
    if r["ok"]:
        tarjeta("alerta", "⚠️", "No saltó ninguna restricción",
                f"La sentencia afectó {r['rowcount']} fila(s) y no hubo error (igual se deshizo).", [], tabla=tabla, r=r)
        return
    tipo, explica = TIPO_ERROR.get(r["sqlstate"], ("Restricción", "La base no aceptó el dato."))
    tarjeta("", "🛡️", f"¡Rechazado! La base frenó <b>{html.escape(caso.lower())}</b>", explica,
            [(r["constraint"] or "—", True), (tipo, False), (f"SQLSTATE {r['sqlstate']}", False)],
            "La regla, tal como está escrita en la base:", definicion(r["constraint"]), tabla, r)
    with st.expander("Ver el mensaje original de PostgreSQL"):
        st.code(r["error"], language="text")


def mostrar_control(cod: str, r: dict, tabla: str | None):
    if not r["ok"]:
        tarjeta("alerta", "⚠️", "La sentencia dio error", r["error"].splitlines()[0], [], tabla=tabla, r=r)
        return
    n = 0 if r["check"] is None else len(r["check"])
    if n:
        tarjeta("control", "🔎", f"¡Detectado! <b>{cod}</b> encontró {n} fila(s) que rompen la regla",
                "La base aceptó el cambio (ningún CHECK mira otras filas o tablas), pero el control lo encontró.",
                [(cod, True), ("control de integridad", False), (f"{r['rowcount']} fila(s) modificadas", False)],
                "La regla que revisa el control:", por_codigo[cod].titulo, tabla, r)
        st.dataframe(r["check"], hide_index=True, width="stretch")
    else:
        tarjeta("alerta", "⚠️", f"{cod} devolvió 0 filas", "El control no encontró nada para este caso.", [],
                tabla=tabla, r=r)


with tab_trucho:
    st.markdown("Elegí un dato trucho y probá guardarlo. Todo corre dentro de `begin … rollback`: "
                "**la base no cambia**, y al final se cuenta la tabla para demostrarlo.")
    a, b = st.columns(2, gap="large")
    with a:
        st.subheader("1 · Lo frena el DDL")
        st.caption("PK, FK (simples y compuestas), UNIQUE y CHECK: la base directamente no deja guardarlo.")
        lugar_ddl = st.empty()
        caso = st.selectbox("Dato trucho", list(FRENADOS_POR_DDL))
        sql = FRENADOS_POR_DDL[caso]
        tabla = tabla_de(sql)
        with st.expander("Ver el SQL que se intenta correr"):
            st.code(sql, language="sql")
        if st.button("🚀 Intentar guardarlo", type="primary", key="ddl", width="stretch"):
            with st.status("Probando el dato trucho…", expanded=True) as stt:
                paso(stt, "🔓 Abro una transacción (`begin`)")
                paso(stt, f"✍️ Intento guardar en `{tabla}`: *{caso.lower()}*")
                r = run_in_rollback([sql], tabla=tabla)
                if r["ok"]:
                    paso(stt, "😬 No saltó ninguna restricción")
                else:
                    paso(stt, f"🛑 PostgreSQL lo rechazó: `{r['constraint'] or r['sqlstate']}`", 0.6)
                paso(stt, "↩️ `rollback`: deshago todo")
                paso(stt, f"🔍 Cuento las filas de `{tabla}`: {miles(r['antes'])} antes, {miles(r['despues'])} después", 0.2)
                stt.update(label="🛡️ La base se defendió" if not r["ok"] else "⚠️ No hubo error",
                           state="complete" if not r["ok"] else "error", expanded=False)
            st.session_state["ultimo_ddl"] = (caso, r, tabla)
            if not r["ok"]:
                st.toast(f"Rechazado por **{r['constraint']}**", icon="🛡️")
            anotar("probados_ddl", caso, len(FRENADOS_POR_DDL),
                   "¡Probaste todos! La base frenó cada uno de los datos truchos.")
        ultimo = st.session_state.get("ultimo_ddl")
        if ultimo and ultimo[0] == caso:  # el resultado queda mientras no cambies de caso
            mostrar_ddl(*ultimo)
        marcador(lugar_ddl, "probados_ddl", len(FRENADOS_POR_DDL), "casos frenados por la base")

    with b:
        st.subheader("2 · Lo detecta un control")
        st.caption("Reglas que miran otras filas u otras tablas: un CHECK no alcanza, las encuentra el control.")
        lugar_ctrl = st.empty()
        caso2 = st.selectbox("Dato trucho", list(DETECTADOS_POR_CONTROL))
        cod, sql2 = DETECTADOS_POR_CONTROL[caso2]
        tabla2 = tabla_de(sql2)
        st.caption(f"Después corre **{cod}** — {por_codigo[cod].titulo}")
        with st.expander("Ver el SQL que se intenta correr"):
            st.code(sql2, language="sql")
        if st.button("🧪 Romper y correr el control", type="primary", key="ctrl", width="stretch"):
            with st.status("Rompiendo el dato y buscando el error…", expanded=True) as stt:
                paso(stt, "🔓 Abro una transacción (`begin`)")
                paso(stt, f"✍️ Rompo el dato en `{tabla2}`: *{caso2.lower()}*")
                r = run_in_rollback([sql2], check_sql=por_codigo[cod].sql, tabla=tabla2)
                if r["ok"]:
                    paso(stt, f"😶 La base lo aceptó ({r['rowcount']} fila(s)): ninguna restricción mira otras tablas")
                    n = 0 if r["check"] is None else len(r["check"])
                    paso(stt, f"🔎 Corro **{cod}**… encontró **{n}** fila(s) que rompen la regla", 0.6)
                else:
                    paso(stt, f"🛑 La sentencia dio error: `{r['sqlstate']}`")
                paso(stt, "↩️ `rollback`: deshago todo")
                paso(stt, f"🔍 Cuento las filas de `{tabla2}`: {miles(r['antes'])} antes, {miles(r['despues'])} después", 0.2)
                hallado = r["ok"] and r["check"] is not None and len(r["check"]) > 0
                stt.update(label=f"🔎 {cod} lo detectó" if hallado else "⚠️ No se detectó",
                           state="complete" if hallado else "error", expanded=False)
            st.session_state["ultimo_ctrl"] = (caso2, cod, r, tabla2)
            if hallado:
                st.toast(f"**{cod}** encontró el dato roto", icon="🔎")
            anotar("probados_ctrl", caso2, len(DETECTADOS_POR_CONTROL),
                   "¡Probaste todos! Cada dato roto lo encontró su control.")
        ultimo = st.session_state.get("ultimo_ctrl")
        if ultimo and ultimo[0] == caso2:
            mostrar_control(*ultimo[1:])
        marcador(lugar_ctrl, "probados_ctrl", len(DETECTADOS_POR_CONTROL), "casos detectados por un control")

# ------------------------------------------------------------------ ejemplos
with tab_ej:
    for b in ejemplos:
        with st.expander(f"**{b.codigo}** — {b.titulo}", expanded=b.codigo == "E3"):
            st.code(b.sql, language="sql")
            st.dataframe(query(b.sql), hide_index=True, width="stretch")
